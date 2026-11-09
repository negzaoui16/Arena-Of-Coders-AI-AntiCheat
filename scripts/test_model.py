"""
Script de test du modèle anti-triche via l'API.
Teste : code simple, code style IA, copier-coller, plagiat.
"""
import json
import urllib.request
import sys

BASE = "http://127.0.0.1:8000"


def post_analyze(code: str, typing_stats=None, room_params=None):
    body = {"code": code}
    if typing_stats is not None:
        body["typing_stats"] = typing_stats
    if room_params is not None:
        body["room_params"] = room_params
    req = urllib.request.Request(
        f"{BASE}/analyze",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def main():
    print("=" * 60)
    print("TESTS DU MODÈLE ANTI-TRICHE")
    print("=" * 60)

    # 1. Code simple (style humain)
    code_humain = '''def fib(n):
    if n < 2:
        return n
    return fib(n-1) + fib(n-2)
'''
    print("\n1. Code simple (style humain)")
    r = post_analyze(code_humain)
    print(f"   score_ia: {r['score_ia']}, score_plagiat: {r['score_plagiat']}, copy_paste: {r['copy_paste_detected']}")
    print(f"   final_score: {r['final_score']} -> verdict: {r['verdict']}")

    # 2. Code style IA (docstrings, type hints)
    code_ia = '''def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number using dynamic programming.
    """
    if n <= 0:
        return 0
    if n == 1:
        return 1
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
'''
    print("\n2. Code style IA (docstrings, type hints)")
    r = post_analyze(code_ia)
    print(f"   score_ia: {r['score_ia']}, score_plagiat: {r['score_plagiat']}, copy_paste: {r['copy_paste_detected']}")
    print(f"   final_score: {r['final_score']} -> verdict: {r['verdict']}")

    # 3. Copier-coller simulé (gros bloc + temps très court)
    code_copier = "def hello():\n    print('world')\n" * 5
    stats_copy = {
        "total_typing_time_ms": 100,
        "block_insertions": [{"line_count": 15, "duration_ms": 20}],
    }
    print("\n3. Copier-coller simulé (gros bloc + temps court)")
    r = post_analyze(code_copier, typing_stats=stats_copy)
    print(f"   score_ia: {r['score_ia']}, score_plagiat: {r['score_plagiat']}, copy_paste: {r['copy_paste_detected']}")
    print(f"   final_score: {r['final_score']} -> verdict: {r['verdict']}")

    # 4. Plagiat : code proche d'une solution existante (factorial)
    code_plagiat = """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
    print("\n4. Code proche d'une solution existante (plagiat)")
    r = post_analyze(code_plagiat)
    print(f"   score_ia: {r['score_ia']}, score_plagiat: {r['score_plagiat']}, copy_paste: {r['copy_paste_detected']}")
    print(f"   final_score: {r['final_score']} -> verdict: {r['verdict']}")

    # 5. Code neutre court
    print("\n5. Code très court (neutre)")
    r = post_analyze("x = 1")
    print(f"   score_ia: {r['score_ia']}, score_plagiat: {r['score_plagiat']}, copy_paste: {r['copy_paste_detected']}")
    print(f"   final_score: {r['final_score']} -> verdict: {r['verdict']}")

    print("\n" + "=" * 60)
    print("Tests terminés.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as e:
        print("Erreur: l'API ne répond pas. Lancez: uvicorn src.api:app --host 127.0.0.1 --port 8000")
        sys.exit(1)
    except Exception as e:
        print("Erreur:", e)
        sys.exit(1)
