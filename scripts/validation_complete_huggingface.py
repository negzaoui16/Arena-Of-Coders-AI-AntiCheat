"""
=============================================================================
VALIDATION COMPLETE DU MODELE ANTI-TRICHE SUR HUGGING FACE
=============================================================================

Ce script teste TOUT le modèle déployé sur Hugging Face :
1. Santé de l'API
2. Apprentissage automatique (auto-learn)
3. Analyse de code humain (POST /analyze)
4. Analyse de code IA/ChatGPT (POST /analyze)
5. Analyse de code vide (POST /analyze)
6. Décisions humaines (POST /human_decision)
7. Sync storage (POST /sync_storage)
8. Test de 12 utilisateurs (6 humains + 6 IA)
9. Analyse d'un repo GitHub via POST /analyze_github (NOUVEL ENDPOINT)

Usage:
  python scripts/validation_complete_huggingface.py

Le script affiche un rapport final avec le statut de chaque test.
"""
import json
import sys
import time
import urllib.request
import urllib.error

# Configuration
BASE_URL = "https://negzaoui-anti-cheat-coding.hf.space"
TIMEOUT = 60

# Compteurs de résultats
TESTS_OK = 0
TESTS_FAILED = 0
RESULTS = []


def log(msg, status="INFO"):
    """Affiche un message avec statut."""
    symbols = {"OK": "✓", "FAIL": "✗", "INFO": "→", "WARN": "⚠"}
    print(f"  {symbols.get(status, '→')} {msg}")


def add_result(name, success, details=""):
    """Enregistre un résultat de test."""
    global TESTS_OK, TESTS_FAILED
    if success:
        TESTS_OK += 1
    else:
        TESTS_FAILED += 1
    RESULTS.append({"name": name, "success": success, "details": details})


def api_request(method, path, body=None, headers=None, timeout=TIMEOUT):
    """Effectue une requête HTTP vers l'API."""
    url = BASE_URL + path
    h = dict(headers or {})
    h.setdefault("Content-Type", "application/json")
    data = body.encode("utf-8") if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.getcode(), json.loads(r.read().decode())


def test_health():
    """Test 1: Vérifie que l'API répond."""
    print("\n[TEST 1] GET /health - Santé de l'API")
    try:
        code, data = api_request("GET", "/health", timeout=15)
        if code == 200 and data.get("status") == "ok":
            log("API en ligne", "OK")
            add_result("Health Check", True)
            return True
        else:
            log(f"Réponse inattendue: {data}", "FAIL")
            add_result("Health Check", False, str(data))
            return False
    except Exception as e:
        log(f"Erreur: {e}", "FAIL")
        add_result("Health Check", False, str(e))
        return False


def test_auto_learn_status():
    """Test 2: Vérifie l'état de l'apprentissage automatique."""
    print("\n[TEST 2] GET /auto_learn_status - Apprentissage automatique")
    try:
        code, data = api_request("GET", "/auto_learn_status", timeout=15)
        if code == 200:
            enabled = data.get("enabled", False)
            hf_configured = data.get("hf_configured", False)
            log(f"enabled: {enabled}", "OK" if enabled else "WARN")
            log(f"hf_configured: {hf_configured}", "OK" if hf_configured else "WARN")
            log(f"retrain_every_n: {data.get('retrain_every_n')}", "INFO")
            log(f"thresholds: human={data.get('thresholds', {}).get('human')}, ia={data.get('thresholds', {}).get('ia')}", "INFO")
            log(f"total_predictions: {data.get('total_predictions')}", "INFO")
            log(f"total_decisions: {data.get('total_decisions')}", "INFO")
            log(f"auto_labeled_decisions: {data.get('auto_labeled_decisions')}", "INFO")
            add_result("Auto-Learn Status", enabled and hf_configured, 
                      f"enabled={enabled}, hf_configured={hf_configured}")
            return data
        else:
            log(f"Code HTTP: {code}", "FAIL")
            add_result("Auto-Learn Status", False, f"HTTP {code}")
            return None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            log("Endpoint non trouvé (mise à jour nécessaire)", "FAIL")
            add_result("Auto-Learn Status", False, "404 Not Found")
        else:
            log(f"Erreur HTTP {e.code}", "FAIL")
            add_result("Auto-Learn Status", False, str(e))
        return None
    except Exception as e:
        log(f"Erreur: {e}", "FAIL")
        add_result("Auto-Learn Status", False, str(e))
        return None


def test_analyze_human_code():
    """Test 3: Analyse un code type humain."""
    print("\n[TEST 3] POST /analyze - Code type HUMAIN")
    code = "x = 5\nprint(x)"
    try:
        body = json.dumps({"code": code})
        status, data = api_request("POST", "/analyze", body=body)
        if status == 200:
            score_ia = data.get("score_ia", -1)
            verdict = data.get("verdict", "?")
            log(f"score_ia: {score_ia:.2f}", "OK" if score_ia < 0.5 else "WARN")
            log(f"verdict: {verdict}", "OK" if verdict == "OK" else "WARN")
            log(f"final_score: {data.get('final_score', '?')}", "INFO")
            success = score_ia < 0.5 and verdict == "OK"
            add_result("Analyze Human Code", success, f"score_ia={score_ia:.2f}, verdict={verdict}")
            return data
        else:
            log(f"Code HTTP: {status}", "FAIL")
            add_result("Analyze Human Code", False, f"HTTP {status}")
            return None
    except Exception as e:
        log(f"Erreur: {e}", "FAIL")
        add_result("Analyze Human Code", False, str(e))
        return None


def test_analyze_ia_code():
    """Test 4: Analyse un code type IA/ChatGPT."""
    print("\n[TEST 4] POST /analyze - Code type IA/ChatGPT")
    code = '''def binary_search(arr: list, target: int) -> int:
    """
    Perform a binary search on a sorted array.
    
    Args:
        arr: A sorted list of integers.
        target: The value to search for.
    
    Returns:
        The index of the target if found, otherwise -1.
    """
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1'''
    try:
        body = json.dumps({"code": code})
        status, data = api_request("POST", "/analyze", body=body)
        if status == 200:
            score_ia = data.get("score_ia", -1)
            verdict = data.get("verdict", "?")
            log(f"score_ia: {score_ia:.2f}", "OK" if score_ia > 0.5 else "WARN")
            log(f"verdict: {verdict}", "OK" if verdict != "OK" else "WARN")
            log(f"final_score: {data.get('final_score', '?')}", "INFO")
            # On considère le test OK si le score_ia est > 0.5 (détecté comme IA)
            success = score_ia > 0.5
            add_result("Analyze IA Code", success, f"score_ia={score_ia:.2f}, verdict={verdict}")
            return data
        else:
            log(f"Code HTTP: {status}", "FAIL")
            add_result("Analyze IA Code", False, f"HTTP {status}")
            return None
    except Exception as e:
        log(f"Erreur: {e}", "FAIL")
        add_result("Analyze IA Code", False, str(e))
        return None


def test_analyze_empty_code():
    """Test 5: Analyse un code vide."""
    print("\n[TEST 5] POST /analyze - Code VIDE")
    try:
        body = json.dumps({"code": ""})
        status, data = api_request("POST", "/analyze", body=body)
        if status == 200:
            verdict = data.get("verdict", "?")
            log(f"verdict: {verdict}", "OK")
            log(f"final_score: {data.get('final_score', '?')}", "INFO")
            add_result("Analyze Empty Code", True, f"verdict={verdict}")
            return data
        else:
            log(f"Code HTTP: {status}", "FAIL")
            add_result("Analyze Empty Code", False, f"HTTP {status}")
            return None
    except Exception as e:
        log(f"Erreur: {e}", "FAIL")
        add_result("Analyze Empty Code", False, str(e))
        return None


def test_human_decision():
    """Test 6: Enregistre une décision humaine."""
    print("\n[TEST 6] POST /human_decision - Décision humaine")
    try:
        body = json.dumps({
            "submission_id": f"validation_test_{int(time.time())}",
            "human_label": 0,
            "comment": "Test de validation automatique"
        })
        status, data = api_request("POST", "/human_decision", body=body)
        if status == 200 and data.get("status") == "recorded":
            log(f"Décision enregistrée: {data.get('submission_id')}", "OK")
            add_result("Human Decision", True)
            return True
        else:
            log(f"Réponse: {data}", "FAIL")
            add_result("Human Decision", False, str(data))
            return False
    except Exception as e:
        log(f"Erreur: {e}", "FAIL")
        add_result("Human Decision", False, str(e))
        return False


def test_sync_storage():
    """Test 7: Sync storage vers le Hub."""
    print("\n[TEST 7] POST /sync_storage - Synchronisation")
    try:
        status, data = api_request("POST", "/sync_storage", body="{}")
        if status == 200:
            uploaded = data.get("uploaded", [])
            log(f"Fichiers uploadés: {uploaded}", "OK")
            add_result("Sync Storage", True, str(uploaded))
            return True
        else:
            log(f"Code HTTP: {status}", "FAIL")
            add_result("Sync Storage", False, f"HTTP {status}")
            return False
    except urllib.error.HTTPError as e:
        if e.code == 503:
            log("HF_REPO/HF_TOKEN non configurés", "WARN")
            add_result("Sync Storage", False, "503 - Non configuré")
        else:
            log(f"Erreur HTTP {e.code}", "FAIL")
            add_result("Sync Storage", False, str(e))
        return False
    except Exception as e:
        log(f"Erreur: {e}", "FAIL")
        add_result("Sync Storage", False, str(e))
        return False


def test_multiple_users():
    """Test 8: Simule 12 utilisateurs avec différents types de code."""
    print("\n[TEST 8] Simulation de 12 utilisateurs")
    
    users = [
        # --- 6 USERS HUMAINS ---
        ("User 1 - Débutant", "x = 1\nprint(x)", "humain"),
        
        ("User 2 - Humain erreurs", "def f(a,b):\n  return a+b\nprint(f(1,2))", "humain"),
        
        ("User 3 - Script simple", "import os\nprint(os.getcwd())", "humain"),
        
        ("User 4 - Humain expérimenté", """# fix bug #42
def calc(x):
    return x * 2
# TODO: optimiser plus tard
res = calc(5)
print(res)""", "humain"),
        
        ("User 5 - Code brouillon", """# test rapide
a=1
b=2
c=a+b
print(c)  # debug""", "humain"),
        
        ("User 6 - Boucle simple", """for i in range(5):
    print(i)
print("fini")""", "humain"),
        
        # --- 6 USERS IA/CHEAT ---
        ("User 7 - ChatGPT style", '''def binary_search(arr: list, target: int) -> int:
    """
    Perform a binary search on a sorted array.
    
    Args:
        arr: A sorted list of integers.
        target: The value to search for.
    
    Returns:
        The index of the target if found, otherwise -1.
    """
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1''', "ia"),
        
        ("User 8 - Copilot style", '''def quicksort(arr: list) -> list:
    """Sort array using quicksort algorithm."""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)''', "ia"),
        
        ("User 9 - Merge sort IA", '''def merge_sort(arr: list) -> list:
    """
    Sort an array using the merge sort algorithm.
    
    Time complexity: O(n log n)
    Space complexity: O(n)
    """
    if len(arr) <= 1:
        return arr
    
    mid = len(arr) // 2
    left_half = merge_sort(arr[:mid])
    right_half = merge_sort(arr[mid:])
    
    return merge(left_half, right_half)

def merge(left: list, right: list) -> list:
    """Merge two sorted arrays into one sorted array."""
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
    
    return result''', "ia"),
        
        ("User 10 - Fibonacci IA", '''def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number.
    
    Args:
        n: The position in the Fibonacci sequence (0-indexed).
    
    Returns:
        The nth Fibonacci number.
    
    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")
    if n <= 1:
        return n
    
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    
    return curr''', "ia"),
        
        ("User 11 - Palindrome IA", '''def is_palindrome(s: str) -> bool:
    """
    Check if a string is a palindrome.
    
    A palindrome is a word, phrase, or sequence that reads the same
    backward as forward, ignoring spaces and punctuation.
    
    Args:
        s: The string to check.
    
    Returns:
        True if the string is a palindrome, False otherwise.
    """
    # Remove non-alphanumeric characters and convert to lowercase
    cleaned = ''.join(char.lower() for char in s if char.isalnum())
    
    # Compare with reversed string
    return cleaned == cleaned[::-1]''', "ia"),
        
        ("User 12 - Classe IA", '''class BinaryTree:
    """
    A binary tree implementation with basic operations.
    
    Attributes:
        value: The value stored in the node.
        left: The left child node.
        right: The right child node.
    """
    
    def __init__(self, value: int):
        """Initialize a new binary tree node."""
        self.value = value
        self.left = None
        self.right = None
    
    def insert(self, value: int) -> None:
        """Insert a value into the binary tree."""
        if value < self.value:
            if self.left is None:
                self.left = BinaryTree(value)
            else:
                self.left.insert(value)
        else:
            if self.right is None:
                self.right = BinaryTree(value)
            else:
                self.right.insert(value)
    
    def search(self, value: int) -> bool:
        """Search for a value in the binary tree."""
        if value == self.value:
            return True
        elif value < self.value and self.left:
            return self.left.search(value)
        elif value > self.value and self.right:
            return self.right.search(value)
        return False''', "ia"),
    ]
    
    results_users = []
    for name, code, expected_type in users:
        try:
            body = json.dumps({"code": code})
            status, data = api_request("POST", "/analyze", body=body, timeout=30)
            if status == 200:
                score_ia = data.get("score_ia", -1)
                verdict = data.get("verdict", "?")
                detected = "ia" if score_ia > 0.5 else "humain"
                correct = detected == expected_type
                symbol = "✓" if correct else "✗"
                log(f"{symbol} {name}: score_ia={score_ia:.2f}, verdict={verdict} (attendu: {expected_type})", 
                    "OK" if correct else "WARN")
                results_users.append(correct)
            else:
                log(f"✗ {name}: Erreur HTTP {status}", "FAIL")
                results_users.append(False)
        except Exception as e:
            log(f"✗ {name}: {e}", "FAIL")
            results_users.append(False)
    
    success_rate = sum(results_users) / len(results_users) if results_users else 0
    success = success_rate >= 0.5  # Au moins 50% correct
    
    # Afficher le résumé
    print()
    log(f"Résumé: {sum(results_users)}/{len(results_users)} détections correctes ({success_rate*100:.0f}%)", 
        "OK" if success_rate >= 0.7 else "WARN")
    
    add_result("12 Users Test", success, f"{sum(results_users)}/{len(results_users)} corrects ({success_rate*100:.0f}%)")
    return success


def test_github_repo():
    """Test 9: Analyse un repo GitHub via POST /analyze_github."""
    print("\n[TEST 9] POST /analyze_github - Analyse repo GitHub")
    
    github_url = "https://github.com/negzaoui16/anti-cheat-coding"
    
    log(f"Repo: {github_url}", "INFO")
    
    try:
        body = json.dumps({"github_url": github_url})
        status, data = api_request("POST", "/analyze_github", body=body, timeout=120)
        
        if status == 200:
            owner = data.get("owner", "?")
            repo = data.get("repo", "?")
            files_analyzed = data.get("files_analyzed", 0)
            avg_score = data.get("avg_score_ia", 0)
            final_verdict = data.get("final_verdict", "?")
            details = data.get("details", [])
            
            log(f"Owner: {owner}", "INFO")
            log(f"Repo: {repo}", "INFO")
            log(f"Fichiers analysés: {files_analyzed}", "INFO")
            
            # Afficher les détails (max 5 fichiers)
            for d in details[:5]:
                file_name = d.get("file", "?").split("/")[-1][:20]
                score = d.get("score_ia", 0)
                verdict = d.get("verdict", "?")
                log(f"{file_name}: score_ia={score:.2f}, verdict={verdict}", "INFO")
            
            if len(details) > 5:
                log(f"... et {len(details) - 5} autres fichiers", "INFO")
            
            # Verdict final
            print()
            if avg_score < 0.5:
                log(f"Score moyen: {avg_score:.2f} → {final_verdict}", "OK")
            elif avg_score < 0.7:
                log(f"Score moyen: {avg_score:.2f} → {final_verdict}", "WARN")
            else:
                log(f"Score moyen: {avg_score:.2f} → {final_verdict}", "WARN")
            
            add_result("POST /analyze_github", True, f"{owner}/{repo}: {final_verdict} ({avg_score:.2f})")
            return True
        else:
            log(f"Code HTTP: {status}", "FAIL")
            add_result("POST /analyze_github", False, f"HTTP {status}")
            return False
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            log("Endpoint /analyze_github non trouvé - mise à jour nécessaire", "FAIL")
            add_result("POST /analyze_github", False, "404 - Endpoint non trouvé")
        elif e.code == 400:
            body_err = e.read().decode()[:100]
            log(f"Erreur 400: {body_err}", "FAIL")
            add_result("POST /analyze_github", False, f"400 - {body_err}")
        else:
            log(f"Erreur HTTP {e.code}", "FAIL")
            add_result("POST /analyze_github", False, f"HTTP {e.code}")
        return False
    except Exception as e:
        log(f"Erreur: {e}", "FAIL")
        add_result("POST /analyze_github", False, str(e))
        return False


def print_final_report():
    """Affiche le rapport final."""
    print("\n")
    print("=" * 70)
    print("                    RAPPORT DE VALIDATION")
    print("=" * 70)
    print()
    print(f"  API testée: {BASE_URL}")
    print()
    print("  | Test                    | Statut | Détails")
    print("  |-------------------------|--------|----------------------------------")
    for r in RESULTS:
        status = "OK" if r["success"] else "FAIL"
        name = r["name"][:23].ljust(23)
        details = (r["details"][:30] + "...") if len(r["details"]) > 33 else r["details"]
        print(f"  | {name} | {status:6} | {details}")
    print()
    print(f"  TOTAL: {TESTS_OK} OK / {TESTS_FAILED} FAIL")
    print()
    
    if TESTS_FAILED == 0:
        print("  ╔════════════════════════════════════════════════════════════════╗")
        print("  ║  VALIDATION REUSSIE - Le modèle Hugging Face fonctionne !     ║")
        print("  ╚════════════════════════════════════════════════════════════════╝")
    else:
        print("  ╔════════════════════════════════════════════════════════════════╗")
        print(f"  ║  VALIDATION PARTIELLE - {TESTS_FAILED} test(s) échoué(s)                     ║")
        print("  ╚════════════════════════════════════════════════════════════════╝")
    
    print()
    print("=" * 70)


def main():
    print()
    print("=" * 70)
    print("      VALIDATION COMPLETE - MODELE ANTI-TRICHE HUGGING FACE")
    print("=" * 70)
    print(f"  API: {BASE_URL}")
    print("=" * 70)
    
    # Exécuter tous les tests
    if not test_health():
        print("\n  ⚠ L'API n'est pas accessible. Arrêt des tests.")
        print_final_report()
        return 1
    
    test_auto_learn_status()
    test_analyze_human_code()
    test_analyze_ia_code()
    test_analyze_empty_code()
    test_human_decision()
    test_sync_storage()
    test_multiple_users()
    test_github_repo()
    
    # Rapport final
    print_final_report()
    
    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
