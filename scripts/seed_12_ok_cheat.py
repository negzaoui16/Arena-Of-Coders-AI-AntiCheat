"""
Envoie 12 analyse + 12 human_decision : 6 OK (humain) et 6 CHEAT (triche/IA).
Pour voir comment le modèle répond après retrain (score plus haut sur du "cheat", plus bas sur "OK").
"""
import json
import urllib.request

BASE = "https://negzaoui-anti-cheat-coding.hf.space"

# 12 codes différents. human_label: 0 = OK (humain), 1 = CHEAT (triche/IA)
# 6 premiers = OK, 6 derniers = CHEAT
SAMPLES = [
    # --- 6 OK (humain) ---
    ("def hello():\n    print('world')", 0),
    ("x = 1\ny = 2\nprint(x + y)", 0),
    ("for i in range(5):\n    print(i * 2)", 0),
    ("def add(a, b):\n    return a + b", 0),
    ("lst = [1, 2, 3]\nprint(sum(lst))", 0),
    ("s = 'hello'\nprint(s.upper())", 0),
    # --- 6 CHEAT (triche/IA) ---
    ("def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)", 1),
    ("def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)", 1),
    ("def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5)+1):\n        if n % i == 0:\n            return False\n    return True", 1),
    ("class Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n        for i, v in enumerate(nums):\n            if target - v in seen:\n                return [seen[target-v], i]\n            seen[v] = i", 1),
    ("def reverse_string(s):\n    return s[::-1] if s else ''", 1),
    ("def binary_search(arr, x):\n    low, high = 0, len(arr)-1\n    while low <= high:\n        mid = (low+high)//2\n        if arr[mid] == x: return mid\n        if arr[mid] < x: low = mid+1\n        else: high = mid-1\n    return -1", 1),
]


def main():
    print("Envoi de 12 analyse + 12 human_decision (6 OK, 6 CHEAT) vers", BASE)
    for i, (code, label) in enumerate(SAMPLES, 1):
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
        # 2. Human decision
        tag = "OK" if label == 0 else "CHEAT"
        body2 = json.dumps({
            "submission_id": sid,
            "human_label": label,
            "comment": f"seed #{i} {tag}",
        }).encode("utf-8")
        req2 = urllib.request.Request(
            BASE + "/human_decision",
            data=body2,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req2, timeout=15) as r2:
            pass
        print(f"  {i}/12 ok (submission_id={sid}, label={label} {tag})")
    print("\nTermine. Lance : python scripts\\test_tout_api.py")
    print("Puis appelle POST /retrain?min_samples=10 pour re-entrainer.")
    print("Ensuite re-teste /analyze sur du code 'OK' vs 'cheat' pour voir la difference de score_ia.")


if __name__ == "__main__":
    main()
