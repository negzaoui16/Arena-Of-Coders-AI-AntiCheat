"""
TEST COMPLET : chaque utilisateur (lien GitHub) -> RESULTAT FINAL : il triche ou non.
Utilise le modèle déployé sur Hugging Face.

Usage (tout utilisateur peut lancer) :
  python scripts/test_complet_user.py https://github.com/user1/repo1
  python scripts/test_complet_user.py https://github.com/user1/repo1 https://github.com/user2/repo2
  python scripts/test_complet_user.py   (démo : vérifie le modèle avec 1 code OK + 1 code "cheat", puis demande une URL)

À la fin : pour chaque user/repo, affiche clairement CET UTILISATEUR TRICHE / NE TRICHE PAS / SUSPECT.
"""
import json
import base64
import urllib.request
import urllib.error
import re
import sys

BASE_API = "https://negzaoui-anti-cheat-coding.hf.space"
CODE_EXTENSIONS = (".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".cs", ".rb", ".php", ".swift", ".kt")
MAX_CODE_LENGTH = 200000

# Codes de démo pour vérifier que le modèle fonctionne (OK vs CHEAT)
CODE_DEMO_OK = "def hello():\n    print('world')"
CODE_DEMO_CHEAT = "def binary_search(arr, x):\n    low, high = 0, len(arr)-1\n    while low <= high:\n        mid = (low+high)//2\n        if arr[mid] == x: return mid\n        if arr[mid] < x: low = mid+1\n        else: high = mid-1\n    return -1"


def parse_github_url(url_or_slug):
    url_or_slug = url_or_slug.strip()
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+))?/?", url_or_slug)
    if m:
        owner, repo, ref = m.group(1), m.group(2), m.group(3)
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo, ref
    if "/" in url_or_slug and " " not in url_or_slug:
        parts = url_or_slug.split("/", 1)
        return parts[0], parts[1], None
    raise ValueError("URL invalide. Exemple: https://github.com/owner/repo")


def fetch_contents(owner, repo, path="", ref=None):
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
    if item.get("encoding") == "base64" and item.get("content"):
        return base64.b64decode(item.get("content", "")).decode("utf-8", errors="replace")
    url = item.get("download_url")
    if url:
        req = urllib.request.Request(url, headers={"User-Agent": "AntiCheat-GitHub-Analyzer"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="replace")
    return ""


def collect_code(owner, repo, path="", ref=None, collected=None):
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


def api_analyze(code):
    body = json.dumps({"code": code}).encode("utf-8")
    req = urllib.request.Request(
        BASE_API + "/analyze",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def verdict_final(verdict_api):
    if verdict_api == "OK":
        return "NE TRICHE PAS"
    if verdict_api == "SUSPECT":
        return "SUSPECT"
    return "TRICHE"


def run_demo_verification():
    """Vérifie que le modèle HF répond bien (1 code OK -> OK, 1 code cheat -> SUSPECT/TRICHE)."""
    print("=" * 60)
    print("  VERIFICATION DU MODELE (Hugging Face)")
    print("=" * 60)
    try:
        r1 = api_analyze(CODE_DEMO_OK)
        r2 = api_analyze(CODE_DEMO_CHEAT)
    except Exception as e:
        print("  ERREUR API:", e)
        return False
    v1 = r1.get("verdict", "?")
    v2 = r2.get("verdict", "?")
    print("  Code OK (humain)  : verdict =", v1, "| score_ia =", r1.get("score_ia"))
    print("  Code CHEAT (IA)   : verdict =", v2, "| score_ia =", r2.get("score_ia"))
    if v1 == "OK" and v2 in ("SUSPECT", "TRICHE PROBABLE"):
        print("  >> Modele OK : distingue bien humain vs IA.")
    else:
        print("  >> Modele repond (verifier les seuils si besoin).")
    print("=" * 60)
    print()
    return True


def test_one_user(github_url):
    """Analyse le repo GitHub d'un utilisateur, retourne (owner, repo, verdict, score_ia, final_score)."""
    try:
        owner, repo, ref = parse_github_url(github_url)
    except ValueError as e:
        return (None, None, "ERREUR", 0, 0, str(e))
    try:
        files = collect_code(owner, repo, ref=ref)
    except Exception as e:
        return (owner, repo, "ERREUR", 0, 0, str(e))
    if not files:
        return (owner, repo, "ERREUR", 0, 0, "Aucun fichier de code (.py, .js, etc.). Verifiez que l'URL est un vrai repo avec du code.")
    full_code = "\n\n".join(f"[Fichier: {path}]\n{content}" for path, content in files)
    if len(full_code) > MAX_CODE_LENGTH:
        full_code = full_code[:MAX_CODE_LENGTH] + "\n\n... (tronque)"
    try:
        result = api_analyze(full_code)
    except Exception as e:
        return (owner, repo, "ERREUR", 0, 0, str(e))
    verdict = result.get("verdict", "?")
    score_ia = result.get("score_ia", 0)
    final_score = result.get("final_score", 0)
    return (owner, repo, verdict, score_ia, final_score, None)


def main():
    urls = [a.strip() for a in sys.argv[1:] if a.strip()]
    print()
    print("=" * 60)
    print("  TEST COMPLET - MODELE ANTI-TRICHE (Hugging Face)")
    print("  API:", BASE_API)
    print("=" * 60)
    print()

    # 1) Démo : vérifier que le modèle répond (1 user OK, 1 user "cheat")
    run_demo_verification()

    if not urls:
        print("Usage: python scripts/test_complet_user.py <URL GitHub> [URL2 ...]")
        print()
        print("Exemple (vraie URL) :")
        print("  python scripts/test_complet_user.py https://github.com/negzaoui16/anti-cheat-coding")
        print()
        print("Ne pas utiliser UTILISATEUR/REPO : ce n'est qu'un exemple. Utilisez un vrai repo GitHub.")
        return 0

    # Avertissement si l'utilisateur a mis le placeholder
    for url in urls:
        if "UTILISATEUR" in url.upper() or "/REPO" in url.upper():
            print("ATTENTION : UTILISATEUR/REPO n'est pas un vrai repo. Utilisez une vraie URL, ex:")
            print("  python scripts/test_complet_user.py https://github.com/negzaoui16/anti-cheat-coding")
            print()
            break

    # 2) Pour chaque URL : analyse + résultat final
    results = []
    for i, url in enumerate(urls, 1):
        print("=" * 60)
        print(f"  UTILISATEUR {i}/{len(urls)} : {url}")
        print("=" * 60)
        t = test_one_user(url)
        owner, repo, verdict, score_ia, final_score, err = t
        if verdict == "ERREUR":
            print("  Erreur:", err or "inconnue")
            results.append((owner or "?", repo or "?", "ERREUR"))
            print()
            continue
        print(f"  Repo     : {owner}/{repo}")
        print(f"  score_ia : {score_ia:.2f}  (0 = humain, 1 = IA)")
        print(f"  verdict  : {verdict}")
        print()
        v_final = verdict_final(verdict)
        print("  " + "-" * 50)
        if v_final == "NE TRICHE PAS":
            print("  RESULTAT FINAL : CET UTILISATEUR NE TRICHE PAS")
        elif v_final == "SUSPECT":
            print("  RESULTAT FINAL : CET UTILISATEUR EST SUSPECT (a verifier)")
        else:
            print("  RESULTAT FINAL : CET UTILISATEUR TRICHE")
        print("  " + "-" * 50)
        results.append((owner, repo, v_final))
        print()

    # 3) Tableau récapitulatif
    print("=" * 60)
    print("  RECAPITULATIF - TOUS LES UTILISATEURS")
    print("=" * 60)
    print()
    print("  | User (owner) | Repo           | Resultat        |")
    print("  |--------------|----------------|-----------------|")
    for owner, repo, v in results:
        owner_short = (owner or "?")[:14]
        repo_short = (repo or "?")[:14]
        print(f"  | {owner_short:14} | {repo_short:14} | {v:15} |")
    print()
    print("  Resultat : NE TRICHE PAS = OK  |  SUSPECT = a verifier  |  TRICHE = triche probable")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
