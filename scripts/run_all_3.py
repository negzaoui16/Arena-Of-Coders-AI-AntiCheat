"""
Un seul fichier = 3 étapes en une fois :
  1. Seed 12 décisions (6 OK + 6 CHEAT)
  2. Test complet (health, analyze, human_decision, sync_storage, retrain)
  3. Réponse du modèle (OK vs CHEAT)

Usage : python scripts/run_all_3.py
Change BASE si tu testes en local (http://localhost:7860).
"""
import json
import urllib.request
import urllib.error
import sys

BASE = "https://negzaoui-anti-cheat-coding.hf.space"
RETRAIN_SECRET = ""

# --- Données pour étape 1 (seed 12) ---
SAMPLES = [
    ("def hello():\n    print('world')", 0),
    ("x = 1\ny = 2\nprint(x + y)", 0),
    ("for i in range(5):\n    print(i * 2)", 0),
    ("def add(a, b):\n    return a + b", 0),
    ("lst = [1, 2, 3]\nprint(sum(lst))", 0),
    ("s = 'hello'\nprint(s.upper())", 0),
    ("def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)", 1),
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


def step1_seed_12():
    """Étape 1 : 12 analyse + 12 human_decision (6 OK, 6 CHEAT)."""
    print("\n" + "=" * 55)
    print("  [1/3] SEED 12 DECISIONS (6 OK + 6 CHEAT)")
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


def step2_test_complet():
    """Étape 2 : health, analyze, human_decision, sync_storage, retrain."""
    print("=" * 55)
    print("  [2/3] TEST COMPLET (health, analyze, human_decision, sync, retrain)")
    print("=" * 55)

    print("\n  [1] GET /health")
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + "/health"), timeout=15) as r:
            print("       Reponse:", r.read().decode())
    except Exception as e:
        print("       ERREUR:", e)
        return

    print("\n  [2] POST /analyze")
    try:
        body = json.dumps({"code": CODE_OK}).encode("utf-8")
        result = req("POST", "/analyze", body)
        sid = result.get("submission_id")
        print("       submission_id:", sid, "| verdict:", result.get("verdict"))
    except Exception as e:
        print("       ERREUR:", e)
        sid = "sub_test_123"

    print("\n  [3] POST /human_decision")
    try:
        body = json.dumps({"submission_id": sid, "human_label": 0, "comment": "run_all_3"}).encode("utf-8")
        req("POST", "/human_decision", body, timeout=15)
        print("       OK")
    except Exception as e:
        print("       ERREUR:", e)

    print("\n  [4] POST /sync_storage")
    try:
        out = req("POST", "/sync_storage", b"{}", timeout=30)
        print("       Reponse:", out)
    except urllib.error.HTTPError as e:
        if e.code == 503:
            print("       (HF_REPO/HF_TOKEN non configures)")
        else:
            print("       ERREUR:", e.code, e.read().decode()[:200])
    except Exception as e:
        print("       ERREUR:", e)

    print("\n  [5] POST /retrain?min_samples=10")
    try:
        out = req("POST", "/retrain?min_samples=10", b"{}", timeout=120)
        print("       Reponse:", out)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        if e.code == 404:
            print("       404 = Space pas a jour.")
        elif e.code == 503:
            print("       (HF_REPO/HF_TOKEN non configures)")
        elif e.code == 400:
            print("       (Pas assez de decisions)")
        elif e.code == 403:
            print("       (Secret invalide)")
        else:
            print("       ERREUR:", e.code, body)
    except Exception as e:
        print("       ERREUR:", e)
    print()


def step3_reponse_modele():
    """Étape 3 : analyse OK vs CHEAT pour voir la réponse du modèle."""
    print("=" * 55)
    print("  [3/3] REPONSE DU MODELE (OK vs CHEAT)")
    print("=" * 55)
    try:
        r1 = req("POST", "/analyze", json.dumps({"code": CODE_OK}).encode("utf-8"))
        print("\n  Code OK (humain)    : score_ia =", r1.get("score_ia"), "| verdict =", r1.get("verdict"))
        r2 = req("POST", "/analyze", json.dumps({"code": CODE_CHEAT}).encode("utf-8"))
        print("  Code CHEAT (IA)    : score_ia =", r2.get("score_ia"), "| verdict =", r2.get("verdict"))
    except Exception as e:
        print("  ERREUR:", e)
    print("\n" + "=" * 55)
    print("  FIN (1 fichier = 3 etapes)")
    print("=" * 55)


def main():
    print("Base:", BASE)
    step1_seed_12()
    step2_test_complet()
    step3_reponse_modele()
    return 0


if __name__ == "__main__":
    sys.exit(main())
