# Image pour Hugging Face Spaces (API anti-triche)
# Port 7860 requis par HF Spaces
FROM python:3.11-slim

WORKDIR /app

# Dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code et données (hors venv, cache, storage)
COPY config.py .
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Création du modèle v1 au build (script d'entraînement initial)
RUN python scripts/train_initial_model.py

# Hugging Face Spaces écoute sur 7860
EXPOSE 7860
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "7860"]
