---
title: Anti Cheat Coding
emoji: 🔒
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Modèle Anti-triche - Coding Challenges

Système de détection de triche pour une application de coding challenges (rooms) : détection du **copier-coller**, du **plagiat** et du **code généré par IA** (ChatGPT, Copilot, etc.). Le modèle retourne un **score de suspicion** et ne bloque pas automatiquement l'utilisateur.

- **Langage** : Python  
- **Exécution** : locale, CPU uniquement  
- **API** : REST (FastAPI)  
- **ML** : scikit-learn (RandomForest), apprentissage continu par cycles contrôlés  
- **Déploiement** : voir [DEPLOY_HF_SPACES.md](DEPLOY_HF_SPACES.md) pour mettre l’API en ligne sur **Hugging Face Spaces** (toujours exécutée).
- **Utiliser l'API dans un autre projet** : voir [API_USAGE.md](API_USAGE.md) (URL, exemples JS/Python).

---

## Est-ce qu'il apprend et devient plus intelligent ?

**Oui**, mais uniquement **par cycles contrôlés** (pas en temps réel) :

1. **En production** : chaque analyse est enregistrée (code + scores + verdict) dans `storage/predictions.jsonl`.
2. **Validation humaine** : un correcteur consulte les cas suspects, décide (OK ou triche) et envoie sa décision via **POST /human_decision** (`human_label`: 0 = OK, 1 = triche). Ces décisions sont stockées dans `storage/human_decisions.jsonl`.
3. **Ré-entraînement** : quand suffisamment de décisions sont disponibles (ex. 10+), on lance le script de ré-entraînement :  
   `python -m src.training --min-samples 10`  
   Un **nouveau modèle** (v2, v3, …) est créé à partir des paires (code, décision humaine).
4. **Mise en production** : on change la version du modèle utilisée (dans `config.py` : `DEFAULT_MODEL_VERSION`) ou on l’expose via l’API. Le nouveau modèle est alors utilisé pour les prochaines analyses.

Ainsi, **avec le temps et les retours humains**, le modèle s’améliore sur les cas réels de votre plateforme. Il ne s’adapte pas tout seul en temps réel : chaque amélioration passe par un cycle « collecte → décisions humaines → ré-entraînement → déploiement ».

---

## Arborescence du projet

```
Modele_Cheat/
├── config.py                 # Configuration (poids, seuils, chemins)
├── requirements.txt
├── README.md
├── data/
│   ├── examples/             # Exemples de requêtes API
│   │   ├── sample_request.json
│   │   └── sample_request_copy_paste.json
│   └── solutions/            # Solutions de référence (détection plagiat)
│       ├── example_solution_1.py
│       └── example_solution_2.py
├── models/                   # Modèles versionnés (v1, v2, ...)
│   └── model_v1.pkl          # (créé après entraînement initial)
├── storage/                  # Prédictions + décisions humaines (JSONL)
│   ├── predictions.jsonl
│   ├── human_decisions.jsonl
│   └── datasets/             # Datasets générés pour ré-entraînement
├── scripts/
│   └── train_initial_model.py   # Création du modèle v1
└── src/
    ├── __init__.py
    ├── features.py           # Extraction de features du code
    ├── model_ia.py           # Modèle ML (détection IA)
    ├── copy_paste.py         # Détection copier-coller (règles)
    ├── plagiarism.py         # TF-IDF + cosine (plagiat)
    ├── scoring.py            # Score final + verdict
    ├── storage.py            # Stockage prédictions / décisions
    ├── training.py           # Script de ré-entraînement
    └── api.py                # API FastAPI
```

---

## Résumé des parties

| Partie | Rôle |
|--------|------|
| **features.py** | Extrait du code des indicateurs (longueur des lignes, variance d’indentation, complexité, commentaires, etc.) pour le modèle ML. |
| **model_ia.py** | Classifieur RandomForest (scikit-learn) qui prédit la probabilité que le code soit généré par IA (score 0–1). Charge/sauvegarde avec versioning (v1, v2). |
| **copy_paste.py** | Règles métier : gros blocs insérés d’un coup, temps de frappe trop court par ligne → booléen + score copier-coller. |
| **plagiarism.py** | TF-IDF sur le code normalisé + similarité cosinus avec un ensemble de solutions existantes → score plagiat 0–1. |
| **scoring.py** | Combine les trois scores avec des poids (0.4 IA, 0.3 plagiat, 0.3 copier-coller) et produit le verdict : OK / SUSPECT / TRICHE PROBABLE. |
| **storage.py** | Enregistre les prédictions (JSONL) et les décisions humaines ; construit un dataset pour le ré-entraînement. |
| **training.py** | Script de ré-entraînement : dataset à partir des décisions validées, entraînement d’un nouveau modèle, sauvegarde avec nouvelle version. |
| **api.py** | API REST FastAPI : `POST /analyze`, `POST /human_decision`, etc. |

---

## Installation et exécution locale

### 1. Environnement virtuel et dépendances

**Windows (PowerShell) :**
```powershell
cd C:\Users\Negza\Desktop\Modele_Cheat
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS :**
```bash
cd Modele_Cheat
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Créer le modèle initial (v1)

Sans cette étape, le score IA sera toujours 0 (pas de blocage, comportement par défaut).

```bash
python scripts/train_initial_model.py
```

Cela crée `models/model_v1.pkl` à partir d’exemples minimalistes (code humain vs style IA).

### 3. Lancer l’API

Depuis la racine du projet (avec le venv activé) :

```bash
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

Ou avec le Python du venv directement :
```bash
.\venv\Scripts\python.exe -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

- **Documentation** : http://localhost:8000/docs  
- **Santé** : GET http://localhost:8000/health  

### 4. Exemple d’appel à l’API

**POST /analyze**

```bash
curl -X POST "http://localhost:8000/analyze" -H "Content-Type: application/json" -d "{\"code\": \"def hello():\\n    print('world')\"}"
```

Ou avec un fichier :

```bash
curl -X POST "http://localhost:8000/analyze" -H "Content-Type: application/json" -d @data/examples/sample_request.json
```

**Réponse type :**

```json
{
  "score_ia": 0.12,
  "score_plagiat": 0.05,
  "copy_paste_detected": false,
  "score_copy_paste": 0.0,
  "final_score": 0.068,
  "verdict": "OK",
  "submission_id": "sub_1234567890"
}
```

### 5. Enregistrer une décision humaine (pour ré-entraînement)

```bash
curl -X POST "http://localhost:8000/human_decision" -H "Content-Type: application/json" -d "{\"submission_id\": \"sub_1234567890\", \"human_label\": 0, \"comment\": \"OK manuel\"}"
```

- `human_label`: **0** = OK / humain, **1** = triche / IA.

### 6. Ré-entraînement périodique (cycles contrôlés)

Après avoir accumulé des prédictions et des décisions humaines :

```bash
python -m src.training --min-samples 10
```

Une nouvelle version du modèle (v2, v3, …) est créée dans `models/`. Pour utiliser une version précise, modifier `DEFAULT_MODEL_VERSION` dans `config.py` ou ajouter un paramètre de version dans l’API.

---

## Score final et verdict

- **Formule** :  
  `FinalScore = 0.4 * score_ia + 0.3 * score_plagiat + 0.3 * score_copier_coller`

- **Verdict** :  
  - **OK** : `FinalScore < 0.35`  
  - **SUSPECT** : `0.35 ≤ FinalScore < 0.65`  
  - **TRICHE PROBABLE** : `FinalScore ≥ 0.65`  

Les seuils et poids sont configurables dans `config.py`.

---

## Qualité du code (PFE)

- Code modulaire, commenté, séparation claire modèle / API / utils / training.  
- Pas de blocage automatique : le système fournit un score et un verdict pour décision humaine.  
- Apprentissage continu uniquement par **cycles contrôlés** (script de ré-entraînement + versioning).  
- Exécutable en local sur CPU (scikit-learn, pas de GPU requis).  

---

## Licence / Contexte

Projet académique (PFE). Adapter les seuils et les jeux de données selon le contexte pédagogique.
