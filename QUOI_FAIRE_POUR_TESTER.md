# Quoi faire pour tester

## 1. Tester l’API en ligne (sans configurer le Hub)

- Ouvre un terminal dans le projet.
- Lance le script de test :

```powershell
cd C:\Users\Negza\Desktop\Modele_Cheat
python scripts\test_tout_api.py
```

**Ce que le script fait :**

1. **GET /health** – vérifie que l’API répond.
2. **POST /analyze** – envoie du code, affiche le verdict et le `submission_id`.
3. **POST /human_decision** – enregistre une décision humaine (0 = OK) pour cette soumission.
4. **POST /sync_storage** – peut renvoyer 503 si `HF_REPO` / `HF_TOKEN` ne sont pas configurés (c’est normal).
5. **POST /retrain** – peut renvoyer 400 (pas assez de données) ou 503 (Hub non configuré) ; c’est normal.

Si les étapes 1 et 2 fonctionnent, l’API de base est OK.

**Si tu as 404 sur [4] et [5]** : le Space tourne encore une ancienne version sans `/sync_storage` ni `/retrain`. Il faut pousser le code à jour → voir la section « Mettre à jour le Space » ci-dessous.

---

## 2. Mettre à jour le Space (si 404 sur /sync_storage et /retrain)

Le Space doit exécuter la **dernière version** du code (avec `sync_storage` et `retrain`). Depuis la racine du projet :

```powershell
cd C:\Users\Negza\Desktop\Modele_Cheat

# 1. Copier le code dans le clone du Space
Copy-Item .\config.py .\hf-space\ -Force
Copy-Item .\requirements.txt .\hf-space\ -Force
Copy-Item .\Dockerfile .\hf-space\ -Force
Copy-Item .\src .\hf-space\ -Recurse -Force
Copy-Item .\scripts .\hf-space\ -Recurse -Force
Copy-Item .\data .\hf-space\ -Recurse -Force

# 2. Aller dans hf-space et pousser
cd hf-space
git add .
git status
git commit -m "Add sync_storage and retrain endpoints"
git push origin main
```

Quand Git demande le mot de passe, colle ton **token Hugging Face** (avec droit « write »).  
Après le build (quelques minutes), relance `python scripts\test_tout_api.py` : [4] et [5] ne devraient plus être en 404 (ils pourront être 503 si tu n’as pas encore configuré HF_REPO / HF_TOKEN).

---

## 3. Tester en local (API sur ta machine)

1. Crée un environnement virtuel et installe les dépendances :

```powershell
cd C:\Users\Negza\Desktop\Modele_Cheat
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Lance l’API (port 7860 comme sur le Space) :

```powershell
uvicorn src.api:app --host 0.0.0.0 --port 7860
```

3. Dans un **autre** terminal, lance le test en pointant vers le local :

- Ouvre `scripts\test_tout_api.py`.
- Change la première ligne de `BASE` en :  
  `BASE = "http://localhost:7860"`.
- Puis exécute :

```powershell
cd C:\Users\Negza\Desktop\Modele_Cheat
.\venv\Scripts\Activate.ps1
python scripts\test_tout_api.py
```

Tu verras les mêmes appels (health, analyze, human_decision, sync_storage, retrain). En local, sans `HF_REPO` / `HF_TOKEN`, sync et retrain échoueront ou ne feront rien ; ce qui compte c’est que health et analyze marchent.

---

## 4. Tester l’apprentissage continu sur le Space (optionnel)

Pour que **sync_storage** et **retrain** fonctionnent sur le Space :

1. Va sur ton Space : **Settings → Variables and secrets**.
2. Ajoute :
   - **HF_REPO** = `Negzaoui/anti-cheat-coding`
   - **HF_TOKEN** = ton token Hugging Face (avec droit d’écriture)
   - **RETRAIN_SECRET** (optionnel) = un mot de passe pour protéger `/retrain`

3. Redémarre le Space (ou attends le prochain build).

4. Pour tester **/retrain** avec le secret : dans `scripts\test_tout_api.py`, mets ton secret :

   `RETRAIN_SECRET = "ton_secret"`

5. Relance :

```powershell
python scripts\test_tout_api.py
```

Si tu as assez de décisions humaines (au moins 10), l’étape 5 devrait retourner une réponse avec `version`, `accuracy`, `n_samples`.

---

## Fichiers utiles

| Fichier | Rôle |
|--------|------|
| `scripts\test_tout_api.py` | Script à lancer pour tester (health, analyze, human_decision, sync_storage, retrain). |
| `scripts\test_api_online.py` | Test minimal (health + analyze) sur l’URL du Space. |
| `API_USAGE.md` | Détail des endpoints et exemples. |
| `DEPLOY_HF_SPACES.md` | Déploiement et config du Space. |

En résumé : pour un test rapide, lance `python scripts\test_tout_api.py` et vérifie que les étapes 1 et 2 sont OK.
