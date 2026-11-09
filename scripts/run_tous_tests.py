"""
UN SEUL FICHIER = TOUS LES TESTS.
Execute tout : health, seed 12, analyze, human_decision, sync, retrain,
reponse modele (OK vs CHEAT), analyse repo GitHub.

Usage : python scripts/run_tous_tests.py
        python scripts/run_tous_tests.py [URL_GITHUB]   (optionnel, defaut: negzaoui16/anti-cheat-coding)

Change BASE si tu testes en local (http://localhost:7860).
"""
import json
import base64
import re
import urllib.request
import urllib.error
import sys

BASE = "https://negzaoui-anti-cheat-coding.hf.space"
RETRAIN_SECRET = ""
DEFAULT_GITHUB_REPO = "https://github.com/negzaoui16/anti-cheat-coding.git"

CODE_EXTENSIONS = (".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".cs", ".rb", ".php", ".swift", ".kt")
MAX_CODE_LENGTH = 200000

SAMPLES = [
    ("def hello():\n    print('world')", 0),
    ("x = 1\ny = 2\nprint(x + y)", 0),
    ("for i in range(5):\n    print(i * 2)", 0),
    ("def add(a, b):\n    return a + b", 0),
    ("lst = [1, 2, 3]\nprint(sum(lst))", 0),
    ("s = 'hello'\nprint(s.upper())", 0),
    ("def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1)+fibonacci(n-2)", 1),
    ("def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)", 1),
    ("def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5)+1):\n        if n % i == 0:\n            return False\n    return True", 1),
    ("class Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n        for i, v in enumerate(nums):\n            if target - v in seen:\n                return [seen[target-v], i]\n            seen[v] = i", 1),
    ("def reverse_string(s):\n    return s[::-1] if s else ''", 1),
    ("def binary_search(arr, x):\n    low, high = 0, len(arr)-1\n    while low <= high:\n        mid = (low+high)//2\n        if arr[mid] == x: return mid\n        if arr[mid] < x: low = mid+1\n        else: high = mid-1\n    return -1", 1),
]
CODE_OK = "def hello():\n    print('world')"
CODE_CHEAT = "def binary_search(arr, x):\n    low, high = 0, len(arr)-1\n    while low <= high:\n        mid = (low+high)//2\n        if arr[mid] == x: return mid\n        if arr[mid] < x: low = mid+1\n        else: high = mid-1\n    return -1"


def req(method, path, body=None, timeout=30):
    h = {"Content-Type": "application/json"}
    if RETRAIN_SECRET and "retrain" in path:
        h["X-Retrain-Secret"] = RETRAIN_SECRET
    r = urllib.request.Request(BASE + path, data=body, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def test_health():
    print("\n" + "=" * 55)
    print("  [1] GET /health")
    print("=" * 55)
    with urllib.request.urlopen(urllib.request.Request(BASE + "/health"), timeout=15) as r:
        print("  Reponse:", r.read().decode())
    print()


def test_seed_12():
    print("=" * 55)
    print("  [2] SEED 12 DECISIONS (6 OK + 6 CHEAT)")
    print("=" * 55)
    for i, (code, label) in enumerate(SAMPLES, 1):
        body = json.dumps({"code": code}).encode("utf-8")
        r = req("POST", "/analyze", body, timeout=30)
        sid = r.get("submission_id")
        tag = "OK" if label == 0 else "CHEAT"
        body2 = json.dumps({"submission_id": sid, "human_label": label, "comment": f"seed #{i} {tag}"}).encode("utf-8")
        urllib.request.urlopen(
            urllib.request.Request(BASE + "/human_decision", data=body2, method="POST", headers={"Content-Type": "application/json"}),
            timeout=15,
        )
        print(f"  {i}/12 ok (submission_id={sid}, {tag})")
    print("  Termine.\n")


def test_analyze_human_sync_retrain():
    print("=" * 55)
    print("  [3] ANALYZE + HUMAN_DECISION + SYNC + RETRAIN")
    print("=" * 55)
    print("\n  POST /analyze")
    body = json.dumps({"code": CODE_OK}).encode("utf-8")
    result = req("POST", "/analyze", body)
    sid = result.get("submission_id")
    print("     submission_id:", sid, "| verdict:", result.get("verdict"))
    print("\n  POST /human_decision")
    body2 = json.dumps({"submission_id": sid, "human_label": 0, "comment": "run_tous_tests"}).encode("utf-8")
    req("POST", "/human_decision", body2, timeout=15)
    print("     OK")
    print("\n  POST /sync_storage")
    try:
        out = req("POST", "/sync_storage", b"{}", timeout=30)
        print("     Reponse:", out)
    except urllib.error.HTTPError as e:
        if e.code == 503:
            print("     (HF_REPO/HF_TOKEN non configures)")
        else:
            print("     ERREUR:", e.code)
    print("\n  POST /retrain?min_samples=10")
    try:
        out = req("POST", "/retrain?min_samples=10", b"{}", timeout=120)
        print("     Reponse:", out)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        if e.code == 503:
            print("     (HF_REPO/HF_TOKEN non configures)")
        elif e.code == 400:
            print("     (Pas assez de decisions)")
        else:
            print("     ERREUR:", e.code, body)
    except Exception as e:
        print("     ERREUR:", e)
    print()


def test_reponse_modele():
    print("=" * 55)
    print("  [4] REPONSE DU MODELE (OK vs CHEAT)")
    print("=" * 55)
    r1 = req("POST", "/analyze", json.dumps({"code": CODE_OK}).encode("utf-8"))
    print("  Code OK (humain)    : score_ia =", r1.get("score_ia"), "| verdict =", r1.get("verdict"))
    r2 = req("POST", "/analyze", json.dumps({"code": CODE_CHEAT}).encode("utf-8"))
    print("  Code CHEAT (IA)    : score_ia =", r2.get("score_ia"), "| verdict =", r2.get("verdict"))
    print()


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
    raise ValueError("URL ou slug invalide")


def fetch_github_contents(owner, repo, path="", ref=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    req_obj = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "AntiCheat-GitHub-Analyzer"},
    )
    with urllib.request.urlopen(req_obj, timeout=15) as r:
        return json.loads(r.read().decode())


def get_github_file_content(item):
    if item.get("encoding") == "base64" and item.get("content"):
        return base64.b64decode(item.get("content", "")).decode("utf-8", errors="replace")
    url = item.get("download_url")
    if url:
        req_obj = urllib.request.Request(url, headers={"User-Agent": "AntiCheat-GitHub-Analyzer"})
        with urllib.request.urlopen(req_obj, timeout=15) as r:
            return r.read().decode("utf-8", errors="replace")
    return ""


def collect_github_code(owner, repo, path="", ref=None, collected=None):
    if collected is None:
        collected = []
    try:
        data = fetch_github_contents(owner, repo, path, ref)
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
                    content = get_github_file_content(item)
                    if content.strip():
                        collected.append((path + "/" + name if path else name, content))
                except Exception:
                    pass
        elif item.get("type") == "dir":
            dir_path = path + "/" + name if path else name
            if dir_path not in (".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"):
                collect_github_code(owner, repo, dir_path, ref, collected)
    return collected


def test_github_repo(url_or_slug):
    """Analyse le repo GitHub et retourne (score_ia, verdict, final_score) ou None en cas d'erreur."""
    print("=" * 55)
    print("  [5] ANALYSE REPO GITHUB (humain vs IA)")
    print("=" * 55)
    try:
        owner, repo, ref = parse_github_url(url_or_slug)
    except ValueError as e:
        print("  Erreur:", e)
        return None
    print(f"\n  Repo: {owner}/{repo}" + (f" (ref: {ref})" if ref else ""))
    print("  Recuperation des fichiers...")
    try:
        files = collect_github_code(owner, repo, ref=ref)
    except Exception as e:
        print("  Erreur:", e)
        return None
    if not files:
        print("  Aucun fichier de code trouve.")
        return None
    full_code = "\n\n".join(f"[Fichier: {path}]\n{content}" for path, content in files)
    if len(full_code) > MAX_CODE_LENGTH:
        full_code = full_code[:MAX_CODE_LENGTH] + "\n\n... (tronque)"
    print(f"  {len(files)} fichier(s), {len(full_code)} caracteres.")
    print("  Envoi a l'API...")
    try:
        body = json.dumps({"code": full_code}).encode("utf-8")
        result = req("POST", "/analyze", body, timeout=60)
    except Exception as e:
        print("  Erreur API:", e)
        return None
    score_ia = result.get("score_ia", 0)
    verdict = result.get("verdict", "?")
    final_score = result.get("final_score", 0)
    print(f"\n  score_ia   : {score_ia:.2f}  (0 = humain, 1 = IA)")
    print(f"  verdict    : {verdict}")
    if score_ia < 0.35:
        print("  >> Probablement ecrit par un humain.")
    elif score_ia < 0.65:
        print("  >> Suspect (mixte ou style IA).")
    else:
        print("  >> Probablement ecrit avec un modele IA.")
    print()
    return {"score_ia": score_ia, "verdict": verdict, "final_score": final_score}


def test_final(github_result, github_url):
    """Affiche le TEST FINAL : verdict utilisateur (CHEAT ou OK) + score analyse GitHub."""
    print("=" * 55)
    print("  TEST FINAL - CET UTILISATEUR TRICHE OU NON ?")
    print("=" * 55)
    if github_result is None:
        print("  (Analyse GitHub non disponible - pas de verdict final)")
        print("=" * 55)
        return
    score_ia = github_result["score_ia"]
    verdict = github_result["verdict"]
    final_score = github_result["final_score"]
    print(f"\n  Repo analyse : {github_url}")
    print(f"  Score analyse GitHub :")
    print(f"    - score_ia     : {score_ia:.2f}  (0 = humain, 1 = IA)")
    print(f"    - final_score  : {final_score:.2f}")
    print(f"    - verdict API  : {verdict}")
    print()
    if verdict == "OK":
        conclusion = "OK - PAS DE TRICHE"
        detail = "Le code soumis par cet utilisateur est considere comme probablement humain."
    elif verdict == "SUSPECT":
        conclusion = "SUSPECT"
        detail = "Le code presente des signaux suspects (mixte humain/IA ou style IA). A verifier manuellement."
    else:
        conclusion = "TRICHE PROBABLE"
        detail = "Le code soumis par cet utilisateur est considere comme probablement genere par une IA (triche)."
    print("  " + "-" * 50)
    print("  VERDICT FINAL : " + conclusion)
    print("  " + "-" * 50)
    print(f"  >> {detail}")
    print("=" * 55)


def main():
    github_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GITHUB_REPO
    print("=" * 55)
    print("  TOUS LES TESTS - API ANTI-TRICHE")
    print("  Base:", BASE)
    print("=" * 55)
    test_health()
    test_seed_12()
    test_analyze_human_sync_retrain()
    test_reponse_modele()
    github_result = test_github_repo(github_url)
    test_final(github_result, github_url)
    print("\n  FIN DE TOUS LES TESTS")
    print("=" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
