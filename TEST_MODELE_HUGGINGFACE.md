# Comment tester le modèle anti-triche sur Hugging Face

Ce guide explique **comment tester le modèle déployé sur Hugging Face** (pas le modèle en local). Tous les tests ci-dessous appellent l’API du Space HF.

---

## Prérequis

- Le Space doit être **Running** : [https://huggingface.co/spaces/Negzaoui/anti-cheat-coding](https://huggingface.co/spaces/Negzaoui/anti-cheat-coding)
- URL de l’API : **`https://negzaoui-anti-cheat-coding.hf.space`**

Aucune clé API n’est obligatoire pour `/health` et `/analyze`.

---

## 1. Test rapide avec curl

### Vérifier que l’API répond (health)

```bash
curl https://negzaoui-anti-cheat-coding.hf.space/health
```

Réponse attendue : `{"status":"ok"}`

### Analyser du code (modèle HF)

```bash
curl -X POST "https://negzaoui-anti-cheat-coding.hf.space/analyze" ^
  -H "Content-Type: application/json" ^
  -d "{\"code\": \"def hello():\\n    print('world')\"}"
```

Sous Linux/macOS (remplacer `^` par `\` en fin de ligne) :

```bash
curl -X POST "https://negzaoui-anti-cheat-coding.hf.space/analyze" \
  -H "Content-Type: application/json" \
  -d '{"code": "def hello():\n    print(\"world\")"}'
```

Réponse attendue (exemple) :  
`score_ia`, `score_plagiat`, `copy_paste_detected`, `final_score`, `verdict` (ex. `"OK"`, `"SUSPECT"`, `"TRICHE PROBABLE"`).

---

## 2. Test complet avec le script Python (recommandé)

Un script exécute **tous les tests** contre le modèle sur Hugging Face uniquement (aucun appel local).

### Lancer le test complet

```bash
cd C:\Users\Negza\Desktop\Modele_Cheat
python scripts/test_complet_huggingface.py
```

Ce script :

1. **GET /health** – vérifie que l’API HF répond  
2. **POST /analyze** – code type “humain” (attendu : verdict OK ou proche)  
3. **POST /analyze** – code type “IA/cheat” (attendu : SUSPECT ou TRICHE PROBABLE)  
4. **POST /analyze** – code vide  
5. **POST /analyze** – code long (stress léger)  
6. **POST /human_decision** – enregistre une décision (pour l’apprentissage)  
7. **POST /sync_storage** – sync du storage (peut être 503 si HF_REPO/HF_TOKEN non configurés)  
8. **POST /retrain** – ignoré par défaut (voir ci-dessous)

En fin d’exécution, le script affiche soit **TOUS LES TESTS API (Hugging Face) OK**, soit le nombre d’erreurs.

### Tester aussi le ré-entraînement (optionnel)

Si tu as configuré `RETRAIN_SECRET` sur le Space et que tu as assez de décisions :

```bash
set RETRAIN_SECRET=ton_secret
python scripts/test_complet_huggingface.py --retrain
```

Sous Linux/macOS :

```bash
export RETRAIN_SECRET=ton_secret
python scripts/test_complet_huggingface.py --retrain
```

### Changer l’URL du Space (autre déploiement)

```bash
set ANTI_CHEAT_BASE_URL=https://ton-space.hf.space
python scripts/test_complet_huggingface.py
```

---

## 3. Tester avec des dépôts GitHub (verdict par utilisateur)

Pour obtenir un **verdict final** (triche / ne triche pas / suspect) à partir du **code d’un repo GitHub**, utilise :

```bash
python scripts/test_complet_user.py https://github.com/utilisateur/repo
```

Plusieurs repos :

```bash
python scripts/test_complet_user.py https://github.com/user1/repo1 https://github.com/user2/repo2
```

Ce script :

- Utilise **uniquement** l’API Hugging Face (pas de modèle local)  
- Récupère le code des fichiers du repo (Python, JS, etc.)  
- Envoie tout à **POST /analyze** sur le Space  
- Affiche pour chaque repo : **score_ia**, **verdict**, puis **RESULTAT FINAL : CET UTILISATEUR TRICHE / NE TRICHE PAS / SUSPECT**

Au démarrage, il fait aussi une petite vérification du modèle (1 code OK + 1 code “cheat”) pour confirmer que le modèle HF répond bien.

---

## 4. Résumé : quoi utiliser selon le besoin

| Objectif | Commande / outil |
|----------|-------------------|
| Vérifier que l’API HF répond | `curl .../health` ou `python scripts/test_complet_huggingface.py` |
| Tester toute l’API (health, analyze, human_decision, sync, etc.) | `python scripts/test_complet_huggingface.py` |
| Tester le modèle sur du code “à la main” | `curl .../analyze` avec ton JSON ou `test_complet_huggingface.py` (étapes 2–5) |
| Verdict pour un ou plusieurs repos GitHub | `python scripts/test_complet_user.py <url_github> [url2 ...]` |
| Tester le ré-entraînement sur le Space | `RETRAIN_SECRET=... python scripts/test_complet_huggingface.py --retrain` |

---

## 5. En cas d’erreur

- **Pas de réponse / timeout** : vérifier que le Space est bien **Running** sur la page du Space HF.  
- **404** : l’endpoint n’existe pas → pousser la dernière version du code sur le Space (voir `DEPLOY_HF_SPACES.md`).  
- **503 sur /sync_storage ou /retrain** : normal si `HF_REPO` et `HF_TOKEN` (et éventuellement `RETRAIN_SECRET`) ne sont pas encore configurés dans les paramètres du Space.

Tous ces tests ciblent **uniquement le modèle déployé sur Hugging Face** ; aucun test ne lance ni n’appelle le modèle en local.
