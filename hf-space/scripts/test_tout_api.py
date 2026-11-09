"""
Script pour tester toute l'API anti-triche (health, analyze, human_decision, sync_storage, retrain).
Change BASE si tu testes en local (http://localhost:7860).
"""
import json
import urllib.request
import sys

# URL de l'API (Space HF ou local)
BASE = "https://negzaoui-anti-cheat-coding.hf.space"
# Si tu as configuré RETRAIN_SECRET sur le Space, mets-le ici pour tester /retrain
RETRAIN_SECRET = ""  # ex: "mon_secret"


def request(method, path, body=None, headers=None, timeout=30):
    url = BASE + path
    h = dict(headers or {})
    h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    print("=" * 55)
    print("  TEST COMPLET API ANTI-TRICHE")
    print("  Base:", BASE)
    print("=" * 55)

    # --- 1. Health ---
    print("\n[1] GET /health")
    try:
        req = urllib.request.Request(BASE + "/health")
        with urllib.request.urlopen(req, timeout=15) as r:
            out = r.read().decode()
        print("     Reponse:", out)
    except Exception as e:
        print("     ERREUR:", e)
        return 1

    # --- 2. Analyze ---
    print("\n[2] POST /analyze")
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
        sid = result.get("submission_id")
        print("     submission_id:", sid)
        print("     verdict:", result.get("verdict"), "| final_score:", result.get("final_score"))
    except Exception as e:
        print("     ERREUR:", e)
        return 1

    # --- 3. Human decision (pour apprentissage) ---
    print("\n[3] POST /human_decision")
    if not sid:
        sid = "sub_test_123"
    body = json.dumps({
        "submission_id": sid,
        "human_label": 0,
        "comment": "Test script",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            BASE + "/human_decision",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            out = json.loads(r.read().decode())
        print("     Reponse:", out)
    except Exception as e:
        print("     ERREUR:", e)
        # pas bloquant

    # --- 4. Sync storage ---
    print("\n[4] POST /sync_storage")
    try:
        req = urllib.request.Request(
            BASE + "/sync_storage",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read().decode())
        print("     Reponse:", out)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        if e.code == 404:
            print("     404 = Space pas a jour. Pousse le code (voir QUOI_FAIRE_POUR_TESTER.md).")
        elif e.code == 503:
            print("     (HF_REPO/HF_TOKEN non configures sur le Space - normal si pas encore fait)")
        else:
            print("     ERREUR:", e.code, body)
    except Exception as e:
        print("     ERREUR:", e)

    # --- 5. Retrain (optionnel) ---
    print("\n[5] POST /retrain?min_samples=10")
    try:
        url = BASE + "/retrain?min_samples=10"
        h = {"Content-Type": "application/json"}
        if RETRAIN_SECRET:
            h["X-Retrain-Secret"] = RETRAIN_SECRET
        req = urllib.request.Request(url, data=b"{}", method="POST", headers=h)
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read().decode())
        print("     Reponse:", out)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        if e.code == 404:
            print("     404 = Space pas a jour. Pousse le code (voir QUOI_FAIRE_POUR_TESTER.md).")
        elif e.code == 503:
            print("     (HF_REPO/HF_TOKEN non configures - normal)")
        elif e.code == 400:
            print("     (Pas assez de decisions pour entraîner - normal)")
        elif e.code == 403:
            print("     (Secret invalide ou manquant - configure RETRAIN_SECRET)")
        else:
            print("     ERREUR:", e.code, body)
    except Exception as e:
        print("     ERREUR:", e)

    print("\n" + "=" * 55)
    print("  FIN DES TESTS")
    print("=" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
