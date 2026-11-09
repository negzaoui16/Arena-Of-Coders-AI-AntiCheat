"""
Script de ré-entraînement périodique du modèle (cycles contrôlés).
- Charge le dataset construit à partir des décisions humaines validées
- Entraîne un nouveau modèle (RandomForest)
- Sauvegarde avec versioning (v1, v2, ...)
Pas d'apprentissage en temps réel : exécution manuelle ou cron.
"""
import argparse
import json
from pathlib import Path

from config import STORAGE_DIR, DEFAULT_MODEL_VERSION
from src.storage import build_training_dataset, load_predictions, load_human_decisions
from src.model_ia import train_model, load_model, save_model
from src.features import FEATURE_NAMES


def get_next_version() -> str:
    """Détermine la prochaine version du modèle (v1, v2, ...)."""
    from config import MODELS_DIR
    if not MODELS_DIR.exists():
        return "v1"
    versions = []
    for p in MODELS_DIR.glob("model_*.pkl"):
        name = p.stem  # model_v1
        if name.startswith("model_"):
            ver = name[6:]
            if ver.startswith("v") and ver[1:].isdigit():
                versions.append(int(ver[1:]))
    if not versions:
        return "v1"
    return f"v{max(versions) + 1}"


def run_training(
    min_samples: int = 10,
    version: str = None,
    dataset_path: Path = None,
) -> dict:
    """
    Construit le dataset à partir des décisions humaines, entraîne le modèle, sauvegarde.
    version : si None, utilise la prochaine version (v2, v3, ...).
    """
    if version is None:
        version = get_next_version()

    # 1. Construire le dataset
    try:
        path = build_training_dataset(output_path=dataset_path, min_samples=min_samples)
    except ValueError as e:
        return {"error": str(e), "version": None}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    X = data["X"]
    y = data["y"]

    # 2. Entraîner le modèle
    # X est une liste de listes (features_to_vector), on doit les convertir en dict pour train_model
    from src.features import extract_all_features
    # train_model attend List[dict] pour X mais on a déjà des vecteurs dans le JSON
    import numpy as np
    X_vec = X  # déjà des listes de floats
    y_list = y
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestClassifier
    X_arr = np.array(X_vec)
    y_arr = np.array(y_list)
    X_train, X_test, y_train, y_test = train_test_split(X_arr, y_arr, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    clf.fit(X_train, y_train)
    score = clf.score(X_test, y_test)
    save_model(clf, version)

    return {
        "version": version,
        "accuracy": float(score),
        "n_samples": len(y_list),
        "dataset_path": str(path),
    }


def main():
    parser = argparse.ArgumentParser(description="Ré-entraînement du modèle anti-triche")
    parser.add_argument("--min-samples", type=int, default=10, help="Nombre minimum d'échantillons")
    parser.add_argument("--version", type=str, default=None, help="Version du modèle (ex: v2). Par défaut: auto-incrément")
    parser.add_argument("--dataset", type=Path, default=None, help="Chemin du dataset JSON (optionnel)")
    args = parser.parse_args()
    result = run_training(min_samples=args.min_samples, version=args.version, dataset_path=args.dataset)
    if "error" in result:
        print("Erreur:", result["error"])
        return 1
    print("Ré-entraînement terminé.")
    print("Version:", result["version"])
    print("Accuracy (test):", result["accuracy"])
    print("Échantillons:", result["n_samples"])
    return 0


if __name__ == "__main__":
    exit(main())
