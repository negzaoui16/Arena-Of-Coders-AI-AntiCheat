"""
Combinaison des scores et verdict textuel.
FinalScore = 0.4 * score_ia + 0.3 * score_plagiat + 0.3 * score_copier_coller
Verdict : OK / SUSPECT / TRICHE PROBABLE selon les seuils.
"""
from typing import Literal

from config import WEIGHT_IA, WEIGHT_PLAGIAT, WEIGHT_COPY_PASTE
from config import THRESHOLD_OK, THRESHOLD_SUSPECT

VerdictType = Literal["OK", "SUSPECT", "TRICHE PROBABLE"]


def compute_final_score(
    score_ia: float,
    score_plagiat: float,
    score_copy_paste: float,
) -> float:
    """
    Score final pondéré (entre 0 et 1).
    """
    return round(
        WEIGHT_IA * score_ia
        + WEIGHT_PLAGIAT * score_plagiat
        + WEIGHT_COPY_PASTE * score_copy_paste,
        4,
    )


def get_verdict(final_score: float) -> VerdictType:
    """
    Verdict textuel selon les seuils configurés.
    - score < THRESHOLD_OK -> OK
    - THRESHOLD_OK <= score < THRESHOLD_SUSPECT -> SUSPECT
    - score >= THRESHOLD_SUSPECT -> TRICHE PROBABLE
    """
    if final_score < THRESHOLD_OK:
        return "OK"
    if final_score < THRESHOLD_SUSPECT:
        return "SUSPECT"
    return "TRICHE PROBABLE"


def analyze(
    score_ia: float,
    score_plagiat: float,
    copy_paste_detected: bool,
    score_copy_paste: float,
) -> dict:
    """
    Agrège les résultats et retourne le dictionnaire complet pour l'API.
    """
    final_score = compute_final_score(score_ia, score_plagiat, score_copy_paste)
    verdict = get_verdict(final_score)
    return {
        "score_ia": round(score_ia, 4),
        "score_plagiat": round(score_plagiat, 4),
        "copy_paste_detected": copy_paste_detected,
        "score_copy_paste": round(score_copy_paste, 4),
        "final_score": final_score,
        "verdict": verdict,
    }


# Alias pour usage externe
compute_analysis_result = analyze
