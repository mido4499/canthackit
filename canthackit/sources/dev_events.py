"""dev.events US listings: https://dev.events/NA/US

Each page embeds schema.org JSON-LD for its ~30 events; `?page=N` walks forward in time.
(Not to be confused with developers.events, handled in dev_conferences.py.)
"""

import json
import re
import time
from datetime import datetime

import httpx

from canthackit.models import Event

URL = "https://dev.events/NA/US"
LD_JSON = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S)
IN_PERSON = ("OfflineEventAttendanceMode", "MixedEventAttendanceMode")


def parse_page(page: str) -> list[dict]:
    """All events on a page, including online ones (needed to detect the last page)."""
    blocks = [json.loads(b) for b in LD_JSON.findall(page)]
    return [b for b in blocks if isinstance(b, dict) and b.get("@type") == "EducationEvent"]


def to_event(e: dict) -> Event | None:
    address = (e.get("location") or {}).get("address") or {}
    in_us = "United States" in (address.get("addressRegion"), address.get("addressCountry"))
    if not in_us or not e.get("eventAttendanceMode", "").endswith(IN_PERSON):
        return None
    return Event(
        name=e["name"].strip(),
        url=e["url"],
        kind="conference",
        start=datetime.fromisoformat(e["startDate"]).date(),
        end=datetime.fromisoformat(e.get("endDate") or e["startDate"]).date(),
        city=address.get("addressLocality") or "",
        sources=["dev.events"],
    )


def fetch(client: httpx.Client) -> list[Event]:
    seen: set[str] = set()
    events = []
    for page in range(1, 50):
        on_page = parse_page(client.get(URL, params={"page": page}).raise_for_status().text)
        fresh = [e for e in on_page if e["url"] not in seen]
        if not fresh:  # past the last page, the site keeps returning the same pinned events
            break
        seen.update(e["url"] for e in fresh)
        events += filter(None, map(to_event, fresh))
        time.sleep(1)
    return events
