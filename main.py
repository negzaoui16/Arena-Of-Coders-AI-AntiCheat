import io
import os
import sys

# Ensure ffmpeg is found on Windows
if os.name == 'nt':
    ffmpeg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "venv", "Scripts"))
    os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH", "")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import uvicorn
import librosa
import soundfile as sf
import torch
import faiss
import numpy as np
import json
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Vocal Checkpoint Validator",
    description="API to validate hackathon participant work via voice using Whisper (STT) and Zero-Shot Classification.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

print("Loading AI Models...(This may take a moment)")
# 1. Speech-to-Text Model (Faster & Lighter version)
STT_MODEL = "openai/whisper-tiny"  
# 2. NLP Zero-Shot Classification Model (Multilingual for Arabic, French, English)
NLP_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

device = 0 if torch.cuda.is_available() else -1

print("Loading Embedding Model for Memory...")
embedder_device = "cuda" if torch.cuda.is_available() else "cpu"
embedder = SentenceTransformer('all-MiniLM-L6-v2', device=embedder_device)

# --- Memory Bank (FAISS) Setup ---
FAISS_INDEX_PATH = "vocal_memory_bank.index"
MEMORY_DATA_PATH = "vocal_memory_data.json"
EMBEDDING_DIM = 384 # MiniLM uses 384-dimensional vectors

vocal_memory_data = {}

if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(MEMORY_DATA_PATH):
    print("Loading existing Vocal FAISS Memory Bank...")
    index = faiss.read_index(FAISS_INDEX_PATH)
    try:
        with open(MEMORY_DATA_PATH, "r", encoding="utf-8") as f:
            vocal_memory_data = json.load(f)
    except Exception as e:
        print(f"Error loading memory data: {e}")
        vocal_memory_data = {}
else:
    print("Creating new Vocal FAISS Memory Bank...")
    index = faiss.IndexFlatL2(EMBEDDING_DIM)

try:
    print(f"Loading Whisper model ({STT_MODEL})...")
    transcriber = pipeline("automatic-speech-recognition", model=STT_MODEL, device=device)
    
    print(f"Loading Zero-Shot Classifier ({NLP_MODEL})...")
    classifier = pipeline("zero-shot-classification", model=NLP_MODEL, device=device)
    
    print("✅ AI Models loaded successfully!")
except Exception as e:
    print(f"❌ Error loading models: {e}")
    transcriber = None
    classifier = None

# Labels we consider "Valid Work"
POSITIVE_LABELS = [
    # English
    "talking about a coding project or software development",
    "discussing code, algorithms, or programming logic",
    "hackathon teamwork and project planning",
    "fixing a bug or technical issue",
    # French
    "parler d'un projet de code ou développement de logiciels",
    "discuter du code, des algorithmes ou de la logique de programmation",
    "travail d'équipe au hackathon et planification de projet",
    "correction d'un bug ou problème technique",
    # Arabic
    "الحديث عن مشروع برمجة أو تطوير برمجيات",
    "مناقشة الكود، الخوارزميات، أو المنطق البرمجي",
    "العمل الجماعي في الهاكاثون وتخطيط المشروع",
    "إصلاح خطأ أو مشكلة فنية"
]

# Labels we consider "Not Working / Leisure"
NEGATIVE_LABELS = [
    # English
    "playing video games or talking about gaming",
    "talking about sleeping or taking a nap",
    "small talk about food or restaurants",
    "listening to music or watching a movie",
    "silence or background noise",
    # French
    "jouer à des jeux vidéo ou parler de gaming",
    "parler de dormir ou faire une sieste",
    "discuter de nourriture ou de restaurants",
    "écouter de la musique ou regarder un film",
    "silence ou bruit de fond",
    # Arabic
    "لعب ألعاب الفيديو أو التحدث عن الألعاب",
    "الحديث عن النوم أو أخذ قيلولة",
    "أحاديث جانبية عن الطعام أو المطاعم",
    "الاستماع إلى الموسيقى أو مشاهدة فيلم",
    "صمت أو ضجيج في الخلفية"
]

ALL_LABELS = POSITIVE_LABELS + NEGATIVE_LABELS
THRESHOLD = 0.60 # Needs to be at least 60% sure it's work

@app.post("/learn-audio")
async def learn_audio(text: str = Form(...)):
    """
    Force the AI to remember a particular sentence as a valid Hackathon work phrase.
    """
    try:
        if not text or len(text.strip()) < 5:
            return {"success": False, "message": "Le texte est trop court ou vide."}
            
        text = text.strip()
        
        # 1. Convert text to vector
        vector = embedder.encode([text])
        faiss.normalize_L2(vector)
        
        # 2. Add to FAISS Index
        memory_id = index.ntotal
        index.add(vector)
        
        # 3. Store text mapping
        vocal_memory_data[str(memory_id)] = text
        
        # 4. Save to disk
        faiss.write_index(index, FAISS_INDEX_PATH)
        with open(MEMORY_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(vocal_memory_data, f, ensure_ascii=False, indent=4)
            
        return {
            "success": True, 
            "message": f"🧠 Phrase apprise avec succès ! ({text[:30]}...)",
            "total_memories": index.ntotal
        }
        
    except Exception as e:
        print(f"Learning error: {e}")
        return {"success": False, "message": f"Erreur lors de l'apprentissage: {str(e)}"}

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.post("/scan-audio")
async def scan_audio(audio: UploadFile = File(...)):
    if transcriber is None or classifier is None:
        raise HTTPException(status_code=500, detail="AI Models not initialized.")

    if not audio.content_type.startswith("audio/"):
        return {"accepte": False, "confiance": 0, "message": "Le fichier envoyé n'est pas un fichier audio."}

    try:
        # 1. Read Audio Data into Temp File (because librosa fails on M4A streams)
        audio_data = await audio.read()
        
        # Determine extension from filename to help decoder
        ext = os.path.splitext(audio.filename)[1].lower() if audio.filename else ".tmp"
        temp_filename = f"temp_upload_{os.getpid()}{ext}"
        
        with open(temp_filename, "wb") as f:
            f.write(audio_data)
            
        try:
            # Whisper requires 16000Hz sampling rate.
            y, sr = librosa.load(temp_filename, sr=16000)
        finally:
            # Always clean up the temp file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
        
        # 2. Transcribe Audio (Speech to Text)
        print("Transcribing audio...")
        transcription_result = transcriber(y)
        transcribed_text = transcription_result["text"].strip()
        
        if not transcribed_text:
            return {
                "accepte": False,
                "confiance": 0,
                "transcription": "",
                "message": "Aucune voix détectée (Silence)."
            }

        # 3. Classify Text (Zero-Shot NLP)
        print(f"Classifying text: '{transcribed_text}'")
        classification = classifier(transcribed_text, ALL_LABELS, multi_label=True)
        
        # Summarize positive and negative scores independently
        scores = dict(zip(classification["labels"], classification["scores"]))
        
        # Take the Maximum confidence across Positive Labels
        work_score = max(scores[label] for label in POSITIVE_LABELS)
        best_work_label = max(POSITIVE_LABELS, key=lambda l: scores[l])
        
        # Take the Maximum confidence across Negative Labels
        leisure_score = max(scores[label] for label in NEGATIVE_LABELS)
        best_leisure_label = max(NEGATIVE_LABELS, key=lambda l: scores[l])
        
        # Determine the ultimate overarching label
        if work_score > leisure_score:
            best_label = best_work_label
        else:
            best_label = best_leisure_label
            
        # --- MEMORY BONUS MODULE ---
        memory_bonus = 0.0
        similarity_score = 0.0
        memory_match = ""
        
        if index.ntotal > 0:
            # 1. Convert Current Transcription to Vector
            query_vector = embedder.encode([transcribed_text])
            faiss.normalize_L2(query_vector)
            
            # 2. Search FAISS Index
            # We use L2 normalized vectors, so distance < 0.5 roughly means high similarity 
            # (In Inner Product, it would be > 0.85)
            # Since we initialized IndexFlatL2, lower distance is better
            distances, indices = index.search(query_vector, 1)
            best_distance = float(distances[0][0])
            best_memory_id = str(indices[0][0])
            
            # Approximate cosine similarity from L2 distance on normalized vectors:
            # cosine_sim = 1 - (L2^2 / 2)
            similarity_score = 1.0 - (best_distance / 2.0)
            
            if similarity_score > 0.85: # If 85% similar to a remembered valid thought
                print(f"🧠 MEMORY MATCH! Dist: {best_distance:.4f} (Sim: {similarity_score:.4f})")
                memory_bonus = 0.20 # +20% boost
                memory_match = vocal_memory_data.get(best_memory_id, "Unknown Memory")
                
        # Apply Bonus
        final_score = min(work_score + memory_bonus, 1.0)
        
        # 4. Final Decision (Must be mostly work AND pass threshold)
        accepted = (final_score > leisure_score) and (final_score >= THRESHOLD)
        score_percentage = round(final_score * 100, 2)
        
        if accepted:
            msg = f"✅ Analysé avec succès.\n\n🎙️ L'Intelligence Artificielle Vocale globale confirme que vous êtes activement impliqué dans votre travail de développement (Score de confiance: {score_percentage}%)."
            if memory_bonus > 0:
                msg += "\n\n🧠 Bonus contextuel: L'IA a reconnu des similarités avec des sessions de travail extrêmement techniques."
                
            # --- AUTO LEARN ---
            # Automatically memorize very high-confidence work conversations
            if final_score >= 0.95 and similarity_score < 0.85:
                print(f"✨ Auto-learning high confidence text: {transcribed_text[:30]}...")
                auto_vector = embedder.encode([transcribed_text])
                faiss.normalize_L2(auto_vector)
                
                new_id = index.ntotal
                index.add(auto_vector)
                vocal_memory_data[str(new_id)] = transcribed_text
                
                faiss.write_index(index, FAISS_INDEX_PATH)
                with open(MEMORY_DATA_PATH, "w", encoding="utf-8") as f:
                    json.dump(vocal_memory_data, f, ensure_ascii=False, indent=4)
                
                msg += "\n\n📈 Apprentissage Continu: L'IA a trouvé votre explication très qualitative et l'a mémorisée comme référence."

        else:
            msg = f"❌ Refusé.\n\n🎙️ L'Intelligence Artificielle Vocale a détecté une activité non liée au code. Il semblerait que vous parliez de : '{best_label}' au lieu de travailler (Confiance: {score_percentage}%)."
            
        return {
            "accepte": bool(accepted),
            "confiance": float(score_percentage),
            "transcription": str(transcribed_text),
            "details": {
                "top_label": str(best_label),
                "is_work": float(work_score),
                "memory_bonus": float(memory_bonus),
                "similarity_score": float(similarity_score),
                "matched_memory": str(memory_match)
            },
            "message": str(msg)
        }

    except Exception as e:
        print(f"Error processing audio: {e}")
        return {"accepte": False, "confiance": 0, "message": f"Erreur de traitement: {str(e)}"}



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
