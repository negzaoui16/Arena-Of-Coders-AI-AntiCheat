# Intégrer le modèle anti-triche dans ta plateforme de challenges

Ce document décrit comment utiliser l’API anti-triche pour **analyser les rooms** de ton application : plateforme de challenges techniques gamifiés (rooms par domaine, soumissions GitHub, badges/niveaux, entreprises qui créent des rooms avec ou sans IA).

---

## Rôle du modèle dans ton application

- **Quand** : à chaque soumission d’un participant (lien GitHub ou code soumis dans une room).
- **Objectif** : analyser le code et les comportements pour **limiter la triche** tout en respectant les règles de la room (ex. « avec ou sans utilisation de l’IA »).
- **Comportement** : l’API retourne un **verdict** et des **scores** (IA, plagiat, copier-coller). C’est à ta plateforme de décider quoi en faire (affichage, flag modération, blocage, etc.), pas de blocage automatique côté API.

---

## 1. À quel moment appeler l’API

### À la soumission dans une room

1. Le participant soumet sa solution (lien GitHub ou code dans l’éditeur).
2. Ta plateforme récupère le **code source** (clone GitHub, contenu de l’éditeur, ou agrégat des fichiers du projet).
3. Tu appelles **POST /analyze** avec :
   - le **code** (string : contenu des fichiers principaux concaténés ou fichier principal),
   - un **submission_id** (ex. `room_123_user_456_sub_789`) pour tracer et pour les décisions humaines plus tard,
   - **room_params** selon la room :
     - `allow_ai` : `true` si la room autorise l’IA, `false` sinon,
     - `anti_cheat_enabled` : `true` si la room active l’analyse anti-triche,
     - `room_type` : ex. `"algorithm"`, `"web"`, `"data"`, `"mobile"`, etc.
   - **typing_stats** (optionnel) : si tu enregistres le temps de frappe / gros blocs collés dans l’éditeur, pour améliorer la détection copier-coller.

Exemple de corps de requête :

```json
{
  "code": "contenu du ou des fichiers soumis...",
  "submission_id": "room_abc_user_xyz_sub_001",
  "room_params": {
    "allow_ai": false,
    "anti_cheat_enabled": true,
    "room_type": "algorithm"
  },
  "typing_stats": {
    "total_typing_time_ms": 120000,
    "block_insertions": []
  }
}
```

Réponse type :

```json
{
  "score_ia": 0.12,
  "score_plagiat": 0.05,
  "copy_paste_detected": false,
  "score_copy_paste": 0.0,
  "final_score": 0.068,
  "verdict": "OK",
  "submission_id": "room_abc_user_xyz_sub_001"
}
```

---

## 2. Utiliser le verdict dans la room

- **verdict** : `"OK"` | `"SUSPECT"` | `"TRICHE PROBABLE"`.
- **final_score** : 0–1 (plus c’est haut, plus c’est suspect).

Tu peux par exemple :

- **Room sans IA** (`allow_ai: false`) :  
  - Si `verdict === "OK"` → accepter la soumission, compter pour le classement.  
  - Si `"SUSPECT"` → afficher un avertissement, ou mettre en file modération.  
  - Si `"TRICHE PROBABLE"` → ne pas compter pour le classement, ou soumettre à validation entreprise / modérateur.

- **Room avec IA** (`allow_ai: true`) :  
  Utiliser surtout le **plagiat** et le **copier-coller** (score_ia peut être ignoré ou affiché à titre informatif).

- **Entreprises** :  
  Exposer verdict + scores dans l’interface (ex. tableau des soumissions par room) pour qu’elles identifient les talents et les cas à vérifier.

Tu stockes côté plateforme : `submission_id`, `verdict`, `score_ia`, `score_plagiat`, `final_score`, et éventuellement `copy_paste_detected`.

---

## 3. Décisions humaines (modération / entreprises)

Quand un modérateur ou une entreprise valide une soumission :

- **OK (humain / pas de triche)** → `human_label: 0`
- **Triche / IA** → `human_label: 1`

Appel à faire :

**POST /human_decision**

```json
{
  "submission_id": "room_abc_user_xyz_sub_001",
  "human_label": 0,
  "comment": "Validé par modérateur"
}
```

Utilise le **même submission_id** que celui renvoyé par **POST /analyze**. Ces décisions servent au ré-entraînement du modèle (voir plus bas).

---

## 4. Analyser un repo GitHub (humain vs IA)

Un script permet de **vérifier si le code d’un dépôt GitHub** est plutôt humain ou écrit avec un modèle IA :

```powershell
python scripts/analyze_github_repo.py https://github.com/owner/repo
python scripts/analyze_github_repo.py owner/repo
```

Le script :
1. Récupère les fichiers de code du repo (`.py`, `.js`, `.ts`, `.java`, etc.) via l’API GitHub.
2. Envoie le contenu à l’API anti-triche (**POST /analyze**).
3. Affiche **score_ia** et **verdict** : plus le score_ia est bas, plus le code est jugé « humain » ; plus il est haut, plus il est jugé « IA ».

Utile pour : vérifier une soumission par lien GitHub avant de l’accepter dans une room, ou pour un modérateur qui veut un avis automatique.

---

## 5. Récupérer le code depuis un lien GitHub (intégration backend)

Pour une soumission par **lien GitHub** :

1. Côté backend : clone ou API GitHub pour récupérer les fichiers du repo (ex. arborescence du challenge).
2. Concaténer les fichiers pertinents (ex. `main.py`, `solution.py`, ou tous les `.py` du repo) en une seule string.
3. Envoyer cette string dans **POST /analyze** en tant que `code`.

Exemple minimal (Node.js) :

```javascript
// après avoir récupéré le contenu du repo (ex. via GitHub API)
const code = files.map(f => f.content).join('\n\n');
const res = await fetch('https://negzaoui-anti-cheat-coding.hf.space/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    code,
    submission_id: submissionId,
    room_params: { allow_ai: room.allow_ai, anti_cheat_enabled: true, room_type: room.type }
  })
});
const result = await res.json();
// result.verdict, result.final_score, result.score_ia, ...
```

Même logique en Python, PHP, etc. : un seul champ `code` (string) à remplir.

---

## 6. Apprentissage continu (optionnel)

Pour que le modèle s’améliore avec l’usage sur ta plateforme :

1. **Décisions humaines** : continuer à appeler **POST /human_decision** quand les modérateurs / entreprises valident ou invalident des soumissions.
2. **Sync** : appeler **POST /sync_storage** (ex. périodiquement ou après batch de décisions) pour sauvegarder les données sur le Hub.
3. **Ré-entraînement** : appeler **POST /retrain?min_samples=10** (avec `X-Retrain-Secret` si configuré) quand tu as assez de nouvelles décisions ; le modèle « latest » est alors mis à jour sur le Hub.

Cela permet d’adapter le modèle aux types de code et aux règles de tes rooms (Mobile, Web, Data, IA, etc.) au fil du temps.

---

## 7. Résumé par acteur

| Acteur | Action |
|--------|--------|
| **Participant** | Soumet code (GitHub ou éditeur) dans une room. |
| **Backend plateforme** | Récupère le code → **POST /analyze** avec `room_params` et `submission_id` → stocke verdict + scores. |
| **Plateforme** | Affiche classement, badges, niveaux ; applique les règles de la room (accepter / flag / exclure selon verdict). |
| **Entreprise / Modérateur** | Consulte les soumissions et verdicts ; valide ou invalide → **POST /human_decision** avec le `submission_id`. |
| **Admin / Cron** | Optionnel : **POST /sync_storage** puis **POST /retrain** pour améliorer le modèle. |

---

## URL de l’API et doc

- **Base** : `https://negzaoui-anti-cheat-coding.hf.space`
- **Doc interactive** : https://negzaoui-anti-cheat-coding.hf.space/docs
- **Détail des requêtes/réponses** : voir `API_USAGE.md` dans ce dépôt.

En résumé : tu utilises ce modèle pour **analyser chaque soumission dans une room** (code + paramètres de room), puis tu exploites le **verdict** et les **scores** dans ta logique métier (classement, modération, règles avec/sans IA), tout en alimentant le modèle avec les **décisions humaines** pour le faire évoluer.
