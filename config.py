"""
Configuration centrale du projet anti-triche.
Poids des scores et seuils pour le verdict.
Apprentissage automatique activable.
"""
import os
from pathlib import Path

# Chemins
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
STORAGE_DIR = PROJECT_ROOT / "storage"

# Hugging Face Hub (apprentissage continu sur le Space)
# Repo = ton Space (ex: Negzaoui/anti-cheat-coding) ou un repo dédié
# Token = HF_TOKEN en env (avec droit écrit pour push modèle / storage)
HF_REPO = os.environ.get("HF_REPO", "").strip() or None
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip() or None
# Type du repo : "space" pour un HF Space, "model" pour un repo Modèle
HF_REPO_TYPE = os.environ.get("HF_REPO_TYPE", "space").strip().lower() or "space"
# Secret pour protéger POST /retrain (optionnel)
RETRAIN_SECRET = os.environ.get("RETRAIN_SECRET", "").strip() or None

# Poids du score final (doivent sommer à 1.0)
WEIGHT_IA = 0.4
WEIGHT_PLAGIAT = 0.3
WEIGHT_COPY_PASTE = 0.3

# Seuils pour le verdict textuel
THRESHOLD_OK = 0.35          # score < 0.35 -> OK
THRESHOLD_SUSPECT = 0.65     # 0.35 <= score < 0.65 -> SUSPECT
# score >= 0.65 -> TRICHE PROBABLE

# Détection copier-coller
MIN_BLOCK_LINES = 10         # nombre min de lignes pour "gros bloc"
MAX_MS_PER_LINE_COPY = 50    # si temps moyen par ligne < 50 ms -> suspect

# Version du modèle par défaut
DEFAULT_MODEL_VERSION = "v1"

# =====================================================
# APPRENTISSAGE AUTOMATIQUE (Auto-Learning)
# =====================================================
# Si activé, le modèle apprend automatiquement :
# 1. Auto-labellise les cas "extrêmes" (score très bas = humain, score très haut = IA)
# 2. Ré-entraîne automatiquement après N soumissions

# Activer l'apprentissage automatique (True/False ou via env)
AUTO_LEARN_ENABLED = os.environ.get("AUTO_LEARN_ENABLED", "true").strip().lower() in ("true", "1", "yes")

# Seuils pour auto-labellisation (cas "extrêmes" = haute confiance)
AUTO_LABEL_HUMAN_THRESHOLD = 0.15   # score_ia < 0.15 → auto-label humain (0)
AUTO_LABEL_IA_THRESHOLD = 0.85      # score_ia > 0.85 → auto-label IA (1)

# Ré-entraînement automatique après N nouvelles décisions
AUTO_RETRAIN_EVERY_N = int(os.environ.get("AUTO_RETRAIN_EVERY_N", "20"))

# Nombre minimum d'échantillons pour déclencher un retrain
AUTO_RETRAIN_MIN_SAMPLES = int(os.environ.get("AUTO_RETRAIN_MIN_SAMPLES", "10"))
