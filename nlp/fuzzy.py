from typing import List, Tuple, Optional

try:
    from rapidfuzz import process, fuzz
    HAVE_RAPIDFUZZ = True
except Exception:
    HAVE_RAPIDFUZZ = False


def _ratio(a: str, b: str) -> int:
    if HAVE_RAPIDFUZZ:
        return int(fuzz.token_set_ratio(a, b))
    # Fallback: simple containment score
    a = (a or '').lower()
    b = (b or '').lower()
    if not a or not b:
        return 0
    if a in b or b in a:
        return 80
    return 0


def fuzzy_choice(query: str, choices: List[str], limit: int = 5) -> List[Tuple[str, int]]:
    if not choices:
        return []
    if HAVE_RAPIDFUZZ:
        return [(m[0], int(m[1])) for m in process.extract(query, choices, scorer=fuzz.token_set_ratio, limit=limit)]
    scored = [(c, _ratio(query, c)) for c in choices]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def best_location_match(user_text: str, options: List[dict]) -> Optional[Tuple[str, int]]:
    # options: [{value, text}]
    texts = [o.get('text', '') for o in options]
    scored = fuzzy_choice(user_text, texts, limit=1)
    if not scored:
        return None
    best_text, score = scored[0]
    # find option with this text
    for o in options:
        if o.get('text') == best_text:
            return (o.get('value', ''), score)
    return None


def suggest_locations(user_text: str, options: List[dict], limit: int = 5) -> List[Tuple[str, str, int]]:
    texts = [o.get('text', '') for o in options]
    top = fuzzy_choice(user_text, texts, limit=limit)
    out: List[Tuple[str, str, int]] = []
    for text, score in top:
        val = next((o['value'] for o in options if o.get('text') == text), '')
        out.append((val, text, score))
    return out 