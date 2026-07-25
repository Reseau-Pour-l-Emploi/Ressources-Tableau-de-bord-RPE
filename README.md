# Glossaire du tableau de bord RPE

Glossaire consultable (recherche, A-Z, filtre par page) des dimensions et mesures des 7 bases du tableau de bord RPE, avec contribution communautaire et modération admin.

## Structure

```
index.html            page publique
admin.html             back-office de modération
firebase-config.js     config Firebase + email(s) admin (A COMPLETER)
firestore.rules        règles de sécurité à publier dans Firebase
data/glossary.json         glossaire de base, généré depuis l'Excel source
data/pages_sources.json    liste des pages/sources, générée depuis les scripts
scripts/                régénération de data/ depuis l'Excel
assets/, fonts/         identité visuelle RPE
```

## Mise en place Firebase (une fois)

1. Créer un projet sur https://console.firebase.google.com
2. Firestore Database > créer en mode production.
3. Authentication > Sign-in method > activer **Anonyme** et **Email/mot de passe**.
4. Authentication > Users > créer le compte administrateur (email + mot de passe de ton choix).
5. Paramètres du projet > Vos applications > Web > copier `firebaseConfig` dans `firebase-config.js`, et renseigner ce même email dans `ADMIN_EMAILS`.
6. Reporter cet email dans `firestore.rules` (fonction `isAdmin`), puis publier ces règles dans Firestore Database > Règles.

Connexion ensuite sur `admin.html` avec l'email et le mot de passe choisis à l'étape 4.

## Déploiement

Pousser le dépôt sur GitHub, activer GitHub Pages (branche `main`, racine).

## Régénérer le glossaire

Si l'Excel source évolue :

```
cd scripts
python3 parse_glossary.py
python3 build_glossary.py
```

Régénère `data/glossary.json` et `data/pages_sources.json`. Pour un nouvel onglet Excel, ajouter sa correspondance dans `BASE_PAGES`/`BASE_SOURCES`/`BASE_LABELS` en tête de `build_glossary.py`.

## Notions clés

- **Groupe** : données aux définitions proches (ex. "Accès à l'emploi"), consolidées en une fiche.
- **Variable hiérarchique** : mêmes données à différents niveaux d'agrégation d'un référentiel (`hierarchie: {nom, niveau}`, niveau 0 = plus détaillé), avec ex æquo possibles. Seul le niveau le plus détaillé s'affiche par défaut.
- **Compteurs** (`compteurs/{id}`) : nombre de demandes en attente par champ. En cas d'incohérence, bouton "🔄 Réparer les compteurs" dans `admin.html`.
- **Propositions** : `ajout`, `modification`, `suppression`, `groupe_lot`, `hierarchie_lot`, `groupe_suppression`, `hierarchie_suppression`. Chacune est visible et éditable par l'admin avant validation, qui écrit dans `glossaire_ajouts`/`glossaire_overrides`.

## Notes

- Aucune donnée personnelle stockée côté client : l'email des contributeurs n'est lisible que par l'admin (règles Firestore).
- `data/glossary.json` n'est pas rechargé avec anti-cache : après régénération, un Ctrl+Shift+R peut être nécessaire pour voir la nouvelle version.
