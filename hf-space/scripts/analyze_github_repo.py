"""
Analyse le code d'un dépôt GitHub pour vérifier s'il est probablement humain ou écrit avec un modèle IA.

Usage :
  python scripts/analyze_github_repo.py https://github.com/owner/repo
  python scripts/analyze_github_repo.py owner/repo

Le script récupère les fichiers de code du repo (API GitHub), les envoie à l'API anti-triche,
puis affiche score_ia et verdict (humain vs IA).
"""
import json
import base64
import urllib.request
import re
import sys

# API anti-triche (Space HF)
BASE_API = "https://negzaoui-anti-cheat-coding.hf.space"

# Extensions de fichiers à inclure dans l'analyse
CODE_EXTENSIONS = (".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".cs", ".rb", ".php", ".swift", ".kt")

# Taille max du code envoyé (caractères) pour éviter des requêtes trop lourdes
MAX_CODE_LENGTH = 200000


def parse_github_url(url_or_slug):
    """Retourne (owner, repo, ref). ref = None pour défaut (main/master)."""
    url_or_slug = url_or_slug.strip()
    # https://github.com/owner/repo ou https://github.com/owner/repo/tree/branch
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+))?/?", url_or_slug)
    if m:
        owner, repo, ref = m.group(1), m.group(2), m.group(3)
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo, ref
    # owner/repo
    if "/" in url_or_slug and " " not in url_or_slug:
        parts = url_or_slug.split("/", 1)
        return parts[0], parts[1], None
    raise ValueError("URL ou slug invalide. Exemples: https://github.com/owner/repo  ou  owner/repo")


def fetch_contents(owner, repo, path="", ref=None):
    """Récupère le contenu d'un dossier (liste de fichiers/dossiers) via l'API GitHub."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "AntiCheat-GitHub-Analyzer"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def get_file_content(item):
    """Récupère le contenu d'un fichier : base64 dans la réponse ou via download_url."""
    if item.get("encoding") == "base64" and item.get("content"):
        return base64.b64decode(item.get("content", "")).decode("utf-8", errors="replace")
    # Quand on liste un dossier, l'API ne renvoie pas "content" ; on utilise download_url (fichier brut)
    url = item.get("download_url")
    if url:
        req = urllib.request.Request(url, headers={"User-Agent": "AntiCheat-GitHub-Analyzer"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="replace")
    return ""


def collect_code(owner, repo, path="", ref=None, collected=None):
    """Parcourt le repo et concatène le contenu des fichiers de code."""
    if collected is None:
        collected = []
    try:
        data = fetch_contents(owner, repo, path, ref)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return collected
        raise
    if not isinstance(data, list):
        data = [data]
    for item in data:
        name = item.get("name", "")
        if item.get("type") == "file":
            if any(name.lower().endswith(ext) for ext in CODE_EXTENSIONS):
                try:
                    content = get_file_content(item)
                    if content.strip():
                        collected.append((path + "/" + name if path else name, content))
                except Exception:
                    pass
        elif item.get("type") == "dir":
            dir_path = path + "/" + name if path else name
            if dir_path not in (".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"):
                collect_code(owner, repo, dir_path, ref, collected)
    return collected


def analyze_code(code):
    """Envoie le code à l'API anti-triche et retourne le résultat."""
    body = json.dumps({"code": code}).encode("utf-8")
    req = urllib.request.Request(
        BASE_API + "/analyze",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_github_repo.py <URL GitHub ou owner/repo>")
        print("Exemple: python scripts/analyze_github_repo.py https://github.com/owner/repo")
        return 1
    url_or_slug = sys.argv[1]
    try:
        owner, repo, ref = parse_github_url(url_or_slug)
    except ValueError as e:
        print("Erreur:", e)
        return 1
    print("=" * 55)
    print("  ANALYSE CODE GITHUB (humain vs IA)")
    print("=" * 55)
    print(f"\nRepo: {owner}/{repo}" + (f" (ref: {ref})" if ref else ""))
    print("Recuperation des fichiers de code...")
    try:
        files = collect_code(owner, repo, ref=ref)
    except urllib.error.HTTPError as e:
        print("Erreur GitHub API:", e.code, e.read().decode()[:200])
        return 1
    except Exception as e:
        print("Erreur:", e)
        return 1
    if not files:
        print("Aucun fichier de code trouve (.py, .js, .ts, .java, etc.).")
        return 1
    full_code = "\n\n".join(f"[Fichier: {path}]\n{content}" for path, content in files)
    if len(full_code) > MAX_CODE_LENGTH:
        full_code = full_code[:MAX_CODE_LENGTH] + "\n\n... (tronque)"
    print(f"  {len(files)} fichier(s) recupere(s), {len(full_code)} caracteres.")
    print("\nEnvoi a l'API anti-triche...")
    try:
        result = analyze_code(full_code)
    except Exception as e:
        print("Erreur API:", e)
        return 1
    score_ia = result.get("score_ia", 0)
    verdict = result.get("verdict", "?")
    final_score = result.get("final_score", 0)
    print("\n" + "=" * 55)
    print("  RESULTAT")
    print("=" * 55)
    print(f"  score_ia      : {score_ia:.2f}  (0 = humain, 1 = IA)")
    print(f"  verdict       : {verdict}")
    print(f"  final_score  : {final_score:.2f}")
    if score_ia < 0.35:
        interpretation = "Probablement ecrit par un humain."
    elif score_ia < 0.65:
        interpretation = "Suspect (mixte ou style IA)."
    else:
        interpretation = "Probablement ecrit avec un modele IA."
    print(f"\n  >> {interpretation}")
    print("=" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
