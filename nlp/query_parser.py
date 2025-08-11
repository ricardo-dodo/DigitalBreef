import re
from typing import Dict, Tuple, Optional
from .normalizer import normalize_text
from .vocab import STATE_ALIASES, SEX_SYNONYMS, TRAIT_SYNONYMS, SORT_FIELD_ALIASES

INTENT_RANCH = 'ranch'
INTENT_ANIMAL = 'animal'
INTENT_EPD = 'epd'

COMPARATORS = [
    (re.compile(r"\b(>=|=>)\b"), '>='),
    (re.compile(r"\b(<=|=<)\b"), '<='),
    (re.compile(r">"), '>'),
    (re.compile(r"<"), '<'),
]

NUM_RE = re.compile(r"(?P<comp>>=|<=|>|<|=)?\s*(?P<num>\d+(?:\.\d+)?)")


def classify_intent(query: str) -> str:
    q = normalize_text(query)
    if any(w in q for w in ['epd', 'weaning', 'yearling', 'milk', 'marbling', 'ced', 'ww', 'yw']):
        return INTENT_EPD
    if any(w in q for w in ['bull', 'bulls', 'female', 'cow', 'eid', 'tattoo', 'registration']):
        return INTENT_ANIMAL
    return INTENT_RANCH


def _extract_location(q: str) -> Optional[str]:
    # map common state aliases fast
    for k, v in STATE_ALIASES.items():
        if f" {k} " in f" {q} ":
            return v
    # look for 'in X' or 'near X' tokens as a hint (return raw; final mapping done by fuzzy layer in UI)
    m = re.search(r"\b(in|near|at)\s+([a-z\s]+)", q)
    if m:
        return m.group(2).strip()
    return None


def parse_query_for_ranch(query: str) -> Dict[str, str]:
    q = normalize_text(query)
    params: Dict[str, str] = {}
    # name/prefix
    m = re.search(r"prefix\s+([a-z0-9\*\-]+)", q)
    if m:
        params['prefix'] = m.group(1).upper()
    m = re.search(r"ranch(?:es)?\s+named\s+([a-z0-9\*\-]+)", q)
    if m:
        params['name'] = m.group(1).upper()
    # city
    m = re.search(r"\bcity\s+([a-z\s]+)", q)
    if m:
        params['city'] = m.group(1).strip().upper()
    # member id
    m = re.search(r"member\s*id\s*([0-9\-]+)", q)
    if m:
        params['member_id'] = m.group(1).upper()
    # location
    loc_hint = _extract_location(q)
    if loc_hint:
        params['location'] = loc_hint
    # weak: if only a state token present
    for k, v in STATE_ALIASES.items():
        if f" {k} " in f" {q} ":
            params['location'] = v
            break
    return params


def parse_query_for_animal(query: str) -> Dict[str, str]:
    q = normalize_text(query)
    params: Dict[str, str] = {}
    # sex
    for token, sex in SEX_SYNONYMS.items():
        if f" {token} " in f" {q} ":
            params['sex'] = sex
            break
    # field/value heuristics
    if 'eid' in q:
        params['field'] = 'eid'
        m = re.search(r"eid\s*([a-z0-9\*\-]+)", q)
        if m:
            params['value'] = m.group(1).upper()
    elif 'tattoo' in q:
        params['field'] = 'animal_private_herd_id'
        m = re.search(r"tattoo\s*([a-z0-9\*\-]+)", q)
        if m:
            params['value'] = m.group(1).upper()
    elif 'reg' in q or 'registration' in q:
        params['field'] = 'animal_registration'
        m = re.search(r"(reg(?:istration)?\s*#?\s*)([a-z0-9\*\-]+)", q)
        if m:
            params['value'] = m.group(2).upper()
    elif 'name' in q:
        params['field'] = 'animal_name'
        m = re.search(r"name\s+([a-z0-9\*\-]+)", q)
        if m:
            params['value'] = m.group(1).upper()
    # born year hint (stored as value suffix for now; detail filter can use later)
    m = re.search(r"born\s+(\d{4})", q)
    if m and 'value' in params:
        params['value'] = f"{params['value']}"
    return params


def parse_query_for_epd(query: str) -> Dict[str, str]:
    q = normalize_text(query)
    params: Dict[str, str] = {}
    # sex
    for token, sex in SEX_SYNONYMS.items():
        if f" {token} " in f" {q} ":
            params['search_sex'] = sex
            break
    # trait numeric filters, e.g., milk > 25, ww >= 60
    for alias, canonical in TRAIT_SYNONYMS.items():
        if alias in q:
            # build key base
            key = canonical.lower().replace(' ', '_').replace('$', '')
            # find nearest number with optional comparator
            pat = re.compile(rf"{re.escape(alias)}\s*(>=|<=|>|<|=)?\s*(\d+(?:\.\d+)?)")
            m = pat.search(q)
            if m:
                comp = m.group(1) or '>='
                num = m.group(2)
                if comp in ('>', '>=', '='):
                    params[f'{key}_min'] = num
                if comp in ('<', '<=', '='):
                    params[f'{key}_max'] = num
    # sort by
    m = re.search(r"sort\s+by\s+([a-z\s$]+)", q)
    if m:
        sort_token = m.group(1).strip()
        sort_key = SORT_FIELD_ALIASES.get(sort_token, SORT_FIELD_ALIASES.get(sort_token.replace(' ', ''), None))
        if not sort_key:
            # try known synonyms
            canonical = TRAIT_SYNONYMS.get(sort_token, None)
            if canonical:
                base = canonical.lower().replace(' ', '_').replace('$', '')
                sort_key = f'epd_{base}' if base in ['ww', 'yw', 'milk', 'bw'] else None
        if sort_key:
            params['sort_field'] = sort_key
    return params 