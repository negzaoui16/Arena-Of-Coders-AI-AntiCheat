"""Test de l'API anti-triche en ligne (Hugging Face Space)."""
import json
import urllib.request

BASE = "https://negzaoui-anti-cheat-coding.hf.space"

def main():
    print("=" * 50)
    print("TEST API EN LIGNE (Hugging Face Space)")
    print("=" * 50)

    # 1. Health
    print("\n1. GET /health")
    try:
        req = urllib.request.Request(BASE + "/health")
        with urllib.request.urlopen(req, timeout=15) as r:
            out = r.read().decode()
        print("   Reponse:", out)
    except Exception as e:
        print("   ERREUR:", e)
        return 1

    # 2. Analyze
    print("\n2. POST /analyze")
    code = 'def hello():\n    print("world")'
    body = json.dumps({"code": code}).encode("utf-8")
    try:
        req = urllib.request.Request(
            BASE + "/analyze",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode())
        print("   score_ia:", result.get("score_ia"))
        print("   score_plagiat:", result.get("score_plagiat"))
        print("   copy_paste_detected:", result.get("copy_paste_detected"))
        print("   final_score:", result.get("final_score"))
        print("   verdict:", result.get("verdict"))
    except Exception as e:
        print("   ERREUR:", e)
        return 1

    print("\n" + "=" * 50)
    print("OK - API en ligne fonctionne.")
    return 0

if __name__ == "__main__":
    exit(main())
