# Déploiement sur Hugging Face Spaces

Ce guide explique comment **pousser** le modèle anti-triche sur **Hugging Face Spaces** pour qu’il tourne en continu (API toujours disponible).

**Space utilisé :** [Negzaoui/anti-cheat-coding](https://huggingface.co/spaces/Negzaoui/anti-cheat-coding)

---

## Prérequis

- Un compte [Hugging Face](https://huggingface.co/join)
- Git installé
- Un **token d’accès** avec droits d’écriture pour pousser : [Créer un token](https://huggingface.co/settings/tokens) (à utiliser comme mot de passe Git quand on te le demande)

---

## Pousser vers Negzaoui/anti-cheat-coding

**Option A – Cloner le Space, copier le code, puis push :**

```powershell
cd C:\Users\Negza\Desktop\Modele_Cheat
git clone https://huggingface.co/spaces/Negzaoui/anti-cheat-coding hf-space
cd hf-space
```

Copier les fichiers du projet dans le clone :

```powershell
Copy-Item ..\Dockerfile .
Copy-Item ..\.dockerignore .
Copy-Item ..\requirements.txt .
Copy-Item ..\config.py .
Copy-Item ..\src -Destination . -Recurse
Copy-Item ..\scripts -Destination . -Recurse
Copy-Item ..\data -Destination . -Recurse
```

Puis commit et push (quand on demande le mot de passe, utilise ton **token HF**) :

```powershell
git add .
git commit -m "Deploy anti-cheat API"
git push
```

**Option B – Si ton projet est déjà un dépôt Git :**

```powershell
cd C:\Users\Negza\Desktop\Modele_Cheat
git remote add space https://huggingface.co/spaces/Negzaoui/anti-cheat-coding
git push space main
```

(À la demande de mot de passe, utilise ton token : [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).)

**URL de l’API une fois le Space en Running :**  
https://negzaoui-anti-cheat-coding.hf.space  
(endpoints : `/health`, `/analyze`, `/docs`)

**Personnalisation du Space (comme dans le guide HF) :**  
Le `README.md` du projet contient déjà le bloc YAML en tête (title, emoji, colorFrom, colorTo, sdk: docker). Quand tu pousses ce README dans le Space, la page HF affichera le titre « Anti Cheat Coding », l’emoji 🔒 et les couleurs choisies.

---

## 1. Créer un nouveau Space (si besoin d’un autre)

1. Va sur [huggingface.co/spaces](https://huggingface.co/spaces)
2. Clique sur **Create new Space**
3. Renseigne :
   - **Name** : par ex. `anti-cheat-coding`
   - **License** : MIT (ou autre)
   - **SDK** : **Docker** (obligatoire pour une API FastAPI)
   - **Hardware** : CPU basic (gratuit)
4. Clique sur **Create Space**

---

## 2. Cloner le Space et pousser le code

Dans un terminal, à la racine de ton projet :

```bash
# Se placer dans le projet
cd C:\Users\Negza\Desktop\Modele_Cheat

# Cloner le Space (remplace TON_USERNAME et TON_SPACE par tes valeurs)
git clone https://huggingface.co/spaces/TON_USERNAME/TON_SPACE hf-space
cd hf-space
```

Ensuite copier les fichiers nécessaires dans le clone du Space :

**Windows (PowerShell) :**
```powershell
Copy-Item ..\Dockerfile .
Copy-Item ..\.dockerignore .
Copy-Item ..\requirements.txt .
Copy-Item ..\config.py .
Copy-Item ..\src -Destination . -Recurse
Copy-Item ..\scripts -Destination . -Recurse
Copy-Item ..\data -Destination . -Recurse
```

**Ou** si ton projet est déjà un dépôt Git, tu peux simplement ajouter le remote HF et push :

```bash
cd C:\Users\Negza\Desktop\Modele_Cheat
git remote add space https://huggingface.co/spaces/TON_USERNAME/TON_SPACE
git push space main
```

(Adapte `main` en `master` si besoin.)

---

## 3. Fichiers requis dans le Space

Le dépôt du Space doit contenir au minimum :

- `Dockerfile` (port **7860** pour HF Spaces)
- `requirements.txt`
- `config.py`
- `src/` (tout le package)
- `scripts/` (dont `train_initial_model.py`)
- `data/` (dont `data/solutions/` pour la détection de plagiat)

Le modèle **v1** est recréé au build via `train_initial_model.py`, pas besoin de pousser `models/`.

---

## 4. Premier déploiement

1. Après le **push** (ou l’upload des fichiers sur le site), Hugging Face **build** l’image Docker puis **lance** le conteneur.
2. Le build peut prendre quelques minutes (pip install + entraînement du modèle v1).
3. Une fois le statut **Running**, l’API est disponible à l’URL du Space.

**URL de l’API (pour ce Space) :**  
`https://negzaoui-anti-cheat-coding.hf.space`

---

## 5. Tester l’API en ligne

**Santé :**
```bash
curl https://negzaoui-anti-cheat-coding.hf.space/health
```

**Analyse d’un extrait de code :**
```bash
curl -X POST "https://negzaoui-anti-cheat-coding.hf.space/analyze" -H "Content-Type: application/json" -d "{\"code\": \"def hello():\\n    print('world')\"}"
```

**Documentation interactive :**  
Ouvre dans le navigateur :  
https://negzaoui-anti-cheat-coding.hf.space/docs

---

## 6. Apprentissage continu (le modèle devient plus intelligent)

Pour que le modèle **apprenne avec le temps** sur le Space :

1. **Variables d'environnement** (Settings → Variables and secrets du Space) :
   - **HF_REPO** = ton Space, ex. `Negzaoui/anti-cheat-coding`
   - **HF_TOKEN** = ton token HF avec droit d’écriture (pour pousser le modèle et le storage)
   - **HF_REPO_TYPE** = `space` (défaut)
   - **RETRAIN_SECRET** (optionnel) = secret pour protéger `POST /retrain`

2. **Workflow** :
   - Les correcteurs envoient des décisions via `POST /human_decision` (0 = OK, 1 = triche).
   - Tu appelles `POST /sync_storage` pour sauvegarder les données sur le Hub (évite de les perdre au redémarrage).
   - Quand tu as assez de décisions (ex. 10+), tu appelles `POST /retrain?min_samples=10` (avec header `X-Retrain-Secret: ton_secret` si configuré).
   - Le nouveau modèle est poussé sur le Hub et rechargé en mémoire ; au prochain redémarrage du Space, ce modèle sera chargé automatiquement.

Voir **API_USAGE.md** section « Apprentissage continu » pour les exemples cURL.

---

## 7. Résumé

| Étape | Action |
|-------|--------|
| 1 | Créer un Space avec SDK **Docker** |
| 2 | Cloner le Space, copier le code (ou push depuis ton repo) |
| 3 | S’assurer que `Dockerfile`, `src/`, `scripts/`, `data/`, `config.py`, `requirements.txt` sont présents |
| 4 | Push → build automatique → API disponible sur l’URL du Space |
| 5 | (Optionnel) Configurer HF_REPO + HF_TOKEN pour l’apprentissage continu |

L’API reste **toujours exécutée** tant que le Space est actif (gratuit avec limite d’usage selon le type de Space).
