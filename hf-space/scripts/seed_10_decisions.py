"""
Envoie 10 analyse + 10 human_decision (codes différents) pour pouvoir appeler /retrain.
À lancer une fois : après ça, POST /retrain?min_samples=10 pourra fonctionner.
"""
import json
import urllib.request

BASE = "https://negzaoui-anti-cheat-coding.hf.space"

# 10 extraits de code différents (pour 10 submission_id différents)
CODES = [
    'def hello():\n    print("world")',
    'def fib(n):\n    return n if n < 2 else fib(n-1)+fib(n-2)',
    'x = 1\ny = 2\nprint(x + y)',
    'for i in range(5):\n    print(i * 2)',
    'def add(a, b):\n    return a + b',
    'lst = [1, 2, 3]\nprint(sum(lst))',
    's = "hello"\nprint(s.upper())',
    'def fact(n):\n    return 1 if n <= 1 else n * fact(n-1)',
    'd = {"a": 1, "b": 2}\nprint(d.get("a"))',
    'import math\nprint(math.sqrt(16))',
]


def main():
    print("Envoi de 10 analyse + 10 human_decision vers", BASE)
    for i, code in enumerate(CODES, 1):
        # 1. Analyze
        body = json.dumps({"code": code}).encode("utf-8")
        req = urllib.request.Request(
            BASE + "/analyze",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode())
        sid = result.get("submission_id")
        # 2. Human decision (0 = OK humain, 1 = triche; on met un mix)
        label = 0 if i % 2 == 1 else 0  # tous OK pour l'exemple
        body2 = json.dumps({"submission_id": sid, "human_label": label, "comment": f"seed #{i}"}).encode("utf-8")
        req2 = urllib.request.Request(
            BASE + "/human_decision",
            data=body2,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req2, timeout=15) as r2:
            pass
        print(f"  {i}/10 ok (submission_id={sid})")
    print("Termine. Tu peux appeler POST /retrain?min_samples=10 (ou relancer test_tout_api.py).")


if __name__ == "__main__":
    main()
