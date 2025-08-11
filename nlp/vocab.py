from typing import Dict, List

# Minimal state aliasing; can be expanded if needed
STATE_ALIASES: Dict[str, str] = {
    'tx': 'United States|TX',
    'texas': 'United States|TX',
    'ca': 'United States|CA',
    'california': 'United States|CA',
    'ny': 'United States|NY',
    'new york': 'United States|NY',
}

SEX_SYNONYMS: Dict[str, str] = {
    'bull': 'B', 'bulls': 'B', 'male': 'B', 'males': 'B',
    'female': 'C', 'females': 'C', 'cow': 'C', 'cows': 'C',
    'both': ''
}

TRAIT_SYNONYMS: Dict[str, str] = {
    'ced': 'CE Direct', 'ce direct': 'CE Direct', 'calving ease direct': 'CE Direct',
    'bw': 'Birth Weight', 'birth weight': 'Birth Weight',
    'ww': 'Weaning Weight', 'weaning weight': 'Weaning Weight',
    'yw': 'Yearling Weight', 'yearling weight': 'Yearling Weight',
    'mk': 'Milk', 'milk': 'Milk', 'maternal milk': 'Milk',
    'cem': 'CE Maternal', 'ce maternal': 'CE Maternal',
    'st': 'Stayability', 'stayability': 'Stayability',
    'yg': 'Yield Grade', 'yield grade': 'Yield Grade',
    'cw': 'Carcass Weight', 'carcass weight': 'Carcass Weight',
    'rea': 'Ribeye Area', 'ribeye area': 'Ribeye Area',
    'fat': 'Fat Thickness', 'fat thickness': 'Fat Thickness',
    'mb': 'Marbling', 'marbling': 'Marbling',
    '$cez': '$CEZ', 'cez': '$CEZ',
    '$bmi': '$BMI', 'bmi': '$BMI',
    '$cpi': '$CPI', 'cpi': '$CPI',
    '$f': '$F', 'f index': '$F',
}

SORT_FIELD_ALIASES: Dict[str, str] = {
    'ww': 'epd_ww', 'weaning weight': 'epd_ww',
    'yw': 'epd_yw', 'yearling weight': 'epd_yw',
    'milk': 'epd_milk',
    'bw': 'epd_bw',
} 