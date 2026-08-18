# Glossaire du tableau de bord RPE

Glossaire consultable (recherche, A-Z, filtre par page, filtre par nature de fiche) des définitions de page, indicateurs de page et champs de tableaux personnalisés du tableau de bord RPE, avec contribution communautaire et modération admin.

## Structure

```
index.html                     page publique
admin.html                      back-office de modération
firebase-config.js              config Firebase + email(s) admin (A COMPLETER)
firestore.rules                 règles de sécurité à publier dans Firebase
data/glossary.json                  glossaire généré (ne pas éditer à la main)
data/pages_sources.json             liste des pages, générée par le script
sources/glossaire_source.json   source unique : une entrée par page (définition, indicateurs,
                                 champs de tableau personnalisé), à éditer directement
scripts/build_glossary.py       génère data/ depuis sources/glossaire_source.json
assets/, fonts/                 identité visuelle RPE
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

## Modifier le contenu

Tout part d'un seul fichier : `sources/glossaire_source.json`. Structure :

```json
{
  "pages": [
    {
      "page": "Nom de la page",
      "definition_page": "...",
      "indicateurs": [
        {"libelle": "...", "definition": "...", "kpi": true}
      ],
      "champs_tableau": [
        {"type": "Dimension", "categorie": "...", "champ": "...", "niveau_hierarchique": null,
         "definition": "...", "modalites": ["...", "..."], "noms_techniques": ["..."], "sources": ["..."]}
      ]
    }
  ]
}
```

- `definition`, `modalites`, `noms_techniques`, `sources` sont facultatifs sur chaque indicateur/champ (laisser vide si inconnu).
- Un champ Dimension au même nom sur plusieurs pages (ex. "Territoire") est automatiquement fusionné en une seule fiche listant toutes ses pages.
- `niveau_hierarchique` renseigné plusieurs fois pour un même champ crée automatiquement une variable hiérarchique (niveaux navigables).

Après modification, régénérer :

```
python3 scripts/build_glossary.py
```

(depuis la racine du dépôt). Régénère `data/glossary.json` et `data/pages_sources.json`.

## Notions clés

- **Définition de page** (`source: "page"`) : une fiche par page. Catégorie à part, filtrable via "📘 Définitions de page", sans type Dimension/Mesure. Son détail liste automatiquement tous les indicateurs et tous les champs de tableaux personnalisés de cette page.
- **Indicateur de page** (`source: "indicateur"`) vs **champ de tableau personnalisé** (`source: "champ_tableau"`) : deux natures de fiches distinctes, jamais fusionnées même à libellé identique ; tags visuels différents (📄 vs 🗂️). Filtrable via "Nature de fiche".
- **KPI** (`kpi: true`) : indicateur clé mis en avant sur une page, identifié par 🗝️.
- **Catégorie** : regroupement fonctionnel d'un champ de tableau personnalisé (ex. "3. Public") - à ne pas confondre avec le **groupe** (données aux définitions proches, ex. "Accès à l'emploi", consolidées en une fiche).
- **Variable hiérarchique** : mêmes données à différents niveaux d'agrégation (`hierarchie: {nom, niveau}`, niveau 0 = plus détaillé), avec ex æquo possibles.
- **Compteurs** (`compteurs/{id}`) : nombre de demandes en attente par fiche. En cas d'incohérence, bouton "🔄 Réparer les compteurs" dans `admin.html`.
- **Propositions** : `ajout`, `modification`, `suppression`, `groupe_lot`, `hierarchie_lot`, `groupe_suppression`, `hierarchie_suppression`. Chacune est visible et éditable par l'admin avant validation, qui écrit dans `glossaire_ajouts`/`glossaire_overrides`.

## Purge Firebase après une refonte du contenu

Chaque fois que `data/glossary.json` change de modèle de données ou d'identifiants (ex. refonte du contenu, changement de schéma), les documents déjà présents dans Firestore (`glossaire_overrides`, `glossaire_ajouts`, `compteurs`, `propositions`) référencent d'anciens id devenus incohérents avec le nouveau glossaire.

Bouton **"🧹 Purger la base"** dans `admin.html` (barre d'outils, à côté de "Réparer les compteurs") : supprime tous les documents de ces 4 collections après confirmation (affiche d'abord le nombre de documents concernés). Le glossaire de base (`data/glossary.json`) n'est jamais touché. À utiliser après chaque refonte de contenu, avant de laisser de nouvelles contributions arriver.

## Vue "Tout"

Un bouton "Tout" apparaît à côté de la barre alphabétique : il affiche l'ensemble du glossaire (filtré par type/nature/page si un filtre est actif), organisé en blocs par lettre, plutôt que de devoir cliquer lettre par lettre.

## Notes

- Aucune donnée personnelle stockée côté client : l'email des contributeurs n'est lisible que par l'admin (règles Firestore).
- `data/glossary.json` n'est pas rechargé avec anti-cache : après régénération, un Ctrl+Shift+R peut être nécessaire pour voir la nouvelle version.
