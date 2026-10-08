"""Merge the same event reported by several sources (e.g. Devpost and Hack Club)."""

import re

from rapidfuzz import fuzz

from canthackit.models import Event
from canthackit.us import state_name

NAME_THRESHOLD = 85
CITY_THRESHOLD = 80
# Identical names this long are specific enough to trust over a city mismatch; shorter ones
# ("DevFest", "Hack Night") are generic series names that need the city to agree.
MIN_DISTINCT_NAME = 12


def _name(name: str) -> str:
    # "HackMIT 2026" and "Hack MIT '26" should compare equal-ish, so drop years and punctuation.
    name = re.sub(r"\b(19|20)\d{2}\b|'\d{2}\b", " ", name.lower())
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


def _url(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url.lower()).rstrip("/")


def _states_differ(a: Event, b: Event) -> bool:
    return bool(a.state and b.state) and state_name(a.state) != state_name(b.state)


def _places_conflict(a: Event, b: Event) -> bool:
    """Sources often disagree on the city (metro vs. suburb), so a state match outranks it."""
    if not (a.city and b.city):
        return False
    if a.state and b.state:
        return _states_differ(a, b)
    return fuzz.partial_ratio(a.city.lower(), b.city.lower()) < CITY_THRESHOLD


def same_event(a: Event, b: Event) -> bool:
    if abs((a.start - b.start).days) > 1:
        return False
    if _url(a.url) == _url(b.url):
        return True
    name_a, name_b = _name(a.name), _name(b.name)
    if name_a == name_b and len(name_a) >= MIN_DISTINCT_NAME:
        return not _states_differ(a, b)
    # "DevFest Boston" vs "DevFest Austin" on the same day are different events.
    if _places_conflict(a, b):
        return False
    return fuzz.token_set_ratio(name_a, name_b) >= NAME_THRESHOLD


def merge(known: list[Event], incoming: list[Event]) -> list[Event]:
    """Fold `incoming` into `known` in place and return the events not seen before."""
    new = []
    for event in incoming:
        match = next((k for k in known if same_event(k, event)), None)
        if match:
            match.sources = sorted(set(match.sources) | set(event.sources))
        else:
            known.append(event)
            new.append(event)
    return new
