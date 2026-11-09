# Use the official Python image
FROM python:3.11-slim

# HF Spaces run as a non-root user (uid 1000)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Fix ownership
RUN chown -R user:user $HOME/app
USER user

# Copy requirements and install deps (CPU-only torch via --index-url)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir tensorflow-cpu==2.16.1 tf-keras==2.16.0
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pillow-avif-plugin

# Pre-download CLIP model only (DeepFace VGG-Face will be downloaded at first request to save build time)
RUN python -c "from transformers import CLIPModel, CLIPProcessor; CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')"

# Copy source
COPY --chown=user . $HOME/app

# Export environment variable for FAISS
ENV FAISS_INDEX_PATH="/home/user/app/memory_bank.index"

EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
