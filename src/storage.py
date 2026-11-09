"""
Stockage des prédictions et des décisions humaines pour l'apprentissage continu.
- Enregistrement des analyses (code, scores, verdict modèle)
- Enregistrement de la décision humaine finale (validée par un correcteur)
- Génération d'un dataset pour le ré-entraînement (cycles contrôlés)
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import STORAGE_DIR, HF_REPO_TYPE

PREDICTIONS_FILE = STORAGE_DIR / "predictions.jsonl"
HUMAN_DECISIONS_FILE = STORAGE_DIR / "human_decisions.jsonl"
DATASET_DIR = STORAGE_DIR / "datasets"


def _ensure_storage():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)


def store_prediction(
    submission_id: str,
    code: str,
    result: Dict[str, Any],
    room_params: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Enregistre une prédiction (sortie de l'analyse) pour traçabilité et futur apprentissage.
    Format : une ligne JSON par enregistrement (JSONL).
    """
    _ensure_storage()
    record = {
        "submission_id": submission_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "code": code,
        "result": result,
        "room_params": room_params or {},
    }
    with open(PREDICTIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def store_human_decision(
    submission_id: str,
    human_label: int,
    comment: Optional[str] = None,
) -> None:
    """
    Enregistre la décision humaine finale (0 = OK / humain, 1 = triche / IA).
    Utilisée pour construire le dataset de ré-entraînement.
    """
    _ensure_storage()
    record = {
        "submission_id": submission_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "human_label": human_label,
        "comment": comment or "",
    }
    with open(HUMAN_DECISIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_predictions(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Charge les prédictions enregistrées (pour génération de dataset)."""
    if not PREDICTIONS_FILE.exists():
        return []
    records = []
    with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if limit and len(records) >= limit:
                break
    return records


def load_human_decisions(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Charge les décisions humaines enregistrées."""
    if not HUMAN_DECISIONS_FILE.exists():
        return []
    records = []
    with open(HUMAN_DECISIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if limit and len(records) >= limit:
                break
    return records


def build_training_dataset(
    output_path: Optional[Path] = None,
    min_samples: int = 10,
) -> Path:
    """
    Construit un dataset (X: features, y: labels) à partir des prédictions
    qui ont une décision humaine associée.
    Retourne le chemin du fichier dataset (JSON) généré.
    """
    from src.features import extract_all_features, features_to_vector, FEATURE_NAMES

    _ensure_storage()
    predictions = {r["submission_id"]: r for r in load_predictions()}
    decisions = {r["submission_id"]: r["human_label"] for r in load_human_decisions()}
    X = []
    y = []
    for sid, label in decisions.items():
        if sid not in predictions:
            continue
        pred = predictions[sid]
        code = pred.get("code") or ""
        features = extract_all_features(code)
        X.append(features_to_vector(features))
        y.append(label)
    if len(X) < min_samples:
        raise ValueError(
            f"Pas assez d'échantillons avec décision humaine: {len(X)} < {min_samples}"
        )
    dataset = {
        "feature_names": FEATURE_NAMES,
        "X": X,
        "y": y,
        "n_samples": len(X),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    output_path = output_path or (DATASET_DIR / f"dataset_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    return output_path


# --- Sync avec Hugging Face Hub (données persistantes pour apprentissage continu) ---

def push_storage_to_hub(repo_id: str, token: Optional[str] = None) -> dict:
    """
    Envoie les fichiers storage (predictions, human_decisions) vers le repo HF.
    Permet de ne pas perdre les données au redémarrage du Space.
    """
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return {"ok": False, "error": "huggingface_hub non installé"}
    _ensure_storage()
    api = HfApi(token=token)
    out = {"ok": True, "uploaded": []}
    if PREDICTIONS_FILE.exists():
        api.upload_file(
            path_in_repo="predictions.jsonl",
            path_or_fileobj=str(PREDICTIONS_FILE),
            repo_id=repo_id,
            repo_type=HF_REPO_TYPE,
            token=token,
        )
        out["uploaded"].append("predictions.jsonl")
    if HUMAN_DECISIONS_FILE.exists():
        api.upload_file(
            path_in_repo="human_decisions.jsonl",
            path_or_fileobj=str(HUMAN_DECISIONS_FILE),
            repo_id=repo_id,
            repo_type=HF_REPO_TYPE,
            token=token,
        )
        out["uploaded"].append("human_decisions.jsonl")
    return out


def load_storage_from_hub(repo_id: str, token: Optional[str] = None) -> dict:
    """
    Télécharge les fichiers storage depuis le repo HF vers le disque local.
    À appeler au démarrage du Space pour récupérer les données des runs précédents.
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        return {"ok": False, "error": "huggingface_hub non installé"}
    _ensure_storage()
    out = {"ok": True, "downloaded": []}
    for remote_name in ["predictions.jsonl", "human_decisions.jsonl"]:
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=remote_name,
                repo_type=HF_REPO_TYPE,
                token=token,
                local_dir=str(STORAGE_DIR),
                local_dir_use_symlinks=False,
            )
            out["downloaded"].append(remote_name)
        except Exception:
            # Fichier absent sur le Hub = premier run, on garde le local (vide ou existant)
            pass
    return out
