"""
Détection du plagiat par similarité textuelle.
TF-IDF + cosine similarity entre la solution actuelle et un ensemble de solutions existantes.
Retourne un score de similarité entre 0 et 1 (1 = très similaire à une solution existante).
"""
from pathlib import Path
from typing import List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import DATA_DIR


def _normalize_for_similarity(code: str) -> str:
    """Réduit les variations (espaces, retours à la ligne) pour la comparaison."""
    return " ".join(code.split())


def compute_plagiarism_score(
    code: str,
    existing_solutions: Optional[List[str]] = None,
    vectorizer: Optional[TfidfVectorizer] = None,
    tfidf_matrix: Optional[np.ndarray] = None,
) -> float:
    """
    Compare le code à un ensemble de solutions existantes via TF-IDF + cosine similarity.
    Retourne le score max de similarité (0 à 1).
    Si existing_solutions est vide/None, retourne 0.0.
    Si vectorizer et tfidf_matrix sont fournis (ex: PlagiarismChecker), on transforme
    uniquement le code actuel et on compare à la matrice existante.
    """
    if not code or not code.strip():
        return 0.0
    current = _normalize_for_similarity(code)

    if vectorizer is not None and tfidf_matrix is not None:
        # Cas optimisé : vectorizer déjà fitté sur les solutions
        current_vec = vectorizer.transform([current])
        sim = cosine_similarity(current_vec, tfidf_matrix)[0]
        return float(np.max(sim))

    if existing_solutions is None:
        existing_solutions = []
    existing_solutions = [s for s in existing_solutions if s and s.strip()]
    if not existing_solutions:
        return 0.0

    others = [_normalize_for_similarity(s) for s in existing_solutions]
    all_docs = others + [current]
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(all_docs)
    current_vec = matrix[-1:]
    others_vec = matrix[:-1]
    sim = cosine_similarity(current_vec, others_vec)[0]
    return float(np.max(sim))


def load_solutions_from_directory(directory: Optional[Path] = None) -> List[str]:
    """
    Charge les solutions existantes depuis un répertoire (fichiers .py ou .txt).
    Utilisé pour alimenter la base de comparaison plagiat.
    """
    directory = directory or (DATA_DIR / "solutions")
    if not directory.exists():
        return []
    solutions = []
    for ext in ("*.py", "*.txt"):
        for path in directory.glob(ext):
            try:
                solutions.append(path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
    return solutions


class PlagiarismChecker:
    """
    Vérificateur de plagiat avec cache TF-IDF pour réutiliser
    le même ensemble de solutions sans recalculer à chaque requête.
    """

    def __init__(self, solutions: Optional[List[str]] = None, solutions_dir: Optional[Path] = None):
        self.solutions = solutions or load_solutions_from_directory(solutions_dir)
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._matrix: Optional[np.ndarray] = None
        if self.solutions:
            docs = [_normalize_for_similarity(s) for s in self.solutions]
            self._vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95,
                sublinear_tf=True,
            )
            self._matrix = self._vectorizer.fit_transform(docs)

    def score(self, code: str) -> float:
        return compute_plagiarism_score(
            code,
            existing_solutions=self.solutions,
            vectorizer=self._vectorizer,
            tfidf_matrix=self._matrix,
        )
