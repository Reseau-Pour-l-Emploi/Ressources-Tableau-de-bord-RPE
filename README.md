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

1. Créer un projet sur https://console.firebase.google.com
2. Activer **Firestore Database** (mode production).
3. Activer **Authentication** > méthodes de connexion : **Anonyme** (pour les contributeurs) et **Email/mot de passe** (pour l'admin).
4. Dans Authentication > Utilisateurs, créer manuellement le compte administrateur (email + mot de passe).
5. Copier la config SDK (Paramètres du projet > Vos applications > Web) dans `firebase-config.js`, et renseigner ce même email dans `ADMIN_EMAILS`.
6. Mettre à jour l'email dans `firestore.rules` (fonction `isAdmin`) pour qu'il corresponde à `ADMIN_EMAILS`.
7. Déployer les règles : `firebase deploy --only firestore:rules` (nécessite `firebase-tools` et `firebase init` préalable), ou coller le contenu de `firestore.rules` dans Firestore > Règles depuis la console.

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

## Notes

- Aucune donnée personnelle n'est stockée côté client : l'email du contributeur n'est lisible que par l'administrateur (règles Firestore).
- Le champ "Période de calcul" des mesures est laissé vide à la génération : à compléter progressivement via les contributions.
