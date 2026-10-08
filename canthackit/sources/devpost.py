"""Devpost in-person hackathons.

The list endpoint is undocumented and only gives a free-text venue ("Amy Gutman Hall"), so
the address and exact dates come from the schema.org JSON-LD on each hackathon's page.
Page details are cached in data/devpost_cache.json so each page is fetched only once.
"""

import html
import json
import re
import time
from datetime import datetime

import httpx

from canthackit import DATA_DIR
from canthackit.models import Event
from canthackit.us import US_STATES

LIST_URL = "https://devpost.com/api/hackathons"
CACHE = DATA_DIR / "devpost_cache.json"
LD_JSON = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S)


def _listings(client: httpx.Client) -> list[dict]:
    params = {"challenge_type[]": "in-person", "status[]": ["upcoming", "open"], "per_page": 40}
    hackathons: list[dict] = []
    for page in range(1, 50):
        batch = client.get(LIST_URL, params={**params, "page": page}).raise_for_status().json()
        hackathons += batch["hackathons"]
        if not batch["hackathons"] or len(hackathons) >= batch["meta"]["total_count"]:
            break
    return hackathons


def parse_page(page: str) -> dict | None:
    """Extract dates and address from a hackathon page; None if the page has no event data."""
    for block in LD_JSON.findall(page):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or data.get("@type") != "Event" or "startDate" not in data:
            continue
        address = data.get("location", {}).get("address", {})
        street = address.get("streetAddress", "")
        region = address.get("addressRegion", "")
        return {
            "start": data["startDate"],
            "end": data.get("endDate") or data["startDate"],
            "city": html.unescape(address.get("addressLocality", "")),
            "state": html.unescape(region),
            "us": address.get("addressCountry") in ("US", "USA", "United States")
            or street.rstrip().endswith(("USA", "United States", "Puerto Rico"))
            or region in US_STATES.values(),
        }
    return None


def fetch(client: httpx.Client) -> list[Event]:
    old_cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    cache = {}  # rebuilt each run so ended hackathons drop out
    events = []
    for h in _listings(client):
        url = h["url"]
        if url in old_cache:
            cache[url] = old_cache[url]
        else:
            time.sleep(1)  # be polite: only new hackathons are fetched, ~1/s
            try:
                cache[url] = parse_page(client.get(url).raise_for_status().text)
            except httpx.HTTPError as exc:  # not cached, so it's retried next run
                print(f"devpost: skipping {url}: {exc!r}")
                continue
        details = cache[url]
        if details and details["us"]:
            events.append(
                Event(
                    name=h["title"].strip(),
                    url=url,
                    kind="hackathon",
                    start=datetime.fromisoformat(details["start"]).date(),
                    end=datetime.fromisoformat(details["end"]).date(),
                    city=details["city"],
                    state=details["state"],
                    sources=["devpost"],
                )
            )
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n")
    return events
