"""
Exemples de "users" pour tester le modèle anti-triche sur Hugging Face.
Chaque user = un code à analyser.

Usage:
  python scripts/exemples_users_test.py
"""
import json
import urllib.request

BASE = "https://negzaoui-anti-cheat-coding.hf.space"

# Exemples de codes (simulant différents users)
USERS = [
    {
        "name": "User 1 - Debutant humain",
        "code": """x = 5
y = 10
print(x + y)
""",
        "expected": "OK (code simple, humain)",
    },
    {
        "name": "User 2 - Humain avec erreurs",
        "code": """def calcul(a,b):
    # je fais la somme
    resultat=a+b
    return resultat

print(calcul(3,4))
""",
        "expected": "OK (style humain, espaces irreguliers)",
    },
    {
        "name": "User 3 - Code type ChatGPT",
        "code": """def binary_search(arr: list, target: int) -> int:
    \"\"\"
    Perform a binary search on a sorted array.
    
    Args:
        arr: A sorted list of integers.
        target: The value to search for.
    
    Returns:
        The index of the target if found, otherwise -1.
    \"\"\"
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1
""",
        "expected": "SUSPECT ou TRICHE (style IA: docstring, type hints, commentaires)",
    },
    {
        "name": "User 4 - Code Copilot style",
        "code": """def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    
    mid = len(arr) // 2
    left_half = merge_sort(arr[:mid])
    right_half = merge_sort(arr[mid:])
    
    return merge(left_half, right_half)

def merge(left, right):
    result = []
    i = j = 0
    
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    
    result.extend(left[i:])
    result.extend(right[j:])
    
    return result
""",
        "expected": "SUSPECT (algorithme classique, bien structure)",
    },
    {
        "name": "User 5 - Humain experimente",
        "code": """# quick fix pour le bug #42
def process(data):
    out = []
    for item in data:
        if item > 0:
            out.append(item * 2)
    return out

# TODO: optimiser plus tard
res = process([1, -2, 3, 0, 5])
print(res)
""",
        "expected": "OK (commentaires informels, style humain)",
    },
    {
        "name": "User 6 - Code vide",
        "code": "",
        "expected": "OK (rien a analyser)",
    },
]


def analyze(code):
    body = json.dumps({"code": code}).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/analyze",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    print("=" * 70)
    print("  EXEMPLES DE USERS - TEST MODELE HUGGING FACE")
    print("  API:", BASE)
    print("=" * 70)
    print()

    for i, user in enumerate(USERS, 1):
        print(f"[{i}/{len(USERS)}] {user['name']}")
        print(f"     Attendu: {user['expected']}")
        try:
            result = analyze(user["code"])
            print(f"     score_ia: {result.get('score_ia', '?'):.2f}")
            print(f"     final_score: {result.get('final_score', '?'):.3f}")
            print(f"     verdict: {result.get('verdict', '?')}")
        except Exception as e:
            print(f"     ERREUR: {e}")
        print()

    print("=" * 70)
    print("  FIN DES TESTS")
    print("=" * 70)


if __name__ == "__main__":
    main()
