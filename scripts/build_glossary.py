# -*- coding: utf-8 -*-
import json, re, unicodedata
from collections import OrderedDict

raw = json.load(open('raw_entries.json'))

BASE_PAGES = {
    'RPE_DESCRIPTIONPUBLICS': ['Description des publics', 'Analyse par public'],
    'RPE_TAETPED': ['Accès / Présence en emploi', 'Analyse par public'],
    'RPE_SATISACO': ['Satisfaction DE', 'Analyse par public'],
    'RPE_FPRIO': ['Entrants en formation', 'Analyse par public'],
    'RPE_FTAE': ['Sortants de formation', 'Analyse par public'],
    'RPE_ENT': ['Taux de recours', 'Analyse par filière'],
    'RPE_TPODPO': ['Taux / Délai de pourvoi', 'Analyse par filière'],
}
BASE_SOURCES = {
    'RPE_DESCRIPTIONPUBLICS': ['Statistiques du Marché du Travail (STMT) - DARES / France Travail', 'Diagnostic Socio-Professionnel (DSP) - Opérateurs du RPE', 'Autres données France Travail'],
    'RPE_TAETPED': ['Statistiques du Marché du Travail (STMT) - DARES / France Travail', 'Déclaration Sociale Nominative (DSN) - GIP-MDS', 'Autres données France Travail'],
    'RPE_SATISACO': ['Enquête IPSOS', 'Autres données France Travail'],
    'RPE_FPRIO': ["Attestations d'Entrée en Stage (AES) - France Travail", 'Compte personnel de formation (CPF) - Caisse des Dépôts'],
    'RPE_FTAE': ["Attestations d'Entrée en Stage (AES) - France Travail", 'Compte personnel de formation (CPF) - Caisse des Dépôts', 'Déclaration Sociale Nominative (DSN) - GIP-MDS', 'Autres données France Travail'],
    'RPE_ENT': ['Déclaration Préalable à l\'Embauche (DPAE) - Urssaf / MSA', 'Déclaration Sociale Nominative (DSN) - GIP-MDS', "Offres d'emploi France Travail", 'Autres données France Travail'],
    'RPE_TPODPO': ["Offres d'emploi France Travail", 'Autres données France Travail'],
}
BASE_LABELS = {
    'RPE_DESCRIPTIONPUBLICS': 'Description des publics',
    'RPE_TAETPED': 'Accès / Présence en emploi',
    'RPE_SATISACO': 'Satisfaction DE',
    'RPE_FPRIO': 'Entrants en formation',
    'RPE_FTAE': 'Sortants de formation',
    'RPE_ENT': 'Taux de recours',
    'RPE_TPODPO': 'Taux / Délai de pourvoi',
}

def norm_key(s):
    s = (s or '').lower().strip()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s

def modalites_from_detail(detail):
    if not detail:
        return None
    parts = [p.strip() for p in detail.split('\n') if p.strip()]
    if len(parts) < 2:
        return None
    return parts

def rules_by_value(regle):
    """Parse 'Valeur : condition' lines into dict valeur->condition (best effort)."""
    if not regle:
        return {}
    out = OrderedDict()
    for line in regle.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^(.*?)\s*:\s*(.+)$', line)
        if m:
            val, cond = m.group(1).strip(), m.group(2).strip()
            out[val] = cond
    return out

def simplify_condition(cond):
    if not cond:
        return cond
    c = cond
    c = re.sub(r"\bin\s*\(", 'parmi (', c, flags=re.I)
    c = c.replace('<>', 'différent de').replace('>=', 'supérieur ou égal à').replace('<=', 'inférieur ou égal à')
    c = re.sub(r'(?<![<>=])=(?!=)', ' égal à ', c)
    c = c.replace(' et ', ' et ').replace('Else', 'dans tous les autres cas')
    return c.strip()

GEO_KEYS = {'C_COMMUNE_ID','C_LBLCOMMUNE','C_TERRITOIRE_ID','C_LBLTERRITOIRE','C_DEPARTEMENT_ID','C_LBLDEPARTEMENT','C_REGION_ID','C_LBLREGION'}

def auto_definition(tech, libelle, mesure, modalites, regle, detail, base):
    t = tech.upper()
    if mesure:
        m = re.match(r"^Accès à l'emploi(?: durable)? à (\d+) mois$", libelle)
        if m:
            n = m.group(1)
            durable = 'durable ' if 'durable' in libelle.lower() else ''
            return ("Nombre de personnes ayant accédé à un emploi %s%s mois après la sortie observée (sortie de "
                    "formation ou sortie des listes selon la base), utilisé comme numérateur du taux d'accès à "
                    "l'emploi à %s mois." % (durable, n, n))
        m = re.match(r"^Présence en emploi(?: durable)? à (\d+) mois$", libelle)
        if m:
            n = m.group(1)
            durable = 'durable ' if 'durable' in libelle.lower() else ''
            return ("Nombre de personnes en emploi %sau cours du %se mois suivant la sortie observée, utilisé comme "
                    "numérateur du taux de présence en emploi à %s mois." % (durable, n, n))
        if libelle.startswith('Individus sortis de formation'):
            return ("Effectif total des sortants de formation observés, utilisé comme dénominateur des taux "
                    "d'accès et de présence en emploi des sortants de formation.")
        if 'Postes pourvus' in libelle or 'Postes sortis' in libelle:
            return "Décompte d'offres d'emploi (postes pourvus ou clôturés), utilisé pour calculer le taux ou le délai de pourvoi des offres."
        if 'Délai de pourvoi' in libelle:
            return "Somme des délais (en jours) entre le dépôt et la clôture des offres, utilisée pour calculer le délai moyen de pourvoi."
        if libelle.startswith('Etablissement'):
            return "Décompte d'établissements, utilisé comme numérateur ou dénominateur du taux de recours à France Travail."
        if re.match(r"^Offre |^Contrat aidé|^Promotion de profils|^Préparation opérationnelle|^DPAE ", libelle):
            return "Décompte du nombre d'établissements ayant eu recours au service ou dispositif : %s." % libelle
        return ("Mesure chiffrée du tableau de bord RPE utilisée dans le calcul d'un indicateur (numérateur, "
                "dénominateur ou décompte) autour de : %s." % libelle.rstrip('.'))
    if t in GEO_KEYS or t.startswith('C_COMMUNE') or t.startswith('C_TERRITOIRE') or t.startswith('C_DEPARTEMENT') or t.startswith('C_REGION'):
        return "Rattachement géographique de la donnée (commune, unité territoriale/CLPE, département ou région)."
    if t == 'DATMAJ':
        return "Date de dernière mise à jour de la base de données."
    if t.startswith('D_'):
        return "Date de référence utilisée pour situer l'observation dans le temps."
    low = libelle.lower()
    if low.startswith('top ') or (modalites and set(m.strip().lower() for m in modalites) <= {'oui','non'}):
        sujet = libelle[4:].strip() if low.startswith('top ') else libelle
        return "Indicateur Oui/Non signalant si la situation suivante s'applique : %s." % sujet
    if modalites:
        return ("Variable catégorielle qui classe la donnée selon les modalités suivantes : %s." %
                ', '.join(modalites[:6]) + ('…' if len(modalites) > 6 else '.'))
    return "Variable d'analyse (dimension) du tableau de bord RPE : %s." % libelle

# Manually curated, higher-quality definitions for key business concepts (overrides auto)
CURATED_DEFS = {
    'sexe': "Sexe de la personne : Femme ou Homme.",
    'tranche-d-age': "Regroupement de l'âge de la personne par tranches, utilisé pour les analyses par public.",
    'tranche-d-age-analyse-par-public': "Regroupement de l'âge en 3 tranches (Moins de 26 ans / De 26 à 49 ans / 50 ans et plus), spécifique aux pages 'Analyse par public'.",
    'niveau-de-formation': "Niveau de formation ou de diplôme le plus élevé atteint, regroupé en grandes catégories (du 'Peu ou pas diplômé' à 'BAC+3 et plus').",
    'duree-de-formation': "Durée prévisionnelle de la formation suivie, regroupée par tranches horaires.",
    'organisme-accompagnateur': "Structure qui assure l'accompagnement du demandeur d'emploi (France Travail, Mission locale, Cap emploi, Conseil départemental, ou sans référent).",
    'referent-d-accompagnement': "Structure qui assure l'accompagnement du demandeur d'emploi (France Travail, Mission locale, Cap emploi, Conseil départemental, ou sans référent).",
    'type-parcours': "Type de parcours d'accompagnement proposé au demandeur d'emploi : social, socio-professionnel, professionnel ou indéterminé.",
    'top-qpv': "Indique si la personne réside dans un Quartier prioritaire de la politique de la ville (QPV).",
    'top-zfrr': "Indique si la commune de résidence est classée en Zone France Ruralités Revitalisation (ZFRR), zone rurale bénéficiant d'un soutien renforcé.",
    'top-rsa': 'Indique si la personne est bénéficiaire du Revenu de solidarité active (RSA), au titre du droit réel et payable.',
    'top-brsa': 'Indique si la personne est bénéficiaire du Revenu de solidarité active (RSA).',
    'top-boe': "Indique si la personne relève de l'obligation d'emploi des travailleurs handicapés (OETH/BOE).",
    'top-cadre': "Indique si la personne recherche un poste de niveau cadre.",
    'top-infrabac': "Indique si la personne a un niveau de formation inférieur au BAC.",
    'top-55-ans-et': "Indique si la personne est âgée de 55 ans ou plus.",
    'top-50-ans-et': "Indique si la personne est âgée de 50 ans ou plus.",
    'top-26-ans-jusqu-a-bac-2': "Indique si la personne a moins de 26 ans et un niveau de formation jusqu'à BAC+2.",
    'top-public-prioritaire': "Indique si la personne appartient à un public prioritaire des politiques de l'emploi (jeunes, seniors, BRSA, BOE, infra BAC...).",
    'etrangers-primo-arrivants': "Situation de la personne au regard du Contrat d'intégration républicaine (CIR) signé par les étrangers primo-arrivants : non concerné, CIR de moins d'un an, ou CIR entre 1 et 5 ans.",
    'top-epa': "Indique si la personne est un étranger primo-arrivant (EPA), c'est-à-dire récemment installé en France dans le cadre de son parcours d'intégration.",
    'top-diplome-obtenu': "Indique si la personne est allée au bout de sa formation et a obtenu le diplôme ou titre visé.",
    'top-abandon': "Indique si la personne a abandonné sa formation avant son terme.",
    'categorie-stat': "Catégorie statistique du demandeur d'emploi (A, B, C, D, E, F ou G), selon sa disponibilité et son activité.",
    'type-activite-reduite': "Volume d'activité réduite (heures travaillées dans le mois) déclaré par le demandeur d'emploi.",
    'anciennete': "Ancienneté d'inscription du demandeur d'emploi sur les listes, regroupée par tranches.",
    'objectif-de-formation': "Finalité recherchée par la formation suivie (qualification, perfectionnement, remise à niveau, création d'entreprise...).",
    'domaine-de-formation': "Grand domaine thématique de la formation suivie.",
    'formation-a-distance': "Modalité pédagogique de la formation : en centre, à distance, ou mixte.",
    'top-metier-en-tension': "Indique si le métier recherché ou visé fait partie des métiers en tension (difficultés de recrutement identifiées).",
    'top-certifiante': "Indique si la formation suivie est certifiante (délivre un diplôme, titre ou certification reconnue).",
    'top-cpf-autonome': "Indique si la formation a été financée par le Compte personnel de formation (CPF) mobilisé de manière autonome par la personne.",
    'secteur': "Secteur d'activité de l'établissement, en 4 grandes familles (Agriculture, Industrie, BTP, Tertiaire).",
    'taille-de-l-etablissement': "Tranche d'effectif salarié de l'établissement.",
    'type-d-etablissement': "Statut de l'établissement : public ou privé.",
    'categorie-juridique-niv2': "Catégorie juridique de l'établissement, niveau intermédiaire (ex. société commerciale, entrepreneur individuel...).",
    'categorie-juridique-niv3': "Catégorie juridique de l'établissement, niveau agrégé le plus lisible (ex. société commerciale, personne morale...).",
    'top-siege-social': "Indique si l'établissement est le siège social de l'entreprise.",
    'top-structure-iae': "Indique si l'établissement est une structure de l'Insertion par l'activité économique (IAE).",
    'top-entreprise-adaptee': "Indique si l'établissement est une entreprise adaptée, employant des travailleurs en situation de handicap.",
    'top-organisme-de-formation': "Indique si l'établissement est un organisme de formation.",
    'type-de-l-offre': "Nature du contrat proposé dans l'offre d'emploi (emploi durable, temporaire, occasionnel ou non salarié).",
    'type-recrutement': "Modalité d'accompagnement de France Travail sur l'offre : dépôt autonome, avec appui d'un conseiller, ou service délivré par un conseiller.",
    'qualification': "Niveau de qualification du poste proposé dans l'offre d'emploi.",
    'delai-d-acces': "Nombre de mois écoulés entre la sortie (de formation ou de la liste) et le premier accès à l'emploi constaté.",
    'nombre-de-contraintes-dimension': "Nombre de freins périphériques à l'emploi identifiés lors du diagnostic (mobilité, santé, logement, savoirs de base...).",
    'ancien-du-diagnostic': "Ancienneté du diagnostic socio-professionnel réalisé, en mois.",
    'metier-recherche': "Métier recherché par le demandeur d'emploi (nomenclature ROME).",
    'domaine-professionnel': "Domaine professionnel du métier recherché (nomenclature ROME).",
    'grand-domaine-pro': "Grand domaine professionnel du métier recherché (nomenclature ROME, niveau le plus agrégé).",
}

def make_cas_usage(key, libelle):
    if key in ('duree-de-formation',):
        return ("La durée de la formation est inséparable du coût de la formation. Ainsi, on peut être plus exigeant "
                "en matière de \u201cretour sur investissement\u201d après une formation de longue durée.")
    return ""

groups = OrderedDict()  # key -> entry
order_counter = 0

for e in raw:
    tech = e['tech']; libelle = e['libelle']; mesure = e['mesure']; base = e['base']
    modalites = modalites_from_detail(e['detail']) if not mesure else None
    tech_key = norm_key(tech)
    if mesure:
        # measures: dedupe strictly by technical name only
        key = 'M::' + tech_key
    else:
        key = 'T::' + tech_key  # first pass keyed by technical name

    if key not in groups:
        order_counter += 1
        groups[key] = {
            'order': order_counter,
            'type': 'mesure' if mesure else 'dimension',
            'libelle': libelle,
            'noms_techniques': [],
            'modalites': modalites,
            'regles': [],
            'bases': [],
        }
    g = groups[key]
    if tech not in g['noms_techniques']:
        g['noms_techniques'].append(tech)
    if e['regle'] and e['regle'] not in g['regles']:
        g['regles'].append(e['regle'])
    if not g['modalites'] and modalites:
        g['modalites'] = modalites
    if base not in g['bases']:
        g['bases'].append(base)

# second pass: merge DIMENSIONS sharing identical normalized libelle across different technical names
by_libelle = OrderedDict()
final = []
for key, g in groups.items():
    if g['type'] == 'dimension':
        lk = norm_key(g['libelle'])
        if lk in by_libelle:
            tgt = by_libelle[lk]
            for tn in g['noms_techniques']:
                if tn not in tgt['noms_techniques']:
                    tgt['noms_techniques'].append(tn)
            for r in g['regles']:
                if r not in tgt['regles']:
                    tgt['regles'].append(r)
            if not tgt['modalites'] and g['modalites']:
                tgt['modalites'] = g['modalites']
            for b in g['bases']:
                if b not in tgt['bases']:
                    tgt['bases'].append(b)
            continue
        by_libelle[lk] = g
        final.append(g)
    else:
        final.append(g)

print('Entrées finales:', len(final), '(mesures:', sum(1 for g in final if g['type']=='mesure'),
      ', dimensions:', sum(1 for g in final if g['type']=='dimension'), ')')

# Build output records
records = []
for g in final:
    libelle = g['libelle']
    mesure = g['type'] == 'mesure'
    key = norm_key(libelle)
    if any(r['id'] == key for r in records):
        # avoid slug collision (rare)
        key = key + '-' + norm_key(g['noms_techniques'][0])
    regle_txt = g['regles'][0] if g['regles'] else None
    definition = CURATED_DEFS.get(norm_key(libelle))
    if not definition:
        definition = auto_definition(g['noms_techniques'][0], libelle, mesure, g['modalites'], regle_txt, None, g['bases'][0])
    modalites_table = None
    if g['modalites'] and not mesure:
        rules = rules_by_value(regle_txt) if regle_txt else {}
        modalites_table = []
        for v in g['modalites']:
            modalites_table.append({'valeur': v, 'regle': simplify_condition(rules.get(v, '')) if rules.get(v) else ''})
    pages = []
    sources = []
    for b in g['bases']:
        for p in BASE_PAGES.get(b, []):
            if p not in pages:
                pages.append(p)
        for s in BASE_SOURCES.get(b, []):
            if s not in sources:
                sources.append(s)
    rec = {
        'id': key,
        'type': g['type'],
        'libelle': libelle,
        'noms_techniques': g['noms_techniques'],
        'definition': definition,
        'modalites': modalites_table,
        'pages': pages,
        'bases': [BASE_LABELS.get(b,b) for b in g['bases']],
        'sources': sources,
        'cas_usage': make_cas_usage(key, libelle),
    }
    if mesure:
        rec['periode_calcul'] = ""
    records.append(rec)

# Add curated cas d'usage for the accès/présence emploi example on TAETPED aggregate measures
for rec in records:
    if rec['type'] == 'mesure' and 'X9F027' in rec['noms_techniques'] or (rec['type']=='mesure' and 'X9F030' in rec.get('noms_techniques',[])):
        rec['cas_usage'] = ("L'analyse conjointe de l'accès et de la présence en emploi permet de mieux mesurer l'impact des "
                             "formations à court et à plus long terme. En comparant l'accès à l'emploi de l'ensemble des "
                             "demandeurs d'emploi avec l'accès à l'emploi des sortants de formation, on mesure l'impact de "
                             "la formation sur l'accès à l'emploi.")
for rec in records:
    if rec['type'] == 'mesure' and rec['libelle'].startswith("Accès à l'emploi") and 'RPE_FTAE' in [b for b in []]:
        pass

GROUP_RULES = [
    (re.compile(r"^Acc[èe]s [àa] l'emploi"), "Accès à l'emploi"),
    (re.compile(r'^Pr[ée]sence en emploi'), 'Présence en emploi'),
]
for rec in records:
    for rx, group_name in GROUP_RULES:
        if rx.match(rec['libelle']):
            rec['groupe'] = group_name
            break

# Variables hiérarchiques : niveaux d'agrégation d'un même référentiel connu.
# Chaque niveau pointe vers le niveau supérieur (plus agrégé) et/ou inférieur
# (plus détaillé). Contrairement au "groupe", il ne s'agit pas de données aux
# définitions proches mais de la même donnée observée à différents niveaux.
HIER_CHAINS = [
    # niveaux du plus détaillé (0) au plus agrégé, listes = ex aequo possibles
    {'nom': 'Catégorie juridique', 'niveaux': [
        ['Catégorie juridique'],
        ['Catégorie juridique niv1'],
        ['Catégorie juridique niv2'],
        ['Catégorie juridique niv3'],
    ]},
]
by_libelle_final = {r['libelle']: r for r in records}
for chain in HIER_CHAINS:
    for niveau, labels in enumerate(chain['niveaux']):
        for lbl in labels:
            if lbl not in by_libelle_final:
                continue
            rec = by_libelle_final[lbl]
            rec['hierarchie'] = {'nom': chain['nom'], 'niveau': niveau}

records.sort(key=lambda r: (norm_key(r['libelle'])))

# Top X / Taux X / Part X : la variable doit aussi etre trouvable a la lettre
# du premier mot important du nom (on ignore "de"/"d'"/"des"/"du"/"l'"/"la"/"le"/"les"/"a").
STOPWORDS_ALIAS = {'de', 'des', 'du', 'la', 'le', 'les', 'a', 'au', 'aux', 'en', 'et', 'un', 'une'}
ALIAS_PREFIX_RE = re.compile(r"^(Top|Taux|Part)\s+(.*)$", re.IGNORECASE)
ELISION_RE = re.compile(r"^(d|l|qu)'(.+)$", re.IGNORECASE)

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def alias_letter(libelle):
    m = ALIAS_PREFIX_RE.match(libelle)
    if not m:
        return None
    for tok in m.group(2).split():
        el = ELISION_RE.match(tok)
        if el:
            word = el.group(2)
            if word:
                tok = word
            else:
                continue
        elif strip_accents(tok).lower() in STOPWORDS_ALIAS:
            continue
        letters = [c for c in tok if c.isalpha()]
        if not letters:
            continue
        return strip_accents(letters[0]).upper()
    return None

for rec in records:
    al = alias_letter(rec['libelle'])
    first_letter = strip_accents(rec['libelle'][0]).upper()
    if al and al != first_letter:
        rec['alias_lettre'] = al

json.dump(records, open('../data/glossary.json','w'), ensure_ascii=False, indent=1)
print('Ecrit: data/glossary.json ->', len(records), 'entrées')

all_pages = sorted({p for plist in BASE_PAGES.values() for p in plist}, key=norm_key)
all_sources = sorted({s for slist in BASE_SOURCES.values() for s in slist}, key=norm_key)
json.dump({'pages': all_pages, 'sources': all_sources}, open('../data/pages_sources.json', 'w'), ensure_ascii=False, indent=1)
print('Ecrit: data/pages_sources.json ->', len(all_pages), 'pages,', len(all_sources), 'sources')
