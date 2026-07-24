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

## Notes

- Aucune donnée personnelle n'est stockée côté client : l'email du contributeur n'est lisible que par l'administrateur (règles Firestore).
- Le champ "Période de calcul" des mesures est laissé vide à la génération : à compléter progressivement via les contributions.
