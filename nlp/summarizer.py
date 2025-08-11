from typing import List, Dict
from collections import Counter


def _top(counter: Counter, n: int = 5):
    return ', '.join([f"{k}({v})" for k, v in counter.most_common(n)])


def summarize_ranch_results(data: List[Dict[str, str]]) -> str:
    if not data:
        return 'No data to summarize.'
    states = Counter([row.get('state', '') for row in data if row.get('state')])
    cities = Counter([row.get('city', '') for row in data if row.get('city')])
    prefixes = Counter([row.get('herd_prefix', '') for row in data if row.get('herd_prefix')])
    out = []
    out.append(f"Total results: {len(data)}")
    if states:
        out.append(f"Top states: {_top(states)}")
    if cities:
        out.append(f"Top cities: {_top(cities)}")
    if prefixes:
        out.append(f"Top herd prefixes: {_top(prefixes)}")
    return '\n'.join(out)


def summarize_epd_results(data: List[Dict[str, str]]) -> str:
    if not data:
        return 'No data to summarize.'
    names = Counter([row.get('name', '') for row in data if row.get('name')])
    regs = Counter([row.get('registration', '') for row in data if row.get('registration')])
    out = []
    out.append(f"Total animals: {len(data)}")
    if names:
        out.append(f"Most common names: {_top(names)}")
    if regs:
        out.append(f"Most common registrations: {_top(regs)}")
    return '\n'.join(out)


def summarize_animal_results(data: List[Dict[str, str]]) -> str:
    if not data:
        return 'No data to summarize.'
    names = Counter([row.get('name', '') for row in data if row.get('name')])
    out = []
    out.append(f"Total animals: {len(data)}")
    if names:
        out.append(f"Most common names: {_top(names)}")
    return '\n'.join(out) 