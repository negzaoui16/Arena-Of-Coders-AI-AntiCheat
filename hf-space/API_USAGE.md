# Utiliser l'API anti-triche dans ton projet

Une fois le Space Hugging Face en **Running**, n'importe qui peut appeler l'API depuis un site web, une app mobile, un backend, etc. Aucune clé obligatoire pour les requêtes (API publique).

---

## URL de base

- **En ligne (Hugging Face)** : `https://negzaoui-anti-cheat-coding.hf.space`
- **En local** : `http://localhost:8000`

---

## Endpoints

| Méthode | URL | Description |
|--------|-----|-------------|
| GET | `/health` | Vérifier que l'API répond |
| POST | `/analyze` | Analyser du code (scores + verdict) |
| POST | `/human_decision` | Enregistrer une décision humaine (pour ré-entraînement) |
| POST | `/sync_storage` | Envoyer le storage local vers le Hub (persistance des données) |
| POST | `/retrain` | Ré-entraîner le modèle et le pousser sur le Hub (modèle plus intelligent) |
| GET | `/docs` | Documentation interactive (Swagger) |

---

## 1. Vérifier l'API (health)

```bash
curl https://negzaoui-anti-cheat-coding.hf.space/health
```

Réponse : `{"status":"ok"}`

---

## 2. Analyser du code (POST /analyze)

**Corps de la requête (JSON) :**

```json
{
  "code": "def hello():\n    print('world')",
  "typing_stats": {
    "total_typing_time_ms": 5000,
    "block_insertions": [],
    "events": []
  },
  "room_params": {
    "allow_ai": false,
    "anti_cheat_enabled": true,
    "room_type": "algorithm"
  },
  "submission_id": "optional-id-123"
}
```

- **code** (obligatoire) : le code source à analyser (string).
- **typing_stats** (optionnel) : statistiques de frappe pour la détection copier-coller.
- **room_params** (optionnel) : paramètres de la room (autoriser IA, anti-cheat, etc.).
- **submission_id** (optionnel) : identifiant de la soumission (pour lier à une décision humaine plus tard).

**Exemple cURL :**

```bash
curl -X POST "https://negzaoui-anti-cheat-coding.hf.space/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"code\": \"def fib(n):\\n    return n if n < 2 else fib(n-1)+fib(n-2)\"}"
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

- **score_ia** : probabilité que le code soit généré par IA (0–1).
- **score_plagiat** : similarité max avec des solutions existantes (0–1).
- **copy_paste_detected** : `true` si copier-coller détecté.
- **score_copy_paste** : score copier-coller (0–1).
- **final_score** : combinaison pondérée (0–1).
- **verdict** : `"OK"` | `"SUSPECT"` | `"TRICHE PROBABLE"`.

---

## 3. Utiliser l'API depuis ton projet

### JavaScript (navigateur ou Node)

```javascript
const response = await fetch('https://negzaoui-anti-cheat-coding.hf.space/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    code: document.getElementById('code').value,
    typing_stats: { total_typing_time_ms: 5000 },
    room_params: { anti_cheat_enabled: true }
  })
});
const result = await response.json();
console.log('Verdict:', result.verdict, 'Score:', result.final_score);
```

### Python (requests)

```python
import requests

url = "https://negzaoui-anti-cheat-coding.hf.space/analyze"
payload = {
    "code": "def hello():\n    print('world')",
    "typing_stats": {"total_typing_time_ms": 5000},
    "room_params": {"anti_cheat_enabled": True}
}
r = requests.post(url, json=payload)
result = r.json()
print("Verdict:", result["verdict"], "| Score:", result["final_score"])
```

### Python (urllib, sans dépendance)

```python
import urllib.request
import json

url = "https://negzaoui-anti-cheat-coding.hf.space/analyze"
data = json.dumps({"code": "def hello():\n    print('world')"}).encode("utf-8")
req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as f:
    result = json.loads(f.read().decode())
print("Verdict:", result["verdict"])
```

---

## 4. Apprentissage continu (le modèle devient plus intelligent)

Pour que le modèle **apprenne avec le temps** sur Hugging Face :

1. **Décisions humaines** : utilise `POST /human_decision` après chaque correction (0 = OK, 1 = triche).
2. **Sauvegarder les données** : appelle `POST /sync_storage` pour envoyer les prédictions et décisions vers le Hub (évite de perdre les données au redémarrage du Space).
3. **Ré-entraîner** : appelle `POST /retrain` (éventuellement avec `?min_samples=10`) pour entraîner un nouveau modèle à partir des décisions, le pousser sur le Hub et le recharger en mémoire.

**Variables d'environnement à configurer sur le Space** (Settings → Variables and secrets) :

- `HF_REPO` = ton Space (ex: `Negzaoui/anti-cheat-coding`)
- `HF_TOKEN` = ton token HF avec droit d’écriture
- `HF_REPO_TYPE` = `space` (défaut)
- `RETRAIN_SECRET` (optionnel) = secret pour protéger `POST /retrain` ; envoie-le en header : `X-Retrain-Secret: ton_secret`

**Exemple : ré-entraînement (avec secret si configuré)**

```bash
curl -X POST "https://negzaoui-anti-cheat-coding.hf.space/retrain?min_samples=10" \
  -H "X-Retrain-Secret: ton_secret"
```

Au prochain démarrage du Space, le dernier modèle poussé sur le Hub sera chargé automatiquement.

---

## 5. Enregistrer une décision humaine (POST /human_decision)

Pour alimenter le ré-entraînement du modèle (optionnel).

```json
{
  "submission_id": "sub_1234567890",
  "human_label": 0,
  "comment": "OK après vérification"
}
```

- **human_label** : `0` = OK / humain, `1` = triche / IA.
- **submission_id** : celui retourné par POST `/analyze`.

```bash
curl -X POST "https://negzaoui-anti-cheat-coding.hf.space/human_decision" \
  -H "Content-Type: application/json" \
  -d "{\"submission_id\": \"sub_123\", \"human_label\": 0, \"comment\": \"OK\"}"
```

---

## Résumé

| Question | Réponse |
|----------|---------|
| L'API est-elle publique ? | Oui, une fois le Space en Running. |
| Faut-il une clé API ? | Non pour `/health` et `/analyze`. |
| Peut-on l'utiliser depuis un autre projet ? | Oui (web, mobile, backend, script). |
| Le modèle apprend-il avec le temps ? | Oui si tu configures HF_REPO + HF_TOKEN et appelles /human_decision puis /retrain. |
| Documentation interactive ? | https://negzaoui-anti-cheat-coding.hf.space/docs |

Tu peux partager le lien du Space ou ce fichier pour que d'autres intègrent l'API dans leur projet.
