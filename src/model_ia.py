"""
Modèle de Machine Learning pour détecter le code généré par IA.
Utilise un classifieur scikit-learn (RandomForest) exécutable sur CPU.
Retourne une probabilité entre 0 et 1 (score de suspicion IA).
Supporte chargement depuis le Hub et modèle global pour rechargement à chaud.
"""
import json
import pickle
from pathlib import Path
from typing import List, Optional, Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from config import MODELS_DIR, DEFAULT_MODEL_VERSION, HF_REPO_TYPE
from src.features import extract_all_features, features_to_vector, FEATURE_NAMES

# Modèle chargé en mémoire (prioritaire sur le disque après retrain ou load from Hub)
_current_clf: Optional[Any] = None


def _model_path(version: str) -> Path:
    """Chemin du fichier modèle pour une version donnée."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR / f"model_{version}.pkl"


def _metadata_path(version: str) -> Path:
    """Chemin des métadonnées du modèle (feature names, etc.)."""
    return MODELS_DIR / f"model_{version}_metadata.json"


def get_global_model():
    """Retourne le classifieur en mémoire (None si non défini)."""
    return _current_clf


def set_global_model(clf) -> None:
    """Définit le classifieur utilisé pour les prédictions (rechargement à chaud)."""
    global _current_clf
    _current_clf = clf


def load_model(version: Optional[str] = None):
    """
    Charge le modèle et le vectoriseur (métadonnées) depuis le disque.
    Si le fichier n'existe pas, retourne None (le module utilisera un fallback).
    """
    version = version or DEFAULT_MODEL_VERSION
    path = _model_path(version)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def save_model(clf, version: str) -> None:
    """Sauvegarde le modèle et les métadonnées."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = _model_path(version)
    with open(path, "wb") as f:
        pickle.dump(clf, f)
    meta = {"feature_names": FEATURE_NAMES}
    with open(_metadata_path(version), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def predict_ia_score(code: str, version: Optional[str] = None) -> float:
    """
    Retourne la probabilité que le code soit généré par IA (score entre 0 et 1).
    Utilise le modèle global si défini (après retrain ou load from Hub), sinon charge depuis le disque.
    Si aucun modèle n'est chargé, retourne un score par défaut 0.0 (pas de blocage).
    """
    features = extract_all_features(code)
    vector = np.array([features_to_vector(features)])

    clf = get_global_model()
    if clf is None:
        clf = load_model(version or DEFAULT_MODEL_VERSION)
    if clf is None:
        # Fallback : pas de modèle entraîné -> score 0 (neutre)
        return 0.0

    # RandomForest en sklearn n'a pas predict_proba pour certains cas; on utilise predict_proba
    if hasattr(clf, "predict_proba"):
        proba = clf.predict_proba(vector)[0]
        # Classe 1 = généré par IA (index 1)
        if proba.shape[0] == 2:
            return float(proba[1])
        return float(proba[0])
    return float(clf.predict(vector)[0])


def train_model(
    X: List[dict],
    y: List[int],
    version: str = "v1",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """
    Entraîne un RandomForest sur les features extraites.
    X : liste de dictionnaires de features (extract_all_features)
    y : labels 0 = humain, 1 = IA
    Retourne des métriques (accuracy, etc.).
    """
    X_vec = np.array([features_to_vector(x) for x in X])
    y_arr = np.array(y)
    X_train, X_test, y_train, y_test = train_test_split(
        X_vec, y_arr, test_size=test_size, random_state=random_state
    )
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=random_state)
    clf.fit(X_train, y_train)
    score = clf.score(X_test, y_test)
    save_model(clf, version)
    return {"accuracy": score, "version": version}


# --- Hugging Face Hub (apprentissage continu) ---

HUB_MODEL_FILENAME = "model_latest.pkl"


def load_model_from_hub(repo_id: str, token: Optional[str] = None) -> bool:
    """
    Télécharge model_latest.pkl depuis le repo HF, le sauvegarde en local comme "latest",
    charge le modèle et le définit comme modèle global.
    Retourne True si succès, False sinon (fichier absent ou erreur).
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        return False
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        path = hf_hub_download(
            repo_id=repo_id,
            filename=f"models/{HUB_MODEL_FILENAME}",
            repo_type=HF_REPO_TYPE,
            token=token,
            local_dir=str(MODELS_DIR),
            local_dir_use_symlinks=False,
            force_filename="model_latest.pkl",
        )
    except Exception:
        return False
    # path peut être un chemin sous local_dir
    local_path = MODELS_DIR / "model_latest.pkl"
    if not local_path.exists():
        return False
    with open(local_path, "rb") as f:
        clf = pickle.load(f)
    set_global_model(clf)
    return True


def push_model_to_hub(version: str, repo_id: str, token: Optional[str] = None) -> bool:
    """
    Envoie le modèle (ex: model_latest.pkl ou model_v2.pkl) vers le repo HF
    sous le nom models/model_latest.pkl pour que le prochain démarrage charge la dernière version.
    """
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return False
    path = _model_path(version)
    if not path.exists():
        return False
    api = HfApi(token=token)
    api.upload_file(
        path_in_repo=f"models/{HUB_MODEL_FILENAME}",
        path_or_fileobj=str(path),
        repo_id=repo_id,
        repo_type=HF_REPO_TYPE,
        token=token,
    )
    return True
