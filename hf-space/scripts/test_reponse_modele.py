"""
Après avoir lancé seed_12_ok_cheat.py puis retrain, ce script envoie 2 analyses :
- 1 code style OK (humain) -> tu devrais voir score_ia plus bas
- 1 code style CHEAT (IA)   -> tu devrais voir score_ia plus haut
Pour voir comment le modèle répond différemment.
"""
import json
import urllib.request

BASE = "https://negzaoui-anti-cheat-coding.hf.space"

# 1 code "OK" (style humain simple), 1 code "CHEAT" (style IA / template)
CODE_OK = "def hello():\n    print('world')"
CODE_CHEAT = "def binary_search(arr, x):\n    low, high = 0, len(arr)-1\n    while low <= high:\n        mid = (low+high)//2\n        if arr[mid] == x: return mid\n        if arr[mid] < x: low = mid+1\n        else: high = mid-1\n    return -1"


def analyze(code, label):
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
    print("=" * 55)
    print("  REPONSE DU MODELE (OK vs CHEAT)")
    print("  Base:", BASE)
    print("=" * 55)

    print("\n[1] Code style OK (humain) :")
    r1 = analyze(CODE_OK, "OK")
    print("    score_ia:", r1.get("score_ia"))
    print("    verdict:", r1.get("verdict"), "| final_score:", r1.get("final_score"))

    print("\n[2] Code style CHEAT (IA/template) :")
    r2 = analyze(CODE_CHEAT, "CHEAT")
    print("    score_ia:", r2.get("score_ia"))
    print("    verdict:", r2.get("verdict"), "| final_score:", r2.get("final_score"))

    print("\n" + "=" * 55)
    print("  En general : score_ia plus bas = plus 'humain', plus haut = plus 'IA'.")
    print("=" * 55)


if __name__ == "__main__":
    main()
