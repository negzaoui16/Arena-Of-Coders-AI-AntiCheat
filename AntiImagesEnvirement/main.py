import io
import os
import numpy as np
import faiss
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import uvicorn
from sklearn.metrics.pairwise import cosine_similarity
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Checkpoint Image Validator AI with Continuous Learning",
    description="API to validate hackathon workspace images using Hugging Face CLIP model and a FAISS memory bank.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

print("Loading the AI model...")
MODEL_NAME = "openai/clip-vit-base-patch32"
EMBEDDING_DIM = 512 # CLIP output dimension
FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH", "memory_bank.index")

try:
    model = CLIPModel.from_pretrained(MODEL_NAME)
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    print("AI model loaded successfully!")
    
    # Initialize FAISS Memory Bank
    if os.path.exists(FAISS_INDEX_PATH):
        print("Loading existing memory bank...")
        index = faiss.read_index(FAISS_INDEX_PATH)
    else:
        print("Creating new empty memory bank...")
        # L2 distance index
        index = faiss.IndexFlatL2(EMBEDDING_DIM) 
        
except Exception as e:
    print(f"Error initializing AI: {e}")
    model, processor, index = None, None, None

POSITIVE_LABELS = [
    "a hackathon workspace",
    "people coding on laptops",
    "a computer programming environment",
    "a team of developers working"
]

NEGATIVE_LABELS = [
    "a blank wall",
    "a video game setup",
    "someone playing video games",
    "a nature scene with trees",
    "a natural landscape",
    "a landscape",
    "a typical selfie",
    "food",
    "an empty room",
    "a bed",
    "a document or piece of paper"
]

ALL_LABELS = POSITIVE_LABELS + NEGATIVE_LABELS
THRESHOLD = 0.70 # Stricter threshold
AUTO_LEARN_THRESHOLD = 0.90

def get_image_embedding(pil_image):
    """Extracts the 512-dimensional visual vector of the image."""
    inputs = processor(images=pil_image, return_tensors="pt")
    with torch.no_grad():
        image_features = model.get_image_features(**inputs)
    # Normalize the features
    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
    return image_features.cpu().numpy()

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.post("/scan")
async def scan_checkpoint(image: UploadFile = File(...)):
    if model is None or index is None:
        raise HTTPException(status_code=500, detail="AI System not initialized.")

    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Not an image.")

    try:
        image_data = await image.read()
        try:
            pil_image = Image.open(io.BytesIO(image_data)).convert("RGB")
        except Exception as img_err:
            return {"accepte": False, "confiance": 0, "message": f"Erreur de lecture de l'image (Format non supporte ou fichier corrompu): {img_err}"}
        
        # 1. Zero-Shot Classification (Text comparison)
        inputs = processor(text=ALL_LABELS, images=pil_image, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = model(**inputs)
        
        probs = outputs.logits_per_image.softmax(dim=1).squeeze().tolist()
        results = dict(zip(ALL_LABELS, probs))
        zero_shot_score = sum(results[label] for label in POSITIVE_LABELS)
        best_label = max(results, key=results.get)
        
        # 2. Get Image Embedding for Memory
        img_embedding = get_image_embedding(pil_image)
        
        # 3. Memory Comparison (Did we see something similar before?)
        memory_score = 0.0
        memory_bonus = 0.0
        
        if index.ntotal > 0:
            # Search for the 3 most similar images in memory
            # FAISS L2 returns distances (lower is better).
            distances, _ = index.search(img_embedding, min(3, index.ntotal))
            
            # Convert L2 distance to a similarity score between 0 and 1
            # (Rough approximation for normalized vectors: sim = 1 - (dist^2 / 4))
            avg_distance = np.mean(distances[0])
            memory_score = max(0.0, 1.0 - (avg_distance / 4.0))
            
            # If it's very similar to accepted images, give a bonus (max 20%)
            memory_bonus = memory_score * 0.20

        # 4. Final Decision
        final_score = min(1.0, float(zero_shot_score) + float(memory_bonus))
        accepted = bool(final_score >= THRESHOLD)
        score_percentage = round(float(final_score) * 100, 2)
        zero_shot_pct = round(float(zero_shot_score) * 100, 2)
        
        if accepted:
            msg = f"Accepté! (Score Global: {score_percentage}%) [Base: {zero_shot_pct}% | Mémoire: +{round(float(memory_bonus)*100,1)}%]"
            
            # Auto-learning: If the base score is extremely high, memorize it automatically
            if zero_shot_score >= AUTO_LEARN_THRESHOLD:
                index.add(img_embedding)
                faiss.write_index(index, FAISS_INDEX_PATH)
                msg += " -> Automatiquement appris (Memoire)"
        else:
            msg = f"Refuse. Je vois plutot: '{best_label}'. (Score Global: {score_percentage}%)"
            
        return {
            "accepte": bool(accepted),
            "confiance": float(score_percentage),
            "details": {
                "zero_shot_score": float(zero_shot_pct),
                "memory_bonus": round(float(memory_bonus) * 100, 2),
                "top_label": str(best_label),
                "images_in_memory": int(index.ntotal) if index else 0
            },
            "message": str(msg)
        }
        
    except Exception as e:
        print(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/learn")
async def force_learn(image: UploadFile = File(...)):
    """Admin endpoint to force the model to memorize a good image, even if it scored low."""
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Not an image.")
    try:
        image_data = await image.read()
        pil_image = Image.open(io.BytesIO(image_data)).convert("RGB")
        img_embedding = get_image_embedding(pil_image)
        
        index.add(img_embedding)
        faiss.write_index(index, FAISS_INDEX_PATH)
        
        return {"status": "success", "message": "Image memorized!", "total_memory": index.ntotal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH", "memory_bank.index")

# Create FAISS or initialize
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)
