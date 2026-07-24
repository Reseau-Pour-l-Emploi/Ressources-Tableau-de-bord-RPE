# Glossaire du tableau de bord RPE

Glossaire consultable (recherche + entrée alphabétique) des **dimensions** (variables d'analyse) et **mesures** (indicateurs) des 7 bases du tableau de bord RPE, avec contribution communautaire et modération admin.

## Structure du projet

```
index.html            page publique : recherche, A-Z, détail, formulaire de contribution
admin.html            back-office : connexion admin, validation/correction/suppression des propositions
firebase-config.js    config Firebase + liste des emails admin (A COMPLETER)
firestore.rules       règles de sécurité Firestore à déployer
data/glossary.json    glossaire de base (généré depuis le fichier Excel source, 201 entrées)
scripts/              scripts Python de génération de data/glossary.json
assets/, fonts/       identité visuelle RPE (ne pas modifier)
```

## Principe de fonctionnement

- `data/glossary.json` est le glossaire de référence, versionné dans le dépôt, régénérable à tout moment depuis le fichier Excel source (voir `scripts/`).
- Les contributions des utilisateurs passent par la collection Firestore `propositions` (statut `en_attente`), visible uniquement par l'administrateur.
- Une fois validée par l'admin, une proposition est écrite dans `glossaire_ajouts` (nouvelle entrée) ou `glossaire_overrides` (modification d'une entrée existante, fusionnée par-dessus l'entrée de base).
- `index.html` charge `glossary.json` + `glossaire_ajouts` + `glossaire_overrides` et fusionne le tout à l'affichage. Aucune réécriture du fichier JSON de base n'est nécessaire pour publier une contribution.

## Mise en place Firebase (une seule fois)

1. Aller sur https://console.firebase.google.com > **Ajouter un projet** (ex. nom "rpe-glossaire"), suivre l'assistant (Google Analytics facultatif, à désactiver si non souhaité).
2. Dans le menu de gauche : **Build > Firestore Database** > Créer une base > mode **production** > choisir une région (ex. `eur3`).
3. Dans le menu de gauche : **Build > Authentication** > Get started > onglet **Sign-in method** > activer :
   - **Anonyme** (permet aux visiteurs de proposer des ajouts/modifications sans créer de compte)
   - **Adresse e-mail/Mot de passe**
4. Toujours dans Authentication, onglet **Users** > **Add user** :
   - Email : choisir l'email administrateur (ex. `denis.gorce@francetravail.fr`, à adapter)
   - Mot de passe : **RPE_Gloss**
5. Dans **Paramètres du projet** (roue crantée) > **Vos applications** > **Ajouter une application** > icône `</>` (Web) > donner un nom (ex. "glossaire-web") > **Ne pas** cocher Firebase Hosting > copier l'objet `firebaseConfig` affiché.
6. Coller cet objet dans `firebase-config.js` (remplace les valeurs `A_COMPLETER`), et renseigner l'email choisi à l'étape 4 dans `ADMIN_EMAILS` du même fichier.
7. Dans `firestore.rules`, remplacer `denis.gorce@francetravail.fr` par ce même email (doit être identique dans les deux fichiers).
8. Déployer les règles : soit coller le contenu de `firestore.rules` dans Firestore Database > **Règles** (bouton Publier) depuis la console, soit via `firebase deploy --only firestore:rules` (nécessite `firebase-tools` et `firebase init` préalable).

Une fois ces 8 étapes faites : ouvrir `admin.html`, se connecter avec l'email choisi et le mot de passe **RPE_Gloss**. Ce mot de passe peut être changé ensuite depuis Authentication > Users dans la console Firebase.

## Déploiement GitHub Pages

1. Pousser ce dépôt sur GitHub (branche `main`).
2. Settings > Pages > déployer depuis `main` / racine.
3. Le site est servi sur `https://<utilisateur>.github.io/<depot>/`.

## Régénérer le glossaire de base

Si le fichier Excel de description des champs évolue :

```
cd scripts
python3 parse_glossary.py   # filtre les champs techniques, distingue dimensions/mesures
python3 build_glossary.py   # dédoublonne, fusionne, génère ../data/glossary.json
```

Règles appliquées par les scripts :
- Une mesure est reconnue par un nom technique commençant par `I5F`, `Y5S`, `X7F`, `X9F`, `X8F`, `Y1F` ou `A7S`.
- Les champs marqués "Champ technique" (ou sans libellé court) sont exclus du glossaire.
- Les mesures ne sont fusionnées que si elles partagent le même nom technique (deux mesures de bases différentes portant le même libellé, ex. "Accès à l'emploi à 1 mois" sur la base sortants de formation et sur la base ensemble des demandeurs, restent volontairement distinctes : ce sont deux indicateurs différents comparés l'un à l'autre dans les analyses).
- Les dimensions sont fusionnées par nom technique puis par libellé identique (variables d'analyse réellement partagées entre bases : sexe, territoire, tranche d'âge...).
- Après génération automatique, toute imprécision peut être corrigée directement dans l'application via le bouton "Proposer une modification" (c'est l'objet du glossaire contributif).

## Regroupement de données à plusieurs niveaux

Certaines familles de données (ex. "Catégorie juridique" niv1/niv2/niv3, "Accès à l'emploi" à 1/2/3.../12 mois, "Présence en emploi") sont regroupées en une seule entrée cliquable dans le glossaire public. Le regroupement est piloté par `GROUP_RULES` dans `scripts/build_glossary.py` (expression régulière sur le libellé -> nom de regroupement). Pour ajouter un regroupement, ajouter une ligne à `GROUP_RULES` puis relancer `build_glossary.py`.

## Suppression contributive

Un visiteur peut proposer la suppression d'une fiche depuis son détail ("Proposer la suppression de cette donnée"). La demande arrive dans `propositions` (type `suppression`). Une fois validée par l'admin, la fiche est marquée `supprime: true` dans `glossaire_overrides` et disparaît du glossaire public (elle n'est jamais effacée de `data/glossary.json`, donc réversible en supprimant ce champ dans Firestore si besoin).

## Demandes en attente visibles publiquement

Chaque proposition liée à une fiche existante (modification ou suppression) incrémente un compteur public dans la collection Firestore `compteurs/{id}` (juste un nombre, aucune donnée personnelle). Le badge "X demande(s) en attente" s'affiche sur la fiche concernée pour tous les visiteurs, et disparaît automatiquement (compteur décrémenté) dès que l'administrateur valide ou rejette la proposition. Nécessite un rechargement de la page pour se mettre à jour chez les autres visiteurs (pas de mise à jour temps réel).

## Lien de partage direct

Le bouton "Partager" de chaque fiche (ou regroupement) copie un lien du type `index.html#detail=<id>` (ou `#groupe=<nom>`) dans le presse-papiers. Ouvrir ce lien affiche directement le détail correspondant, sans étape intermédiaire.

## Optimisations de chargement

- Les 3 scripts Firebase (`firebase-app-compat.js`, `firebase-auth-compat.js`, `firebase-firestore-compat.js`) et `firebase-config.js` sont chargés en `defer` : le HTML/CSS s'affiche sans attendre leur téléchargement.
- Le script principal est exécuté au moment `DOMContentLoaded` (garanti après les scripts `defer`), pas de couplage strict à l'ordre des balises.
- Au chargement, `data/glossary.json` et les 3 lectures Firestore (`glossaire_overrides`, `glossaire_ajouts`, `compteurs`) partent **en parallèle** (`Promise.all`) au lieu d'être enchaînés un par un : le temps de chargement correspond au plus lent des 4 appels, pas à leur somme.
- La connexion anonyme Firebase n'est plus faite au chargement de la page (elle n'est pas nécessaire pour lire des données publiques) : elle n'est déclenchée que lorsque l'utilisateur envoie réellement une proposition.
- `data/glossary.json` n'est plus rechargé avec un paramètre anti-cache à chaque visite : le navigateur peut le mettre en cache normalement. Après une régénération du fichier (nouvel Excel), un rechargement forcé (Ctrl+Shift+R) peut être nécessaire pour voir la nouvelle version immédiatement.

## Groupe vs variable hiérarchique

Deux notions distinctes, à ne pas confondre :

- **Groupe** (`groupe`, texte libre) : rassemble des données aux **définitions proches** (ex. toutes les mesures "Accès à l'emploi"). Dans le glossaire public, ces données sont consolidées en une seule fiche cliquable qui liste ses membres. Piloté par `GROUP_RULES` dans `scripts/build_glossary.py`.
- **Variable hiérarchique** (`hierarchie: {sup_id, inf_id}`) : signale que la donnée existe à **d'autres niveaux d'agrégation d'un même référentiel connu** (ex. Catégorie juridique niv1/niv2/niv3). Chaque fiche reste visible séparément dans la liste, avec un badge "N niveaux hiérarchiques" ; son détail permet de naviguer vers le niveau supérieur/inférieur. Piloté par `HIER_CHAINS` dans `scripts/build_glossary.py` (liste de libellés, du plus détaillé au plus agrégé).

Les deux champs sont proposables par les contributeurs (formulaire public : champ texte pour le groupe, deux listes déroulantes pour la hiérarchie) et modifiables par l'admin (deux champs texte `hierarchie_sup_id` / `hierarchie_inf_id` contenant l'id de la fiche liée).

## Filtre par page et navigation par lettre

- Un filtre "Page" liste toutes les pages du tableau de bord référencées dans le glossaire ; cliquer sur une page dans le filtre ou sur le tag page d'une fiche affiche uniquement les données de cette page.
- La barre alphabétique est unique, toujours visible, occupe toute la largeur ; la lettre A est sélectionnée par défaut au chargement pour ne jamais afficher une page vide.

## Barre de recherche et alphabet ancrés

La zone recherche/filtres + barre alphabétique reste visible en haut de l'écran au défilement (`position: sticky`), juste sous l'en-tête.

## Email pré-rempli à la décision admin

Quand l'administrateur valide, corrige ou rejette une proposition, un lien `mailto:` pré-rempli s'ouvre automatiquement vers l'email du contributeur : objet "Modification du glossaire du tableau de bord RPE [validée|rejetée|modifiée] : [libellé]", corps de message standard. "Modifiée" s'affiche quand l'administrateur a changé au moins un champ par rapport à la proposition initiale avant de valider.

## Formulaire adaptatif selon le type

Dimension et mesure n'affichent pas les mêmes champs : "Modalités" seulement pour les dimensions, "Période de calcul" seulement pour les mesures. Comportement identique côté public (`index.html`) et admin (`admin.html`).

## Listes déroulantes Pages / Sources

Les champs "Page(s)" et "Source(s)" des formulaires (public et admin) sont des listes déroulantes multi-sélection, peuplées depuis `data/pages_sources.json` (généré par `scripts/build_glossary.py` à partir des dictionnaires `BASE_PAGES`/`BASE_SOURCES` : une seule source de vérité). Régénérer ce fichier avec les autres données via `python3 build_glossary.py`.

## Groupe affiché comme tag sur chaque fiche

Chaque fiche individuelle affiche, si elle appartient à un groupe, un tag orange "Groupe : [nom] · N champs" (N = nombre total de données de ce groupe). Cliquer dessus filtre la liste sur les autres membres du groupe (comme un filtre page). Il n'y a plus de fiche de regroupement séparée : chaque donnée reste consultable individuellement.

## Champ commentaire

Le formulaire de contribution se termine par un champ "Commentaire" libre et facultatif, transmis à l'administrateur (affiché dans `admin.html`) mais jamais publié tel quel dans le glossaire.

## Consolidation à l'affichage (groupe / hiérarchie)

Le glossaire n'affiche plus chaque membre d'un groupe ou chaque niveau d'une hiérarchie comme une fiche séparée dans la liste :

- **Groupe** : une seule fiche synthétique "Groupe · N variables" apparaît ; cliquer dessus liste tous les membres, chacun cliquable vers sa fiche complète.
- **Variable hiérarchique** : seul le niveau **le plus détaillé** de la chaîne (celui sans `inf_id`) apparaît dans la liste ; son détail permet de naviguer vers les niveaux plus agrégés.

**Recherche** : si le mot-clé correspond à un membre masqué (membre de groupe, ou niveau hiérarchique non affiché), c'est le représentant visible (la fiche groupe, ou le niveau le plus détaillé de la chaîne) qui remonte dans les résultats - jamais une fiche autrement invisible.

Les liens de partage directs (`#detail=<id>`) continuent de fonctionner vers n'importe quel membre/niveau, même masqué de la liste principale.

## Icône de partage

Le bouton "Partager" (liste, détail, groupe) est une icône (pas de texte), avec une infobulle "Partager le lien vers cette définition".

## Choix exclusif groupe / hiérarchie, avec souffleur

Le formulaire (public et admin) impose de choisir **soit** un groupe **soit** une hiérarchie pour une donnée, jamais les deux à la fois (liste déroulante "Aucun / Groupe / Hiérarchie"). Chacun des deux a désormais un **nom** :

- Groupe : simple nom libre (ex. "Accès à l'emploi").
- Hiérarchie : nom du référentiel (ex. "Catégorie juridique"), stocké dans `hierarchie.nom` en plus de `sup_id`/`inf_id`.

Les deux champs sont associés à un **souffleur** (`<datalist>`) qui suggère les noms de groupes/hiérarchies déjà utilisés dans le glossaire, pour encourager la réutilisation plutôt que la création de doublons.

## Définition en lot d'un groupe ou d'une hiérarchie

Bouton "Définir un groupe ou une hiérarchie" (bandeau de contribution) : plutôt que d'ouvrir chaque fiche une par une, l'utilisateur choisit un nom (groupe ou hiérarchie), puis coche directement tous les champs concernés dans une liste filtrable. Pour une hiérarchie, chaque niveau (du plus agrégé en haut au plus détaillé en bas) a sa propre liste de champs à cocher - plusieurs champs cochés sur un même niveau = ex æquo. Si le nom saisi existe déjà, les champs/niveaux déjà assignés se pré-cochent (ajout à l'existant, pas de perte).

Ces demandes arrivent comme des propositions de type `groupe_lot` / `hierarchie_lot`, visibles et modifiables par l'admin avant validation (mêmes sélecteurs de champs côté `admin.html`), qui écrit alors en une fois dans `glossaire_overrides` pour chaque champ concerné.

Le modèle de donnée pour la hiérarchie est `hierarchie: {nom, niveau}` (niveau 0 = le plus détaillé, les nombres supérieurs sont plus agrégés) : deux champs peuvent partager le même niveau (ex æquo), contrairement à un modèle par pointeurs qui l'aurait interdit.

## Mode d'emploi repliable

En haut de la page publique, un bloc "📖 Mode d'emploi" (`<details>`, ouvert par défaut, repliable) résume dimensions/mesures, groupe, variable hiérarchique, comportement de la recherche, partage et contribution - avec les mêmes couleurs que les badges utilisés dans la liste.

## Diagnostic des erreurs à la création d'un groupe/d'une hiérarchie

Si la création échoue avec un message "Envoi refusé par le serveur (règles Firestore)..." : c'est presque toujours parce que `firestore.rules` publié sur la console Firebase est une version antérieure qui n'autorise pas encore les types `groupe_lot`/`hierarchie_lot`. Republier le contenu à jour de `firestore.rules` (Firestore Database > Règles > coller > Publier) résout le problème. Le formulaire ne ferme plus la fenêtre en cas d'erreur (avant, il se refermait comme en cas de succès, masquant l'échec) : le message d'erreur reste visible et les champs saisis sont conservés pour réessayer.

## Modifier un groupe ou une hiérarchie existant(e)

Le formulaire "Définir un groupe ou une hiérarchie" propose désormais une liste déroulante ("Groupe existant à modifier" / "Hiérarchie existante à modifier") en plus de la saisie libre + bouton "Charger" : sélectionner un nom existant précharge automatiquement ses champs (ou niveaux) déjà assignés, cochés dans le sélecteur, pour les compléter ou les retirer avant de resoumettre.

## Supprimer entièrement un groupe ou une hiérarchie

Une fois un groupe ou une hiérarchie existant(e) chargé(e) dans le formulaire en lot (via le sélecteur ou "Charger"), un bouton rouge "🗑️ Supprimer entièrement ce groupe/cette hiérarchie" apparaît. Il envoie une proposition `groupe_suppression` / `hierarchie_suppression` : une fois validée par l'admin, le rattachement (`groupe` ou `hierarchie`) est retiré de tous les champs concernés (mis à `null` dans `glossaire_overrides`), sans jamais supprimer les champs eux-mêmes.

## Contrainte Firestore : pas de tableaux imbriqués

Firestore interdit un tableau directement contenu dans un autre tableau. Le champ `niveaux` d'une proposition `hierarchie_lot` est donc stocké comme un tableau d'objets `{ids: [...]}` (un objet par niveau) plutôt qu'un tableau de tableaux. Si un nouveau champ de ce type est ajouté un jour, garder ce principe en tête (envelopper tout tableau imbriqué dans un objet).

## Notes

- Aucune donnée personnelle n'est stockée côté client : l'email du contributeur n'est lisible que par l'administrateur (règles Firestore).
- Le champ "Période de calcul" des mesures est laissé vide à la génération : à compléter progressivement via les contributions.
