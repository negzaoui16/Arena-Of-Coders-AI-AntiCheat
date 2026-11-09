"""
API REST FastAPI pour l'analyse anti-triche.
POST /analyze : analyse du code + statistiques de frappe + paramètres room.
Apprentissage continu AUTOMATIQUE : le modèle apprend tout seul avec le temps.
- Auto-labellise les cas extrêmes (haute confiance)
- Ré-entraîne automatiquement après N soumissions
"""
import threading
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse
from pathlib import Path
from pydantic import BaseModel, Field

from config import (
    DEFAULT_MODEL_VERSION, HF_REPO, HF_TOKEN, RETRAIN_SECRET,
    AUTO_LEARN_ENABLED, AUTO_LABEL_HUMAN_THRESHOLD, AUTO_LABEL_IA_THRESHOLD,
    AUTO_RETRAIN_EVERY_N, AUTO_RETRAIN_MIN_SAMPLES,
)
from src.model_ia import (
    predict_ia_score,
    load_model,
    set_global_model,
    load_model_from_hub,
    push_model_to_hub,
)
from src.features import extract_all_features, explain_features
from src.copy_paste import copy_paste_detected
from src.plagiarism import PlagiarismChecker
from src.scoring import analyze as compute_analysis_result
from src.storage import store_prediction, push_storage_to_hub, load_storage_from_hub

# Chargement une fois du vérificateur de plagiat (solutions existantes)
_plagiarism_checker: Optional[PlagiarismChecker] = None

# Compteur pour auto-retrain
_auto_learn_counter: int = 0
_auto_learn_lock = threading.Lock()


def get_plagiarism_checker() -> PlagiarismChecker:
    global _plagiarism_checker
    if _plagiarism_checker is None:
        _plagiarism_checker = PlagiarismChecker()
    return _plagiarism_checker


def _auto_label_and_maybe_retrain(submission_id: str, score_ia: float):
    """
    Apprentissage automatique :
    1. Auto-labellise si score_ia est extrême (haute confiance)
    2. Déclenche retrain après N nouvelles décisions
    """
    global _auto_learn_counter

    if not AUTO_LEARN_ENABLED or not HF_REPO or not HF_TOKEN:
        return

    from src.storage import store_human_decision, load_human_decisions

    # 1. Auto-labellisation des cas extrêmes
    auto_label = None
    if score_ia < AUTO_LABEL_HUMAN_THRESHOLD:
        auto_label = 0  # Très probablement humain
    elif score_ia > AUTO_LABEL_IA_THRESHOLD:
        auto_label = 1  # Très probablement IA

    if auto_label is not None:
        store_human_decision(submission_id, auto_label, f"auto-label (score_ia={score_ia:.2f})")
        
        with _auto_learn_lock:
            _auto_learn_counter += 1
            counter = _auto_learn_counter

        # 2. Ré-entraînement automatique après N décisions
        if counter >= AUTO_RETRAIN_EVERY_N:
            try:
                decisions = load_human_decisions()
                if len(decisions) >= AUTO_RETRAIN_MIN_SAMPLES:
                    _do_auto_retrain()
                    with _auto_learn_lock:
                        _auto_learn_counter = 0
            except Exception:
                pass  # Silencieux en cas d'erreur


def _do_auto_retrain():
    """Exécute le ré-entraînement automatique (en arrière-plan)."""
    try:
        from src.training import run_training
        # 1) Sync storage
        push_storage_to_hub(HF_REPO, HF_TOKEN)
        # 2) Retrain
        result = run_training(min_samples=AUTO_RETRAIN_MIN_SAMPLES, version="latest")
        if result.get("error"):
            return
        # 3) Recharger et pousser le modèle
        clf = load_model("latest")
        if clf is not None:
            set_global_model(clf)
            push_model_to_hub("latest", HF_REPO, HF_TOKEN)
    except Exception:
        pass  # Silencieux


# --- Schémas Pydantic ---

class TypingStats(BaseModel):
    """Statistiques de frappe (optionnel)."""
    total_typing_time_ms: Optional[int] = None
    total_time_ms: Optional[int] = None
    block_insertions: Optional[list] = None
    events: Optional[list] = None


class RoomParams(BaseModel):
    """Paramètres de la room (coding challenge)."""
    allow_ai: Optional[bool] = True
    anti_cheat_enabled: Optional[bool] = True
    room_type: Optional[str] = None


class AnalyzeRequest(BaseModel):
    code: str = Field(..., description="Code source à analyser")
    typing_stats: Optional[Dict[str, Any]] = Field(None, description="Statistiques de frappe")
    room_params: Optional[Dict[str, Any]] = Field(None, description="Paramètres de la room")
    submission_id: Optional[str] = Field(None, description="ID de la soumission (pour lien avec décision humaine)")


class AnalyzeResponse(BaseModel):
    score_ia: float
    score_plagiat: float
    copy_paste_detected: bool
    score_copy_paste: float
    final_score: float
    verdict: str
    submission_id: Optional[str] = None


app = FastAPI(
    title="API Anti-triche - Coding Challenges",
    description="Analyse du code pour détecter IA, plagiat et copier-coller. Retourne un score de suspicion, pas de blocage automatique. Apprentissage continu via Hub + /retrain.",
    version="0.1.0",
)


@app.on_event("startup")
def startup():
    """Au démarrage : récupérer storage et modèle depuis le Hub si configuré."""
    if not HF_REPO or not HF_TOKEN:
        return
    load_storage_from_hub(HF_REPO, HF_TOKEN)
    if load_model_from_hub(HF_REPO, HF_TOKEN):
        pass  # modèle Hub chargé et défini comme global
    else:
        # Fallback : utiliser le modèle disque (v1 au premier run)
        clf = load_model(DEFAULT_MODEL_VERSION)
        if clf is not None:
            set_global_model(clf)


@app.get("/", response_class=HTMLResponse)
def root():
    """Page d'accueil : Interface UI."""
    template_path = Path(__file__).parent / "templates" / "index.html"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content=f.read(),
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    
    # Fallback to simple UI
    auto_status = "activé" if AUTO_LEARN_ENABLED else "désactivé"
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Anti Cheat Coding API</title></head>
    <body style="font-family: sans-serif; max-width: 600px; margin: 2rem auto; padding: 1rem;">
    <h1>🔒 API Anti-triche Coding</h1>
    <p>L'API est en ligne. L'interface Web n'a pas pu être chargée.</p>
    <ul>
    <li><a href="/docs">/docs</a> — Documentation interactive (Swagger)</li>
    <li><a href="/health">/health</a> — Vérifier que l'API répond</li>
    </ul>
    </body>
    </html>
    """


@app.get("/health")
def health():
    """Santé de l'API."""
    return {"status": "ok"}


@app.get("/auto_learn_status")
def auto_learn_status():
    """
    Retourne l'état de l'apprentissage automatique.
    - enabled : True si AUTO_LEARN_ENABLED
    - counter : nombre de décisions auto depuis le dernier retrain
    - retrain_every : déclenche retrain après N décisions
    - thresholds : seuils pour auto-labellisation
    """
    from src.storage import load_human_decisions, load_predictions
    decisions = load_human_decisions()
    predictions = load_predictions()
    auto_decisions = [d for d in decisions if "auto-label" in (d.get("comment") or "")]
    return {
        "enabled": AUTO_LEARN_ENABLED,
        "counter_since_last_retrain": _auto_learn_counter,
        "retrain_every_n": AUTO_RETRAIN_EVERY_N,
        "min_samples_for_retrain": AUTO_RETRAIN_MIN_SAMPLES,
        "thresholds": {
            "human": AUTO_LABEL_HUMAN_THRESHOLD,
            "ia": AUTO_LABEL_IA_THRESHOLD,
        },
        "total_predictions": len(predictions),
        "total_decisions": len(decisions),
        "auto_labeled_decisions": len(auto_decisions),
        "hf_configured": bool(HF_REPO and HF_TOKEN),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_code(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Analyse le code et retourne les scores + verdict.
    - score_ia : probabilité code généré par IA (0-1)
    - score_plagiat : similarité max avec solutions existantes (0-1)
    - copy_paste_detected : booléen
    - final_score : combinaison pondérée
    - verdict : OK / SUSPECT / TRICHE PROBABLE
    
    APPRENTISSAGE AUTOMATIQUE : si AUTO_LEARN_ENABLED=true, le modèle :
    - Auto-labellise les cas extrêmes (score_ia < 0.15 ou > 0.85)
    - Se ré-entraîne automatiquement après 20 nouvelles décisions
    """
    code = request.code or ""
    typing_stats = request.typing_stats
    room_params = request.room_params or {}
    submission_id = request.submission_id

    # 1. Score IA (modèle ML, global ou disque)
    score_ia = predict_ia_score(code)

    # 2. Score plagiat (TF-IDF + cosine)
    plagiarism_checker = get_plagiarism_checker()
    score_plagiat = plagiarism_checker.score(code)

    # 3. Copier-coller (règles)
    cp_detected, score_copy_paste = copy_paste_detected(code, typing_stats)

    # 4. Score final et verdict
    result = compute_analysis_result(
        score_ia=score_ia,
        score_plagiat=score_plagiat,
        copy_paste_detected=cp_detected,
        score_copy_paste=score_copy_paste,
    )

    # Stockage pour apprentissage continu (si activé)
    sid = submission_id or f"sub_{abs(hash(code)) % 10**10}"
    store_prediction(sid, code, result, room_params)

    # 5. APPRENTISSAGE AUTOMATIQUE (en arrière-plan pour ne pas ralentir la réponse)
    background_tasks.add_task(_auto_label_and_maybe_retrain, sid, score_ia)

    return AnalyzeResponse(
        submission_id=sid,
        **result,
    )


# --- Analyse GitHub ---

class AnalyzeGitHubRequest(BaseModel):
    github_url: str = Field(..., description="URL du repo GitHub (ex: https://github.com/user/repo)")
    submission_id: Optional[str] = Field(None, description="ID de la soumission")


class AnalyzeGitHubResponse(BaseModel):
    github_url: str
    owner: str
    repo: str
    files_analyzed: int
    scores: list
    avg_score_ia: float
    final_verdict: str
    global_summary: Optional[str] = None
    submission_id: Optional[str] = None
    details: list


def _fetch_github_files(owner: str, repo: str, ref: Optional[str] = None) -> list:
    """Récupère les fichiers de code d'un repo GitHub."""
    import urllib.request
    import json
    
    code_extensions = (".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".cs", ".rb", ".php", ".dart", ".swift", ".kt", ".html", ".css", ".jsx", ".tsx")
    collected = []
    
    def fetch_contents(path=""):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        if ref:
            url += f"?ref={ref}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AntiCheat-API"
        }
        
        import os
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"
            
        req = urllib.request.Request(
            url,
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    
    def get_file_content(item):
        download_url = item.get("download_url")
        if download_url:
            req = urllib.request.Request(download_url, headers={"User-Agent": "AntiCheat-API"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", errors="replace")
        return ""
    
    def collect(path=""):
        try:
            data = fetch_contents(path)
        except Exception as e:
            if not path:
                if "403" in str(e):
                    raise Exception("Limite d'API GitHub atteinte pour ce serveur (trop de requêtes). Veuillez réessayer plus tard.")
                raise Exception(f"Dépôt introuvable ou privé ({e})")
            return
        if not isinstance(data, list):
            data = [data]
        for item in data:
            name = item.get("name", "")
            if item.get("type") == "file":
                if any(name.lower().endswith(ext) for ext in code_extensions):
                    try:
                        content = get_file_content(item)
                        if content.strip():
                            file_path = path + "/" + name if path else name
                            collected.append({"path": file_path, "content": content})
                    except Exception:
                        pass
            elif item.get("type") == "dir":
                dir_name = item.get("name")
                if dir_name not in (".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"):
                    dir_path = path + "/" + dir_name if path else dir_name
                    collect(dir_path)
    
    collect()
    return collected


@app.post("/analyze_github", response_model=AnalyzeGitHubResponse)
def analyze_github(request: AnalyzeGitHubRequest, background_tasks: BackgroundTasks):
    """
    Analyse un repo GitHub complet.
    
    Le user envoie un lien GitHub (ex: https://github.com/user/repo),
    l'API récupère tous les fichiers de code et les analyse.
    
    Retourne :
    - avg_score_ia : score IA moyen sur tous les fichiers
    - final_verdict : NE TRICHE PAS / SUSPECT / TRICHE PROBABLE
    - details : score par fichier
    """
    import re
    
    github_url = request.github_url.strip()
    
    # Parser l'URL GitHub
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+))?/?", github_url)
    if not match:
        # Essayer format simple user/repo
        if "/" in github_url and " " not in github_url:
            parts = github_url.replace("https://github.com/", "").replace(".git", "").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                ref = None
            else:
                raise HTTPException(status_code=400, detail="URL GitHub invalide. Exemple: https://github.com/user/repo")
        else:
            raise HTTPException(status_code=400, detail="URL GitHub invalide. Exemple: https://github.com/user/repo")
    else:
        owner, repo, ref = match.group(1), match.group(2), match.group(3)
    
    if repo.endswith(".git"):
        repo = repo[:-4]
    
    # Récupérer les fichiers
    try:
        files = _fetch_github_files(owner, repo, ref)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Impossible de récupérer le repo: {str(e)}")
    
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier de code trouvé dans ce repo")
    
    # Analyser chaque fichier (max 20 pour éviter timeout)
    max_files = 20
    files_to_analyze = files[:max_files]
    
    plagiarism_checker = get_plagiarism_checker()
    scores = []
    details = []
    
    for file_info in files_to_analyze:
        file_path = file_info["path"]
        code = file_info["content"][:100000]  # Limiter la taille
        
        # Extraire explicitement les features pour l'explication
        features = extract_all_features(code)
        
        # Calculer les scores
        score_ia = predict_ia_score(code)  # Note: predict_ia_score l'extrait aussi en interne, c'est léger
        score_plagiat = plagiarism_checker.score(code)
        cp_detected, score_copy_paste = copy_paste_detected(code, None)
        
        # Extraire les raisons de suspicion
        reasons = explain_features(features, score_ia)
        
        result = compute_analysis_result(
            score_ia=score_ia,
            score_plagiat=score_plagiat,
            copy_paste_detected=cp_detected,
            score_copy_paste=score_copy_paste,
        )
        
        scores.append(score_ia)
        details.append({
            "file": file_path,
            "score_ia": round(score_ia, 2),
            "verdict": result["verdict"],
            "reasons": reasons
        })
    
    # Calculer le score moyen et le verdict final
    avg_score = sum(scores) / len(scores) if scores else 0
    
    if avg_score < 0.4:
        final_verdict = "NE TRICHE PAS"
    elif avg_score < 0.65:
        final_verdict = "SUSPECT"
    else:
        final_verdict = "TRICHE PROBABLE"
    
    # Enregistrer la prédiction
    sid = request.submission_id or f"github_{owner}_{repo}_{abs(hash(github_url)) % 10**8}"
    full_code = "\n\n".join(f["content"] for f in files_to_analyze)
    store_prediction(sid, full_code[:200000], {
        "score_ia": avg_score,
        "score_plagiat": 0,
        "copy_paste_detected": False,
        "score_copy_paste": 0,
        "final_score": avg_score,
        "verdict": final_verdict,
    }, {"github_url": github_url, "room_type": "github_project"})
    
    # Auto-Validation (Fast Learning) for GitHub projects
    # Chaque analyse GitHub est automatiquement enregistrée comme échantillon d'entraînement
    from src.storage import store_human_decision
    if avg_score >= 0.5:
        store_human_decision(sid, 1, f"Auto-Validation (Score {avg_score:.2f}: Probablement IA)")
    else:
        store_human_decision(sid, 0, f"Auto-Validation (Score {avg_score:.2f}: Probablement Humain)")
        
    # Auto-learn en arrière-plan
    background_tasks.add_task(_auto_label_and_maybe_retrain, sid, avg_score)
    
    # Résumé Global
    global_summary = None
    if final_verdict in ("SUSPECT", "TRICHE PROBABLE"):
        from collections import Counter
        all_reasons = []
        for d in details:
            if d.get("reasons"):
                all_reasons.extend(d["reasons"])
        
        if all_reasons:
            most_common = [r[0] for r in Counter(all_reasons).most_common(2)]
            global_summary = f"Le projet a été signalé avec un score de {round(avg_score*100)}% car il présente de fortes caractéristiques temporelles de l'IA. Principalement : " + " et ".join([f"**{r.lower()}**" for r in most_common]) + " sur une majorité de fichiers."
    
    return AnalyzeGitHubResponse(
        github_url=github_url,
        owner=owner,
        repo=repo,
        files_analyzed=len(files_to_analyze),
        scores=scores,
        avg_score_ia=round(avg_score, 4),
        final_verdict=final_verdict,
        global_summary=global_summary,
        submission_id=sid,
        details=details,
    )


class HumanDecisionRequest(BaseModel):
    submission_id: str = Field(..., description="ID de la soumission (retourné par POST /analyze)")
    human_label: int = Field(..., description="0 = OK / humain, 1 = triche / IA")
    comment: Optional[str] = None


@app.post("/human_decision")
def record_human_decision(body: HumanDecisionRequest):
    """
    Enregistre la décision humaine finale (pour ré-entraînement).
    human_label : 0 = OK / humain, 1 = triche / IA.
    """
    from src.storage import store_human_decision
    if body.human_label not in (0, 1):
        raise HTTPException(status_code=400, detail="human_label doit être 0 ou 1")
    store_human_decision(body.submission_id, body.human_label, body.comment)
    return {"status": "recorded", "submission_id": body.submission_id}


def _check_retrain_secret(x_secret: Optional[str] = Header(None, alias="X-Retrain-Secret")):
    """Protection de POST /retrain."""
    EXPECTED_SECRET = "NEGzaoui1234"
    if x_secret != EXPECTED_SECRET:
        raise HTTPException(status_code=403, detail="Mot de passe invalide")


@app.post("/sync_storage")
def sync_storage_to_hub():
    """
    Envoie le storage local (predictions + human_decisions) vers le repo HF.
    Utile pour ne pas perdre les données avant un redémarrage du Space.
    Nécessite HF_REPO et HF_TOKEN en env.
    """
    if not HF_REPO or not HF_TOKEN:
        raise HTTPException(status_code=503, detail="HF_REPO / HF_TOKEN non configurés")
    result = push_storage_to_hub(HF_REPO, HF_TOKEN)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error", "Erreur sync"))
    return {"status": "ok", "uploaded": result.get("uploaded", [])}


@app.post("/retrain")
def trigger_retrain(
    min_samples: int = 1,
    _: None = Depends(_check_retrain_secret),
):
    """
    Ré-entraîne le modèle à partir des décisions humaines enregistrées,
    sauvegarde comme modèle "latest", pousse vers le Hub et recharge le modèle en mémoire.
    Le modèle devient plus intelligent avec le temps si tu appelles /human_decision puis /retrain.
    Protégé par X-Retrain-Secret si RETRAIN_SECRET est défini.
    """
    if not HF_REPO or not HF_TOKEN:
        raise HTTPException(status_code=503, detail="HF_REPO / HF_TOKEN non configurés")
    from src.training import run_training
    # 1) Sauvegarder le storage sur le Hub avant d'entraîner (persistance)
    push_storage_to_hub(HF_REPO, HF_TOKEN)
    # 2) Ré-entraînement (version "latest" pour le Hub)
    result = run_training(min_samples=min_samples, version="latest")
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    # 3) Recharger en mémoire et pousser le nouveau modèle vers le Hub
    clf = load_model("latest")
    if clf is not None:
        set_global_model(clf)
        push_model_to_hub("latest", HF_REPO, HF_TOKEN)
    return {
        "status": "ok",
        "version": result.get("version"),
        "accuracy": result.get("accuracy"),
        "n_samples": result.get("n_samples"),
    }
