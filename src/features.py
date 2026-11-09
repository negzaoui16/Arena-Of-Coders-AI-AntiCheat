"""
Extraction de features à partir du code source.
Ces features alimentent le modèle ML pour la détection de code généré par IA.
"""
import re
import ast
from typing import List, Optional


def extract_line_length_stats(lines: List[str]) -> tuple:
    """
    Longueur moyenne des lignes et écart-type (variance).
    Le code IA tend à avoir des lignes plus homogènes.
    """
    if not lines:
        return 0.0, 0.0
    lengths = [len(line) for line in lines]
    mean_ = sum(lengths) / len(lengths)
    var_ = sum((x - mean_) ** 2 for x in lengths) / len(lengths) if len(lengths) > 1 else 0.0
    return round(mean_, 2), round(var_ ** 0.5, 2)


def extract_indentation_variance(lines: List[str]) -> float:
    """
    Variance de l'indentation (espaces en début de ligne).
    Le code humain peut être plus irrégulier.
    """
    indents = []
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            indent = len(line) - len(stripped)
            indents.append(indent)
    if not indents:
        return 0.0
    mean_ = sum(indents) / len(indents)
    var_ = sum((x - mean_) ** 2 for x in indents) / len(indents)
    return round(var_ ** 0.5, 2)


def extract_comment_ratio(lines: List[str]) -> float:
    """Ratio commentaires / lignes de code (hors vides)."""
    code_lines = [l for l in lines if l.strip()]
    if not code_lines:
        return 0.0
    comment_count = sum(1 for l in code_lines if l.strip().startswith("#") or '"""' in l or "'''" in l)
    return round(comment_count / len(code_lines), 4)


def extract_complexity_indicators(code: str) -> tuple:
    """
    Indicateurs de complexité : profondeur d'imbrication max,
    nombre de boucles/conditions, longueur des identifiants moyens.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0, 0, 0.0

    max_depth = 0
    num_branches = 0
    name_lengths = []

    def visit(node, depth: int):
        nonlocal max_depth, num_branches
        max_depth = max(max_depth, depth)
        if isinstance(node, (ast.For, ast.While, ast.If, ast.With)):
            num_branches += 1
        if isinstance(node, ast.Name):
            name_lengths.append(len(node.id))
        if isinstance(node, ast.FunctionDef):
            name_lengths.append(len(node.name))
        for child in ast.iter_child_nodes(node):
            visit(child, depth + 1)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            name_lengths.append(len(node.id))
        if isinstance(node, ast.FunctionDef):
            name_lengths.append(len(node.name))

    # Compter boucles/conditions
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While, ast.If, ast.With)):
            num_branches += 1

    # Profondeur approximative
    def depth_of(node, d=0):
        if not list(ast.walk(node)):
            return d
        return max(depth_of(c, d + 1) for c in ast.iter_child_nodes(node)) if list(ast.iter_child_nodes(node)) else d

    for node in ast.walk(tree):
        max_depth = max(max_depth, depth_of(node))

    avg_name_len = sum(name_lengths) / len(name_lengths) if name_lengths else 0.0
    return max_depth, num_branches, round(avg_name_len, 2)


def extract_all_features(code: str) -> dict:
    """
    Agrège toutes les features en un dictionnaire compatible
    avec le modèle scikit-learn (même ordre que à l'entraînement).
    """
    if not code or not code.strip():
        return _empty_features()

    lines = code.strip().split("\n")
    mean_len, std_len = extract_line_length_stats(lines)
    indent_var = extract_indentation_variance(lines)
    comment_ratio = extract_comment_ratio(lines)
    max_depth, num_branches, avg_name_len = extract_complexity_indicators(code)

    # Features supplémentaires : nombre de lignes, ratio lignes vides
    num_lines = len(lines)
    empty_ratio = sum(1 for l in lines if not l.strip()) / num_lines if num_lines else 0.0

    return {
        "mean_line_length": mean_len,
        "std_line_length": std_len,
        "indentation_variance": indent_var,
        "comment_ratio": comment_ratio,
        "max_nesting_depth": max_depth,
        "num_branches": num_branches,
        "avg_identifier_length": avg_name_len,
        "num_lines": num_lines,
        "empty_line_ratio": round(empty_ratio, 4),
    }


def _empty_features() -> dict:
    """Features par défaut pour code vide (code vide = pas de données)."""
    return {
        "mean_line_length": 0.0,
        "std_line_length": 0.0,
        "indentation_variance": 0.0,
        "comment_ratio": 0.0,
        "max_nesting_depth": 0,
        "num_branches": 0,
        "avg_identifier_length": 0.0,
        "num_lines": 0,
        "empty_line_ratio": 0.0,
    }


def explain_features(features: dict, score_ia: float) -> List[str]:
    """
    Analyse les features et le score pour générer des 'raisons' vulgaires
    expliquant pourquoi le modèle considère le code comme écrit par une IA.
    """
    reasons = []
    
    if score_ia < 0.35:
        return reasons
    
    # 1. Variance d'indentation trop faible
    indent_var = features.get("indentation_variance", 10.0)
    if indent_var < 2.0:
        reasons.append("Indentation milimétrée (variance < 2.0)")
    
    # 2. Longueur des lignes constante
    std_len = features.get("std_line_length", 20.0)
    if std_len < 12.0:
        reasons.append("Lignes de longueurs trop régulières (écart-type faible)")
        
    # 3. Ratio de commentaires 
    comment_ratio = features.get("comment_ratio", 0.0)
    if comment_ratio > 0.4:
        reasons.append("Densité de commentaires suspecte (style prompt)")
    elif comment_ratio == 0.0 and features.get("num_lines", 0) > 30:
        reasons.append("Aucun commentaire pour un code long (typique IA brute)")
        
    # 4. Longueur des variables
    avg_name = features.get("avg_identifier_length", 5.0)
    if avg_name > 15.0:
        reasons.append("Noms de variables/fonctions très explicites et longs (>15 char)")
        
    # 5. Complexité vs ratio vide
    empty_ratio = features.get("empty_line_ratio", 0.1)
    if empty_ratio < 0.05 and features.get("num_lines", 0) > 20:
        reasons.append("Code extrêmement dense sans aération (ratio vide < 5%)")

    # Si rien de spécifique n'est trouvé mais le score est fort
    if not reasons and score_ia >= 0.65:
        reasons.append("Structure cyclomatique globale correspondant au profil LLM")
        
    return reasons


# Ordre des colonnes pour le modèle (doit correspondre à l'entraînement)
FEATURE_NAMES = [
    "mean_line_length",
    "std_line_length",
    "indentation_variance",
    "comment_ratio",
    "max_nesting_depth",
    "num_branches",
    "avg_identifier_length",
    "num_lines",
    "empty_line_ratio",
]


def features_to_vector(features: dict) -> List[float]:
    """Convertit le dictionnaire de features en vecteur dans l'ordre attendu."""
    return [features.get(name, 0.0) for name in FEATURE_NAMES]
