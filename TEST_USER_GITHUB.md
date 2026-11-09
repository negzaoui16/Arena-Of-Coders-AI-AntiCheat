# Tester un utilisateur (lien GitHub) : TRICHE ou NON ?

Le modèle est déployé sur **Hugging Face**. Pour savoir si **un utilisateur triche ou non** à partir de son repo GitHub, utilise le script de test complet.

---

## Commande pour tout utilisateur

**Une seule ligne** (remplace par l’URL GitHub du repo à analyser) :

```powershell
python scripts/test_complet_user.py https://github.com/UTILISATEUR/REPO
```

**Exemples :**

```powershell
python scripts/test_complet_user.py https://github.com/negzaoui16/anti-cheat-coding
python scripts/test_complet_user.py negzaoui16/anti-cheat-coding
```

**Plusieurs utilisateurs d’un coup :**

```powershell
python scripts/test_complet_user.py https://github.com/user1/repo1 https://github.com/user2/repo2
```

---

## Résultat final pour chaque utilisateur

À la fin, le script affiche pour **chaque user/repo** :

| Résultat affiché | Signification |
|------------------|----------------|
| **CET UTILISATEUR NE TRICHE PAS** | Code considéré comme probablement humain (verdict OK). |
| **CET UTILISATEUR EST SUSPECT** | À vérifier manuellement (verdict SUSPECT). |
| **CET UTILISATEUR TRICHE** | Code considéré comme probablement généré par IA (triche). |

Un **tableau récapitulatif** liste tous les utilisateurs testés avec leur résultat (NE TRICHE PAS / SUSPECT / TRICHE).

---

## Vérifier que le modèle fonctionne (OK + cheat)

Avant de tester des repos, le script lance une **vérification** :

- Un code **OK** (humain) → verdict **OK**.
- Un code **CHEAT** (style IA) → verdict **SUSPECT** ou **TRICHE PROBABLE**.

Si ces deux cas sont bien distingués, le modèle Hugging Face répond correctement.

---

## Prérequis

- **Python 3** installé sur la machine.
- **Aucune clé API** : le script appelle l’API publique  
  **https://negzaoui-anti-cheat-coding.hf.space**

---

## Résumé

| Action | Commande |
|--------|----------|
| Tester 1 utilisateur (son repo GitHub) | `python scripts/test_complet_user.py https://github.com/user/repo` |
| Tester plusieurs utilisateurs | `python scripts/test_complet_user.py url1 url2 url3` |
| Voir la démo (vérif modèle + usage) | `python scripts/test_complet_user.py` |

**Résultat final** : pour chaque utilisateur, le script affiche clairement **il triche** ou **il ne triche pas** (ou **suspect**).
