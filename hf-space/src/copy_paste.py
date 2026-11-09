"""
Détection du copier-coller basée sur des règles métier.
- Gros blocs collés en une seule fois (nombre de lignes insérées rapidement).
- Analyse du temps de frappe (temps moyen par ligne / par caractère).
Retourne un booléen copy_paste_detected et un score entre 0 et 1 pour le scoring final.
"""
from typing import Any, Dict, List, Optional

from config import MIN_BLOCK_LINES, MAX_MS_PER_LINE_COPY


def detect_large_paste_block(typing_stats: Optional[Dict[str, Any]]) -> bool:
    """
    Détecte si un gros bloc a été inséré en une fois.
    typing_stats peut contenir : events (liste d'événements) ou
    block_insertions (liste de {line_count, timestamp}) ou équivalent.
    """
    if not typing_stats:
        return False
    # Format attendu : block_insertions = [{"line_count": 15, "duration_ms": 10}, ...]
    block_insertions = typing_stats.get("block_insertions") or []
    for block in block_insertions:
        line_count = block.get("line_count") or block.get("lines") or 0
        if line_count >= MIN_BLOCK_LINES:
            return True
    # Alternative : events avec delta de lignes
    events = typing_stats.get("events") or []
    if events:
        # Simuler détection : si on a un saut de plus de MIN_BLOCK_LINES lignes en peu de temps
        for i in range(1, len(events)):
            prev = events[i - 1]
            curr = events[i]
            line_prev = prev.get("line", 0)
            line_curr = curr.get("line", 0)
            dt_ms = curr.get("timestamp_ms", 0) - prev.get("timestamp_ms", 0)
            if line_curr - line_prev >= MIN_BLOCK_LINES and dt_ms < 500:
                return True
    return False


def detect_fast_typing(typing_stats: Optional[Dict[str, Any]], code: str) -> bool:
    """
    Détecte si le temps moyen par ligne est trop faible (collé).
    Si total_time_ms / num_lines < MAX_MS_PER_LINE_COPY -> suspect.
    """
    if not typing_stats or not code or not code.strip():
        return False
    lines = [l for l in code.strip().split("\n") if l.strip()]
    if not lines:
        return False
    total_ms = typing_stats.get("total_typing_time_ms") or typing_stats.get("total_time_ms") or 0
    if total_ms <= 0:
        return False
    avg_ms_per_line = total_ms / len(lines)
    return avg_ms_per_line < MAX_MS_PER_LINE_COPY


def copy_paste_detected(
    code: str,
    typing_stats: Optional[Dict[str, Any]] = None,
) -> tuple:
    """
    Combine les règles de détection copier-coller.
    Retourne (copy_paste_detected: bool, score_copy_paste: float).
    Le score est 0.0 si pas de copier-coller détecté, sinon entre 0.5 et 1.0 selon les signaux.
    """
    large_block = detect_large_paste_block(typing_stats)
    fast_typing = detect_fast_typing(typing_stats, code)
    if large_block and fast_typing:
        return True, 1.0
    if large_block or fast_typing:
        return True, 0.7
    return False, 0.0
