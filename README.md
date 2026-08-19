# Ressources Tableau de bord RPE

Site à trois pages : **Accueil** (actualités, agenda, webinaires, ressources, contact - éditable sans code), **Glossaire** (indicateurs et champs du tableau de bord RPE, contributif) et un bouton d'accès direct au Tableau de Bord RPE.

## Structure

```
index.html                     Accueil (contenu éditable via l'admin, stocké dans Firestore)
glossaire.html                  Glossaire public (ex-index.html)
admin.html                      back-office : propositions, édition directe, contenu du site, export/import
firebase-config.js              config Firebase + email(s) admin (A COMPLETER)
firestore.rules                 règles de sécurité à publier dans Firebase
data/glossary.json                  glossaire généré (ne pas éditer à la main)
data/pages_sources.json             liste des pages, générée par le script
sources/glossaire_source.json   source unique du glossaire : une entrée par page, à éditer directement
scripts/build_glossary.py       génère data/ depuis sources/glossaire_source.json
assets/, fonts/                 identité visuelle RPE
```

## Page d'accueil : contenu éditable sans code

Tout le contenu de `index.html` (texte d'intro, vidéos, textes réglementaires, agenda, actualités, newsletters, webinaires, ressources complémentaires, contact, liens de pied de page, et l'URL du bouton "Accéder au Tableau de Bord RPE" utilisée sur toutes les pages) est stocké dans un seul document Firestore `site_content/homepage` et édité depuis l'onglet **"📄 Contenu du site"** de `admin.html` - ajout/suppression/modification d'éléments via des formulaires répétables, sans toucher au code. Si ce document n'existe pas encore (première utilisation), la page affiche un contenu par défaut identique à celui fourni à la création du site ; la première sauvegarde depuis l'admin crée le document.

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

- **Pages** : ne sont pas des fiches du glossaire, uniquement un filtre. Sélectionner une page dans le filtre affiche sa définition sous l'en-tête ; l'étiquette d'une page révèle cette même définition au survol (infobulle), partout où elle apparaît. Ces définitions sont exportées dans `data/pages_sources.json` (`page_definitions`).
- **Mesure/Dimension** : cette étiquette n'apparaît que sur les fiches "champ de tableau personnalisé" - jamais sur les indicateurs de page.
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

## Affichage organisé par nature, repliable

Toute liste de résultats (lettre, page, "Tout", recherche) est désormais organisée en 3 blocs repliables dans cet ordre : 📘 Définitions de page, 📄 Indicateurs de page, 🗂️ Champs des tableaux personnalisés - séparés par une ligne, chacun affichant son nombre de fiches. En mode "Tout", chaque bloc est lui-même sous-organisé par lettre. Les compteurs sous les lettres de la barre A-Z reflètent les filtres type/nature actifs (recalculés à chaque changement de filtre).

## Tags vs éléments de définition

Tags visibles à côté d'un libellé : Mesure/Dimension, Indicateur de page/Champ tableau, 🗝️ KPI, Groupe - X variables, X niveaux hiérarchiques. La **catégorie** d'un champ de tableau personnalisé (ex. "3. Public") n'est pas un tag : elle apparaît en italique sous le titre dans la liste, et dans une section "Catégorie" dédiée du détail - c'est une information de définition, pas un badge de filtrage.

## Indicateurs Accueil fusionnés

Quand un indicateur de la page "Accueil" porte exactement le même libellé qu'un indicateur déjà présent sur sa page dédiée, `build_glossary.py` ne crée pas de seconde fiche : il rattache "Accueil" à la liste des pages de la fiche existante (et propage le KPI si besoin). Aucune définition n'est donc dupliquée pour ces cas.

## Mode édition directe (admin)

Bouton **"✏️ Mode édition"** dans `admin.html` : bascule vers un onglet permettant de chercher n'importe quelle fiche publiée par libellé, de la modifier (tous les champs, y compris groupe/hiérarchie/pages/sources) et d'enregistrer **directement** dans `glossaire_overrides`/`glossaire_ajouts`, sans passer par une proposition ni attendre de validation. Un bouton "🗑️ Supprimer cette fiche" permet aussi la suppression immédiate. Le bouton "+ Nouvelle fiche" ouvre un formulaire vierge pour créer une fiche de toutes pièces (écrite dans `glossaire_ajouts`).

À utiliser pour les corrections rapides côté admin ; le circuit normal (proposition → validation) reste recommandé pour les contributions d'utilisateurs.

## Indicateurs homonymes fusionnés (hors Accueil)

Quand un indicateur porte exactement le même libellé sur plusieurs pages **non-Accueil**, une seule fiche est créée, avec une définition propre à chaque contexte (`definitions_par_page: {contexte: définition}`). Le détail public affiche alors un tableau "Page / Définition" au lieu d'un simple texte.

Cette fusion fonctionne aussi quand le même libellé se répète **plusieurs fois sur une même page** (ex. les catégories de ventilation "BRSA", "Bénéficiaires de l'obligation d'emploi"... citées une fois pour "Accès à l'emploi" et une fois pour "Présence en emploi" sur la page "Accès / Présence en emploi") : `build_glossary.py` détecte ces sections en repérant, dans l'ordre du fichier source, le dernier indicateur "principal" (non catégorie de ventilation) qui précède chaque catégorie, et l'utilise comme contexte - uniquement quand le libellé se répète réellement sur cette page (sinon le nom de la page seul suffit). La liste des catégories de ventilation reconnues (`BREAKDOWN_LABELS_RAW`) est en tête du script.

## Mode édition (ergonomie)

Le formulaire du mode édition admin reprend la mise en page de la fiche de consultation publique (titre, badges Type/Nature/KPI, sections Définition/Modalités/Cas d'usage/Pages/Sources/Groupe/Hiérarchie) mais chaque zone est directement modifiable en place, avec un bouton Enregistrer et un bouton Supprimer.

## Libellés proches fusionnés

Certains libellés désignent la même donnée sous une forme différente (ex. "BRSA" et "Bénéficiaires du RSA"). Une table `LABEL_ALIASES` en tête de `build_glossary.py` les fait fusionner sous un nom canonique commun ("Bénéficiaires du RSA / BRSA"), avec une définition par contexte comme les autres homonymes. À compléter si d'autres rapprochements de ce type sont identifiés.

## Groupes et hiérarchies : uniquement pour les champs

`groupe` et `hierarchie` ne sont désormais assignés qu'aux fiches `source: "champ_tableau"` - jamais aux indicateurs de page (qui restent des fiches individuelles, dédupliquées par libellé/contexte comme décrit ci-dessus, mais jamais consolidées derrière une fiche "Groupe"). Les mesures de tableaux personnalisés homonymes entre pages sont elles aussi fusionnées en une seule fiche avec une définition par page (même mécanisme que pour les indicateurs).

**KPI et groupe** : si un membre d'un groupe est KPI (`kpi: true`), le groupe entier est marqué KPI (icône 🗝️ affichée sur la fiche groupe).

## Tags renommés et réordonnés

Ordre d'affichage des étiquettes à côté d'un intitulé : **Indicateur/Champ** → **Mesure/Dimension** (uniquement si Champ) → **🗝️ KPI** (le cas échéant) → **Groupe - X variables** → **X niveaux hiérarchiques**.

- "Champ tableau perso." → **"Champ"**, infobulle "Champ présent dans un tableau personnalisé".
- "Indicateur de page" → **"Indicateur"**, infobulle "Indicateur présent sur une page de synthèse".
- KPI : icône 🗝️ seule (plus de texte), infobulle "Indicateur stratégique défini par le Comité National pour l'Emploi".

## Groupes : jamais de mélange indicateur/champ

Un groupe (ex. "Accès à l'emploi") peut exister à la fois côté indicateurs et côté champs de tableaux, mais ce sont deux fiches "Groupe" distinctes - jamais fusionnées entre elles. `build_glossary.py` assigne `groupe` à toute fiche correspondant à la règle, quelle que soit sa nature ; c'est `glossaire.html` (`buildDisplayItems`) qui consolide les membres par clé `(groupe, source)`, garantissant qu'un groupe ne mélange jamais indicateurs et champs.

## Familles de groupes reconnues

`GROUP_RULES` (en tête de `build_glossary.py`) : "Accès à l'emploi", "Présence en emploi", "Nombre d'accès à un emploi", "Nombre d'individus en emploi", "Délai moyen d'accès à l'emploi", "Inscrits depuis plus de X mois". Un groupe qui ne compterait qu'un seul membre après application des règles est automatiquement annulé (pas de groupe à un seul élément). À compléter si d'autres familles de libellés proches sont identifiées.

`CHAMP_LABEL_ALIASES` : variantes orthographiques d'un même champ de tableau personnalisé (ex. "Top 50 ans et +" / "Top 50 ans et plus"), fusionnées comme `LABEL_ALIASES` pour les indicateurs.

## Champs enrichis par leur indicateur homonyme

Un champ de tableau personnalisé sans définition (`""`) reprend automatiquement celle de l'indicateur portant exactement le même libellé, s'il en existe un. Ne remplace jamais une définition déjà renseignée. 18 champs concernés actuellement.

## Export Excel complet (public + admin)

Bouton **"📊 Exporter en Excel"** présent aussi bien sur le site public (`glossaire.html`, exporte le glossaire complet publié) que dans `admin.html`. Deux onglets :

- **Indicateurs** : ID, Libellé, KPI, Pages, Définition, Définitions par page (si différentes), Cas d'usage, Groupe, Période de calcul, Sources, Noms techniques.
- **Champs** : ID, Libellé, Type, Catégorie, Pages, Définition, Définitions par page (si différentes), Modalités, Cas d'usage, Groupe, Hiérarchie - Nom, Hiérarchie - Niveau, Période de calcul, Sources, Noms techniques.

La colonne **ID** est l'identifiant technique de la fiche : c'est elle qui permet la réimportation (voir ci-dessous).

## Import Excel : mise à jour globale (admin)

Bouton **"📥 Importer un Excel"** dans `admin.html` : accepte un fichier au même format que l'export (onglets "Indicateurs"/"Champs", mêmes colonnes). Pour chaque ligne :
- **ID renseigné et existant** → met à jour la fiche correspondante (écrit dans `glossaire_overrides`).
- **ID vide ou inconnu** → crée une nouvelle fiche (écrit dans `glossaire_ajouts`), avec un id dérivé du libellé.

Une confirmation (nombre de lignes par onglet) est affichée avant toute écriture. Permet de corriger en masse le glossaire dans Excel (définitions, groupes, hiérarchie...) puis de réimporter en un clic, sans repasser par le mode édition fiche par fiche.

## Page d'accueil : mise en page

Style sobre (fonds clairs, bordures fines, radius modestes, peu d'ombres). Zone de contenu élargie (1360px), deux colonnes : contenu principal (actualités en bandeaux discrets, **Le Kiosque** - webinaires/newsletters/autres événements fusionnés en une seule grille de vignettes triée automatiquement du plus récent au plus ancien, limitée à 5 puis "Afficher plus", ressources en **véritable carrousel** avec flèches précédent/suivant) et colonne latérale flottante (agenda façon calendrier avec pastille jour/mois, bloc contact). Site responsive (mobile/tablette) sur les trois pages.

Le bandeau d'introduction accepte du HTML simple (paragraphes, listes, gras) pour un texte structuré.

**Agenda et disparition automatique** : un événement d'agenda dont la date est dépassée disparaît du calendrier le lendemain (J+1) - géré côté navigateur à l'affichage, aucune action admin nécessaire.

**Le Kiosque** n'affiche que les événements déjà passés (ou sans date) ; un événement à venir doit être saisi dans l'**Agenda**, pas dans le Kiosque - il y apparaîtra automatiquement une fois sa date passée si vous le dupliquez aussi côté Kiosque, ou ajoutez-le directement au Kiosque avec sa date : il restera invisible tant que la date n'est pas atteinte.

## Abonnement newsletter

Bouton "S'abonner à la newsletter" / "Se désabonner" sur la page d'accueil (dans le bloc Le Kiosque) : recueille un email, écrit dans la collection Firestore `newsletter_subscribers` (lecture réservée à l'admin). Dans l'admin (onglet 🏠 Accueil) : export de la liste en Excel, et import d'une liste d'emails (colonne "Email") pour ajouter/mettre à jour des abonnés en masse.

## Console admin : Glossaire vs Accueil

La barre d'outils admin distingue deux groupes d'onglets : **📚 Glossaire** (Propositions en attente / Mode édition) et **🏠 Accueil** (Contenu du site + Abonnés newsletter). Dans "Contenu du site", chaque bloc (agenda, actualités, Le Kiosque, ressources, liens de pied de page) affiche les **éléments existants pré-remplis** (pas seulement un formulaire d'ajout) : modifiez-les directement, supprimez-en avec "🗑️ Supprimer", ou ajoutez-en avec "+ Ajouter". Le contenu par défaut chargé dans cet éditeur avant toute sauvegarde est strictement identique à celui affiché publiquement (`DEFAULT_SITE_CONTENT` dans `admin.html` = `DEFAULT_CONTENT` dans `index.html`) : à maintenir synchronisé si l'un des deux est modifié directement dans le code.

## Score EcoIndex (éco-conception)

Badge lettre (A à G, fond vert) affiché en bas à droite du pied de page sur `index.html` et `glossaire.html`, lien vers le détail du résultat sur ecoindex.fr. Éditable sans code depuis l'admin (🏠 Accueil > Contenu du site > "Score EcoIndex"). Contrairement au RGAA, l'EcoIndex (GreenIT.fr) repose sur une formule publique et entièrement automatisable (nombre d'éléments DOM, poids de la page, nombre de requêtes) : à recalculer sur https://www.ecoindex.fr après toute évolution significative du site, et à mettre à jour ici avec le nouvel id de résultat.

## Notes

- Aucune donnée personnelle stockée côté client : l'email des contributeurs n'est lisible que par l'admin (règles Firestore).
- `data/glossary.json` n'est pas rechargé avec anti-cache : après régénération, un Ctrl+Shift+R peut être nécessaire pour voir la nouvelle version.
