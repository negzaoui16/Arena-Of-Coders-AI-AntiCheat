"""
TEST COMPLET du modèle anti-triche déployé sur HUGGING FACE uniquement.
Aucun appel au modèle local : tout passe par l'API du Space HF.

Usage:
  python scripts/test_complet_huggingface.py
  python scripts/test_complet_huggingface.py --retrain   # inclut /retrain si RETRAIN_SECRET configuré

Variables d'environnement optionnelles:
  ANTI_CHEAT_BASE_URL  : URL du Space (défaut: https://negzaoui-anti-cheat-coding.hf.space)
  RETRAIN_SECRET       : pour tester POST /retrain
"""
import json
import os
import sys
import urllib.request
import urllib.error

# URL du modèle sur Hugging Face (pas de localhost)
BASE = os.environ.get("ANTI_CHEAT_BASE_URL", "https://negzaoui-anti-cheat-coding.hf.space")
RETRAIN_SECRET = os.environ.get("RETRAIN_SECRET", "")

# Exemples de code pour vérifier le comportement du modèle HF
CODE_OK = 'def hello():\n    print("world")'
CODE_CHEAT = """def binary_search(arr, x):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == x:
            return mid
        if arr[mid] < x:
            low = mid + 1
        else:
            high = mid - 1
    return -1"""
CODE_VIDE = ""
CODE_LONG_HUMAIN = "# commentaire\nx = 1\ny = 2\nprint(x + y)\n" * 50


def req(method, path, body=None, headers=None, timeout=60):
    url = BASE + path
    h = dict(headers or {})
    h.setdefault("Content-Type", "application/json")
    data = body.encode("utf-8") if isinstance(body, str) else body
    request = urllib.request.Request(url, data=data, method=method, headers=h)
    with urllib.request.urlopen(request, timeout=timeout) as r:
        return r.getcode(), r.read().decode()


def main():
    do_retrain = "--retrain" in sys.argv
    errors = 0

    print()
    print("=" * 60)
    print("  TEST COMPLET - MODELE HUGGING FACE UNIQUEMENT")
    print("  (aucun appel au modele local)")
    print("  API:", BASE)
    print("=" * 60)
    print()

    # --- 1. Health ---
    print("[1] GET /health")
    try:
        code, out = req("GET", "/health", timeout=15)
        if code != 200:
            print("     ERREUR: code", code, out)
            errors += 1
        else:
            data = json.loads(out)
            print("     status:", data.get("status", out))
            print("     OK")
    except Exception as e:
        print("     ERREUR:", e)
        errors += 1
    print()

    # --- 2. Analyze : code OK (humain) ---
    print("[2] POST /analyze (code type humain)")
    try:
        body = json.dumps({"code": CODE_OK})
        code, out = req("POST", "/analyze", body=body, timeout=30)
        if code != 200:
            print("     ERREUR: code", code, out[:200])
            errors += 1
        else:
            data = json.loads(out)
            print("     verdict:", data.get("verdict"), "| score_ia:", data.get("score_ia"), "| final_score:", data.get("final_score"))
            print("     OK")
    except Exception as e:
        print("     ERREUR:", e)
        errors += 1
    print()

    # --- 3. Analyze : code type IA/cheat ---
    print("[3] POST /analyze (code type IA / cheat)")
    try:
        body = json.dumps({"code": CODE_CHEAT})
        code, out = req("POST", "/analyze", body=body, timeout=30)
        if code != 200:
            print("     ERREUR: code", code, out[:200])
            errors += 1
        else:
            data = json.loads(out)
            print("     verdict:", data.get("verdict"), "| score_ia:", data.get("score_ia"), "| final_score:", data.get("final_score"))
            print("     OK")
    except Exception as e:
        print("     ERREUR:", e)
        errors += 1
    print()

    # --- 4. Analyze : code vide ---
    print("[4] POST /analyze (code vide)")
    try:
        body = json.dumps({"code": CODE_VIDE})
        code, out = req("POST", "/analyze", body=body, timeout=30)
        if code != 200:
            print("     ERREUR: code", code, out[:200])
            errors += 1
        else:
            data = json.loads(out)
            print("     verdict:", data.get("verdict"), "| final_score:", data.get("final_score"))
            print("     OK")
    except Exception as e:
        print("     ERREUR:", e)
        errors += 1
    print()

    # --- 5. Analyze : code long (stress léger) ---
    print("[5] POST /analyze (code long)")
    try:
        body = json.dumps({"code": CODE_LONG_HUMAIN})
        code, out = req("POST", "/analyze", body=body, timeout=60)
        if code != 200:
            print("     ERREUR: code", code, out[:200])
            errors += 1
        else:
            data = json.loads(out)
            print("     verdict:", data.get("verdict"), "| final_score:", data.get("final_score"))
            print("     OK")
    except Exception as e:
        print("     ERREUR:", e)
        errors += 1
    print()

    # --- 6. Human decision (pour apprentissage) ---
    print("[6] POST /human_decision")
    try:
        body = json.dumps({
            "submission_id": "test_hf_script_001",
            "human_label": 0,
            "comment": "Test script Hugging Face",
        })
        code, out = req("POST", "/human_decision", body=body, timeout=15)
        if code != 200:
            print("     Reponse:", code, out[:150])
        else:
            print("     Reponse:", json.loads(out))
        print("     OK (non bloquant)")
    except Exception as e:
        print("     ERREUR:", e)
    print()

    # --- 7. Sync storage ---
    print("[7] POST /sync_storage")
    try:
        code, out = req("POST", "/sync_storage", body="{}", timeout=45)
        if code == 200:
            print("     Reponse:", json.loads(out))
            print("     OK")
        elif code == 503:
            print("     (HF_REPO/HF_TOKEN non configures sur le Space - attendu si pas encore fait)")
        elif code == 404:
            print("     (404 = Space pas a jour, pousser le code)")
        else:
            print("     Code:", code, out[:200])
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()[:200]
        if e.code == 503:
            print("     (HF_REPO/HF_TOKEN non configures - attendu)")
        elif e.code == 404:
            print("     (404 = Space pas a jour)")
        else:
            print("     ERREUR HTTP:", e.code, body_err)
    except Exception as e:
        print("     ERREUR:", e)
    print()

    # --- 8. Retrain (optionnel) ---
    if do_retrain:
        print("[8] POST /retrain?min_samples=10")
        try:
            h = {}
            if RETRAIN_SECRET:
                h["X-Retrain-Secret"] = RETRAIN_SECRET
            request = urllib.request.Request(
                BASE + "/retrain?min_samples=10",
                data=b"{}",
                method="POST",
                headers={**h, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=120) as r:
                out = r.read().decode()
                print("     Reponse:", json.loads(out))
                print("     OK")
        except urllib.error.HTTPError as e:
            body_err = e.read().decode()[:300]
            if e.code == 503:
                print("     (HF_REPO/HF_TOKEN non configures)")
            elif e.code == 400:
                print("     (Pas assez de decisions pour entraîner)")
            elif e.code == 403:
                print("     (Secret invalide - configurer RETRAIN_SECRET)")
            else:
                print("     ERREUR:", e.code, body_err)
        except Exception as e:
            print("     ERREUR:", e)
        print()
    else:
        print("[8] POST /retrain (ignore - lance avec --retrain pour tester)")

    # --- Récap ---
    print("=" * 60)
    if errors == 0:
        print("  RESULTAT: TOUS LES TESTS API (Hugging Face) OK")
    else:
        print("  RESULTAT:", errors, "ERREUR(S) - verifier que le Space HF est Running et a la bonne URL")
    print("=" * 60)
    print()
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
