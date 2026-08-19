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
    c = champ.rstrip('.').strip()
    return CHAMP_LABEL_ALIASES.get(c, c)


# Libelles de champs quasi-identiques (variante orthographique) designant la meme donnee.
# A completer si d'autres rapprochements de ce type sont identifies.
CHAMP_LABEL_ALIASES = {
    'Top 50 ans et +': 'Top 50 ans et plus',
    'Top 55 ans et +': 'Top 55 ans et plus',
}


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


ACCES_PRESENCE_PAGE = 'Accès / Présence en emploi'
# Categories de ventilation qui se repetent identiquement sous plusieurs "sections" d'une
# meme page (ex. la page Accès/Présence liste BRSA, Bénéficiaires de l'obligation d'emploi...
# une fois sous "Accès à l'emploi", une fois sous "Présence en emploi").
BREAKDOWN_LABELS_RAW = [
    'BRSA', 'Bénéficiaires du RSA', 'Bénéficiaires du RSA / BRSA', "Bénéficiaires de l'obligation d'emploi",
    'Niveau inférieur au BAC', "Moins de 26 ans et jusqu'à BAC+2",
    '50 ans et plus', '55 ans et plus', 'Résidents QPV', 'Résidents ZFRR',
]
BREAKDOWN_LABELS = {norm_key(x) for x in BREAKDOWN_LABELS_RAW}


def short_section(anchor):
    low = strip_accents(anchor).lower()
    if low.startswith('acces'):
        return "Accès à l'emploi"
    if low.startswith('presence'):
        return 'Présence en emploi'
    return anchor


def context_label(page, section):
    if not section:
        return page
    short = short_section(section)
    if page == ACCES_PRESENCE_PAGE:
        return short
    return page + ' - ' + short


# Libelles differents designant la meme donnee : fusionnes sous un nom canonique commun.
# A completer si d'autres rapprochements de ce type sont identifies.
LABEL_ALIASES = {
    'BRSA': 'Bénéficiaires du RSA / BRSA',
    'Bénéficiaires du RSA': 'Bénéficiaires du RSA / BRSA',
}


def canonical_libelle(libelle):
    return LABEL_ALIASES.get(libelle, libelle)


indicateur_groups = {}
occurrences_par_page = {}
for p in pages:
    page = p['page']
    if page == 'Accueil':
        continue
    for ind in p.get('indicateurs', []):
        key = (page, norm_key(canonical_libelle(ind['libelle'])))
        occurrences_par_page[key] = occurrences_par_page.get(key, 0) + 1

for p in pages:
    page = p['page']
    if page == 'Accueil':
        continue
    current_section = None
    for ind in p.get('indicateurs', []):
        libelle = canonical_libelle(ind['libelle'])
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
        is_breakdown = norm_key(libelle) in BREAKDOWN_LABELS
        if is_breakdown:
            section = current_section
        else:
            current_section = libelle
            section = None
        # Le contexte (section) n'est utile que si CE libelle se repete plusieurs fois sur
        # cette meme page (sinon le nom de la page seul suffit a le distinguer).
        repeated_on_page = occurrences_par_page[(page, norm_key(libelle))] > 1
        ctx = context_label(page, section) if repeated_on_page else page
        indicateur_groups.setdefault(norm_key(libelle), []).append({
            'page': page, 'context': ctx, 'libelle': libelle,
            'definition': definition, 'cas_usage': cas_usage,
            'kpi': bool(ind.get('kpi')), 'modalites': modalites_field(ind),
            'sources': ind.get('sources') or [], 'noms_techniques': ind.get('noms_techniques') or [],
            'renvoie_page': renvoie_page,
        })

n_merged_cross_page = 0
for libelle_norm, items in indicateur_groups.items():
    contexts_seen = [it['context'] for it in items]
    pages_seen_dedup = []
    for it in items:
        if it['page'] not in pages_seen_dedup:
            pages_seen_dedup.append(it['page'])
    can_merge = len(items) > 1 and len(set(contexts_seen)) == len(contexts_seen)
    if can_merge:
        n_merged_cross_page += len(items) - 1
        # Meme intitule reutilise (entre pages, ou plusieurs fois sur une meme page dans un
        # contexte different) : une seule fiche, avec une definition propre a chaque contexte.
        order_counter += 1
        base_id = 'indicateur--' + libelle_norm
        rid = unique_id(base_id, items[0]['libelle'], used_ids)
        definitions_par_page = {it['context']: it['definition'] for it in items if it['definition']}
        rec = {
            'order': order_counter,
            'id': rid,
            'libelle': items[0]['libelle'],
            'type': 'mesure',
            'source': 'indicateur',
            'kpi': any(it['kpi'] for it in items),
            'categorie': None,
            'definition': next((it['definition'] for it in items if it['definition']), ''),
            'cas_usage': next((it['cas_usage'] for it in items if it['cas_usage']), ''),
            'modalites': next((it['modalites'] for it in items if it['modalites']), None),
            'periode_calcul': '',
            'pages': pages_seen_dedup,
            'sources': next((it['sources'] for it in items if it['sources']), []),
            'noms_techniques': next((it['noms_techniques'] for it in items if it['noms_techniques']), []),
        }
        if len(definitions_par_page) > 1:
            rec['definitions_par_page'] = definitions_par_page
        records.append(rec)
        by_libelle_norm.setdefault(libelle_norm, []).append(rec)
        for it in items:
            by_page_libelle[(it['page'], libelle_norm)] = rec
    else:
        # Contextes ambigus non distinguables (rare) : on garde des fiches distinctes.
        for it in items:
            order_counter += 1
            base_id = norm_key(it['page']) + '--' + libelle_norm
            rid = unique_id(base_id, it['definition'] or it['libelle'], used_ids)
            rec = {
                'order': order_counter,
                'id': rid,
                'libelle': it['libelle'],
                'type': 'mesure',
                'source': 'indicateur',
                'kpi': it['kpi'],
                'categorie': None,
                'definition': it['definition'],
                'cas_usage': it['cas_usage'],
                'modalites': it['modalites'],
                'periode_calcul': '',
                'pages': [it['page']],
                'sources': it['sources'],
                'noms_techniques': it['noms_techniques'],
            }
            if it['renvoie_page']:
                rec['renvoie_page'] = it['renvoie_page']
            records.append(rec)
            by_libelle_norm.setdefault(libelle_norm, []).append(rec)
            by_page_libelle[(it['page'], libelle_norm)] = rec

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

mesure_groups = {}
for m in mesure_rows:
    mesure_groups.setdefault(norm_key(m['champ_clean']), []).append(m)

n_merged_mesure_champ = 0
for champ_key, items in mesure_groups.items():
    pages_seen = [it['page'] for it in items]
    can_merge = len(items) > 1 and len(set(pages_seen)) == len(pages_seen)
    if can_merge:
        n_merged_mesure_champ += len(items) - 1
        order_counter += 1
        base_id = 'mesure--' + champ_key
        rid = unique_id(base_id, items[0]['champ_clean'], used_ids)
        definitions_par_page = {it['page']: (it.get('definition') or '') for it in items if it.get('definition')}
        rec = {
            'order': order_counter,
            'id': rid,
            'libelle': items[0]['champ_clean'],
            'type': 'mesure',
            'source': 'champ_tableau',
            'kpi': False,
            'categorie': next((it.get('categorie') for it in items if it.get('categorie')), None),
            'definition': next((it.get('definition') for it in items if it.get('definition')), '') or '',
            'cas_usage': '',
            'modalites': next((modalites_field(it) for it in items if modalites_field(it)), None),
            'periode_calcul': '',
            'pages': pages_seen,
            'sources': next((it.get('sources') for it in items if it.get('sources')), []),
            'noms_techniques': next((it.get('noms_techniques') for it in items if it.get('noms_techniques')), []),
        }
        if len(definitions_par_page) > 1:
            rec['definitions_par_page'] = definitions_par_page
        records.append(rec)
    else:
        for it in items:
            order_counter += 1
            base_id = 'mesure--' + norm_key(it['page']) + '--' + champ_key
            rid = unique_id(base_id, it['champ_clean'], used_ids)
            records.append({
                'order': order_counter,
                'id': rid,
                'libelle': it['champ_clean'],
                'type': 'mesure',
                'source': 'champ_tableau',
                'kpi': False,
                'categorie': it.get('categorie'),
                'definition': it.get('definition') or '',
                'cas_usage': '',
                'modalites': modalites_field(it),
                'periode_calcul': '',
                'pages': [it['page']],
                'sources': it.get('sources') or [],
                'noms_techniques': it.get('noms_techniques') or [],
            })

print('Champs de tableaux personnalises (dimensions + niveaux + mesures) :',
      sum(1 for r in records if r['source'] == 'champ_tableau'))

# ---------------------------------------------------------------------------
# 3. Regroupements "definitions proches" (Accès à l'emploi / Présence en emploi)
# ---------------------------------------------------------------------------
GROUP_RULES = [
    (re.compile(r"^Acc[èe]s [àa] l'emploi"), "Accès à l'emploi"),
    (re.compile(r'^Pr[ée]sence en emploi'), 'Présence en emploi'),
    (re.compile(r"^Nombre d'acc[èe]s [àa] un emploi"), "Nombre d'accès à un emploi"),
    (re.compile(r"^Nombre d'individus en emploi"), "Nombre d'individus en emploi"),
    (re.compile(r"^D[ée]lai moyen d'acc[èe]s [àa] l'emploi"), "Délai moyen d'accès à l'emploi"),
    (re.compile(r'^Inscrits depuis plus de'), 'Inscrits depuis plus de X mois'),
]
for rec in records:
    for rx, group_name in GROUP_RULES:
        if rx.match(rec['libelle']):
            rec['groupe'] = group_name
            break

# Un "groupe" d'un seul membre n'a pas de sens (rien a regrouper) : on le retire.
group_sizes = {}
for rec in records:
    if rec.get('groupe'):
        key = (rec['groupe'], rec['source'])
        group_sizes[key] = group_sizes.get(key, 0) + 1
for rec in records:
    if rec.get('groupe') and group_sizes[(rec['groupe'], rec['source'])] < 2:
        del rec['groupe']

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
# 4bis. Un champ de tableau sans definition reprend celle de l'indicateur homonyme
#       (meme libelle), quand il en existe un. Ne remplace jamais une definition deja
#       renseignee (ex. via l'enrichissement issu de l'ancien glossaire).
# ---------------------------------------------------------------------------
indicateur_def_par_libelle = {}
for rec in records:
    if rec['source'] == 'indicateur' and rec.get('definition'):
        indicateur_def_par_libelle.setdefault(norm_key(rec['libelle']), rec['definition'])

n_champ_enrichi_par_indicateur = 0
for rec in records:
    if rec['source'] == 'champ_tableau' and not rec.get('definition'):
        match = indicateur_def_par_libelle.get(norm_key(rec['libelle']))
        if match:
            rec['definition'] = match
            n_champ_enrichi_par_indicateur += 1

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
n_indicateur_attendu = sum(len(p.get('indicateurs', [])) for p in pages) - n_merged_accueil - n_merged_cross_page
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
print('dont champs enrichis par definition d\'indicateur homonyme :', n_champ_enrichi_par_indicateur)
