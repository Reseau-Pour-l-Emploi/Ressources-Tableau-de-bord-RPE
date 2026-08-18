# -*- coding: utf-8 -*-
"""
Génère data/glossary.json et data/pages_sources.json à partir d'une seule source :
sources/glossaire_source.json (une entrée par page, avec sa définition, ses indicateurs et
ses champs de tableau personnalisé - définitions/modalités/noms techniques déjà complétés
quand ils étaient connus).

Pour ajouter/corriger une donnée : éditer directement sources/glossaire_source.json, puis
relancer ce script. Aucun fichier Excel n'est lu ici.
"""
import json
import re
import unicodedata

SRC = 'sources/glossaire_source.json'

STOPWORDS_ALIAS = {'de', 'des', 'du', 'la', 'le', 'les', 'a', 'au', 'aux', 'en', 'et', 'un', 'une'}


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def norm_key(s):
    s = strip_accents((s or '').lower())
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def clean_champ_name(champ):
    return champ.rstrip('.').strip()


def definition_slug(definition, maxwords=4):
    words = re.findall(r"[A-Za-zÀ-ÿ]+", definition or '')
    sig = [w for w in words if strip_accents(w).lower() not in STOPWORDS_ALIAS and len(w) > 2][:maxwords]
    return norm_key(' '.join(sig)) or 'def'


def unique_id(base_id, definition, used_ids):
    if base_id not in used_ids:
        used_ids.add(base_id)
        return base_id
    rid = base_id + '--' + definition_slug(definition)
    n = 2
    while rid in used_ids:
        rid = base_id + '--' + definition_slug(definition) + '-' + str(n)
        n += 1
    used_ids.add(rid)
    return rid


def modalites_field(item):
    """item['modalites'] est une simple liste de valeurs dans la source ; le glossaire final
    attend une liste d'objets {valeur, regle}."""
    if not item.get('modalites'):
        return None
    return [{'valeur': v, 'regle': ''} for v in item['modalites']]


data = json.load(open(SRC))
pages = data['pages']

records = []
order_counter = 0
used_ids = set()

# ---------------------------------------------------------------------------
# 0. Les pages et leurs definitions ne sont PAS des fiches du glossaire : uniquement des
#    metadonnees utilisees pour le filtre page, l'affichage de la definition au filtrage,
#    et l'infobulle sur les etiquettes de page (voir data/pages_sources.json).
# ---------------------------------------------------------------------------

#    Certains indicateurs (notamment sur "Accueil") reprennent mot pour mot la
#    definition d'une page ("<Page> : <definition_page>") : on evite de dupliquer
#    ce texte, on renvoie simplement vers la fiche "definition de page" correspondante.
# ---------------------------------------------------------------------------
page_defs = {p['page']: (p.get('definition_page') or '').strip() for p in pages}


def norm_text(s):
    return re.sub(r'\s+', ' ', (s or '').strip()).rstrip('.').strip()


page_defs_norm = {pname: norm_text(pdef) for pname, pdef in page_defs.items() if pdef}
by_libelle_norm = {}
by_page_libelle = {}


def detect_page_reference(definition, current_page):
    if ' : ' not in definition:
        return None
    suffix = norm_text(definition.split(' : ', 1)[1])
    if len(suffix) < 25:
        return None
    exact = [pname for pname, pdef in page_defs_norm.items() if pdef == suffix]
    partial = [pname for pname, pdef in page_defs_norm.items() if pname not in exact and suffix in pdef]
    candidates = exact or partial
    if not candidates:
        return None
    others = [c for c in candidates if c != current_page]
    return others[0] if others else candidates[0]


for p in pages:
    page = p['page']
    if page == 'Accueil':
        continue
    for ind in p.get('indicateurs', []):
        libelle = ind['libelle']
        definition_raw = ind.get('definition') or ''
        cas_usage = ''
        definition = definition_raw
        if '➡' in definition_raw:
            parts = definition_raw.split('➡', 1)
            definition = parts[0].strip()
            cas_usage = parts[1].strip()
        renvoie_page = detect_page_reference(definition, page)
        if renvoie_page:
            definition = ''
        order_counter += 1
        base_id = norm_key(page) + '--' + norm_key(libelle)
        rid = unique_id(base_id, definition or libelle, used_ids)
        rec = {
            'order': order_counter,
            'id': rid,
            'libelle': libelle,
            'type': 'mesure',
            'source': 'indicateur',
            'kpi': bool(ind.get('kpi')),
            'categorie': None,
            'definition': definition,
            'cas_usage': cas_usage,
            'modalites': modalites_field(ind),
            'periode_calcul': '',
            'pages': [page],
            'sources': ind.get('sources') or [],
            'noms_techniques': ind.get('noms_techniques') or [],
        }
        if renvoie_page:
            rec['renvoie_page'] = renvoie_page
        records.append(rec)
        by_libelle_norm.setdefault(norm_key(libelle), []).append(rec)
        by_page_libelle[(page, norm_key(libelle))] = rec

# Accueil reprend souvent, mot pour mot, des indicateurs deja presents sur leur page dediee,
# mais parfois sous un intitule different (ex. "Taux d'acces a l'emploi" sur Accueil correspond
# a "Acces a l'emploi a 6 mois" sur la page dediee) : cette table fait le lien explicite quand
# le simple rapprochement par libelle identique ne suffit pas.
ACCUEIL_MAPPING = {
    "Taux d'accès à l'emploi": ('Accès / Présence en emploi', "Accès à l'emploi à 6 mois"),
    "Taux de présence en emploi": ('Accès / Présence en emploi', "Présence en emploi à 6 mois"),
    "Taux de satisfaction des demandeurs d'emploi sur leur accompagnement": ('Satisfaction DE', "Taux de satisfaction des demandeurs d'emploi pour leur accompagnement"),
    "Taux de pourvoi des offres": ('Taux / Délai de pourvoi', "Taux de pourvoi des offres d'emploi"),
    "Délai de pourvoi des offres": ('Taux / Délai de pourvoi', "Délai de pourvoi des offres d'emploi"),
    "Part des publics prioritaires dans les entrants en formation": ('Entrants en formation', "Publics prioritaires dans les entrants en formation"),
    "Taux d'accès à l'emploi des sortants de formation": ('Sortants de formation', "Accès à l'emploi à 6 mois"),
}

# Accueil reprend souvent, mot pour mot, des indicateurs deja presents sur leur page dediee.
# Dans ce cas on garde une seule fiche (celle de la page dediee, avec sa definition), mais on
# la rattache aussi a la page "Accueil" (elle reste taguee/trouvable via ce filtre).
accueil_page = next((p for p in pages if p['page'] == 'Accueil'), None)
n_merged_accueil = 0
if accueil_page:
    for ind in accueil_page.get('indicateurs', []):
        libelle = ind['libelle']
        candidates = by_libelle_norm.get(norm_key(libelle), [])
        existing = candidates[0] if candidates else None
        if not existing and libelle in ACCUEIL_MAPPING:
            target_page, target_libelle = ACCUEIL_MAPPING[libelle]
            existing = by_page_libelle.get((target_page, norm_key(target_libelle)))
        if existing:
            if 'Accueil' not in existing['pages']:
                existing['pages'].append('Accueil')
            if ind.get('kpi'):
                existing['kpi'] = True
            n_merged_accueil += 1
            continue
        definition_raw = ind.get('definition') or ''
        cas_usage = ''
        definition = definition_raw
        if '➡' in definition_raw:
            parts = definition_raw.split('➡', 1)
            definition = parts[0].strip()
            cas_usage = parts[1].strip()
        renvoie_page = detect_page_reference(definition, 'Accueil')
        if renvoie_page:
            definition = ''
        order_counter += 1
        base_id = norm_key('Accueil') + '--' + norm_key(libelle)
        rid = unique_id(base_id, definition or libelle, used_ids)
        rec = {
            'order': order_counter,
            'id': rid,
            'libelle': libelle,
            'type': 'mesure',
            'source': 'indicateur',
            'kpi': bool(ind.get('kpi')),
            'categorie': None,
            'definition': definition,
            'cas_usage': cas_usage,
            'modalites': modalites_field(ind),
            'periode_calcul': '',
            'pages': ['Accueil'],
            'sources': ind.get('sources') or [],
            'noms_techniques': ind.get('noms_techniques') or [],
        }
        if renvoie_page:
            rec['renvoie_page'] = renvoie_page
        records.append(rec)
        by_libelle_norm.setdefault(norm_key(libelle), []).append(rec)

print('Indicateurs de page :', sum(1 for r in records if r['source'] == 'indicateur'))

# ---------------------------------------------------------------------------
# 2. Champs des tableaux personnalisés (source = 'champ_tableau')
#    - Dimensions fusionnees entre pages par nom de champ (avec niveaux hierarchiques)
#    - Mesures gardees distinctes par page
# ---------------------------------------------------------------------------
dim_groups = {}
mesure_rows = []

for p in pages:
    page = p['page']
    for row in p.get('champs_tableau', []):
        type_str = row['type']
        categorie = row.get('categorie')
        champ = row['champ']
        niveau_hier = row.get('niveau_hierarchique')
        champ_clean = clean_champ_name(champ)
        if type_str == 'Dimension':
            key = norm_key(champ_clean)
            g = dim_groups.setdefault(key, {
                'champ_clean': champ_clean, 'categorie': categorie, 'pages': [], 'niveaux': [],
                'definition': row.get('definition') or '', 'modalites': modalites_field(row),
                'noms_techniques': row.get('noms_techniques') or [], 'sources': row.get('sources') or [],
            })
            if page not in g['pages']:
                g['pages'].append(page)
            if niveau_hier and niveau_hier not in g['niveaux']:
                g['niveaux'].append(niveau_hier)
        else:
            mesure_rows.append(dict(row, page=page, champ_clean=champ_clean))

for key, g in dim_groups.items():
    base_id = 'champ--' + key
    order_counter += 1
    hierarchie = {'nom': g['champ_clean'], 'niveau': 0} if g['niveaux'] else None
    records.append({
        'order': order_counter,
        'id': base_id,
        'libelle': g['champ_clean'],
        'type': 'dimension',
        'source': 'champ_tableau',
        'kpi': False,
        'categorie': g['categorie'],
        'definition': g['definition'],
        'cas_usage': '',
        'modalites': g['modalites'],
        'periode_calcul': None,
        'pages': list(g['pages']),
        'sources': g['sources'],
        'noms_techniques': g['noms_techniques'],
        'hierarchie': hierarchie,
    })
    for idx, label in enumerate(g['niveaux'], start=1):
        order_counter += 1
        records.append({
            'order': order_counter,
            'id': base_id + '-niv' + str(idx),
            'libelle': g['champ_clean'] + ' - ' + label,
            'type': 'dimension',
            'source': 'champ_tableau',
            'kpi': False,
            'categorie': g['categorie'],
            'definition': '',
            'cas_usage': '',
            'modalites': None,
            'periode_calcul': None,
            'pages': list(g['pages']),
            'sources': [],
            'noms_techniques': [],
            'hierarchie': {'nom': g['champ_clean'], 'niveau': idx},
        })

for m in mesure_rows:
    order_counter += 1
    base_id = 'mesure--' + norm_key(m['page']) + '--' + norm_key(m['champ_clean'])
    rid = unique_id(base_id, m['champ_clean'], used_ids)
    records.append({
        'order': order_counter,
        'id': rid,
        'libelle': m['champ_clean'],
        'type': 'mesure',
        'source': 'champ_tableau',
        'kpi': False,
        'categorie': m.get('categorie'),
        'definition': m.get('definition') or '',
        'cas_usage': '',
        'modalites': modalites_field(m),
        'periode_calcul': '',
        'pages': [m['page']],
        'sources': m.get('sources') or [],
        'noms_techniques': m.get('noms_techniques') or [],
    })

print('Champs de tableaux personnalises (dimensions + niveaux + mesures) :',
      sum(1 for r in records if r['source'] == 'champ_tableau'))

# ---------------------------------------------------------------------------
# 3. Regroupements "definitions proches" (Accès à l'emploi / Présence en emploi)
# ---------------------------------------------------------------------------
GROUP_RULES = [
    (re.compile(r"^Acc[èe]s [àa] l'emploi"), "Accès à l'emploi"),
    (re.compile(r'^Pr[ée]sence en emploi'), 'Présence en emploi'),
]
for rec in records:
    for rx, group_name in GROUP_RULES:
        if rx.match(rec['libelle']):
            rec['groupe'] = group_name
            break

# ---------------------------------------------------------------------------
# 4. Lettre alias pour "Top X" / "Taux X" / "Part X" / "Type X" / "Date X"
# ---------------------------------------------------------------------------
ALIAS_PREFIX_RE = re.compile(r"^(Top|Taux|Part|Type|Date)\s+(.*)$", re.IGNORECASE)
ELISION_RE = re.compile(r"^(d|l|qu)'(.+)$", re.IGNORECASE)


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

# ---------------------------------------------------------------------------
# 5. Ecriture
# ---------------------------------------------------------------------------
for rec in records:
    del rec['order']

records.sort(key=lambda r: norm_key(r['libelle']))

# Garde-fou : chaque fiche doit venir de sources/glossaire_source.json (indicateurs ou champs
# de tableaux personnalises) - jamais d'une autre origine. Les pages elles-memes ne sont pas
# des fiches : uniquement des metadonnees de filtre (voir data/pages_sources.json).
n_indicateur = sum(1 for r in records if r['source'] == 'indicateur')
n_champ = sum(1 for r in records if r['source'] == 'champ_tableau')
n_indicateur_attendu = sum(len(p.get('indicateurs', [])) for p in pages) - n_merged_accueil
assert n_indicateur == n_indicateur_attendu, 'Incoherence indicateurs : %d vs %d attendus' % (n_indicateur, n_indicateur_attendu)
assert n_indicateur + n_champ == len(records), 'Incoherence : une fiche ne provient pas de indicateur/champ_tableau'
assert all(r['source'] != 'page' for r in records), 'Une fiche "page" a ete generee alors que les pages ne doivent etre que des filtres'

json.dump(records, open('data/glossary.json', 'w'), ensure_ascii=False, indent=1)
print('Ecrit: data/glossary.json ->', len(records), 'entrees')

all_pages = sorted({p['page'] for p in pages}, key=norm_key)
page_definitions = {p['page']: p.get('definition_page') or '' for p in pages if p.get('definition_page')}
json.dump({'pages': all_pages, 'sources': [], 'page_definitions': page_definitions},
          open('data/pages_sources.json', 'w'), ensure_ascii=False, indent=1)
print('Ecrit: data/pages_sources.json ->', len(all_pages), 'pages,', len(page_definitions), 'definitions')

print('dont KPI :', sum(1 for r in records if r.get('kpi')))
