"""Major League Hacking's season calendar: https://www.mlh.com/seasons

The page is an Inertia.js app, so all event data is in a JSON <script data-page="app"> tag.
A season named YYYY runs from roughly August of YYYY-1 to July of YYYY.
"""

import json
import re
from datetime import date, datetime

import httpx

from canthackit.models import Event

SEASON_URL = "https://www.mlh.com/seasons/{}/events"
PAGE_DATA = re.compile(r'<script data-page="app" type="application/json">(.*?)</script>', re.S)
IN_PERSON = ("physical", "hybrid_physical")


def parse_page(page: str) -> list[Event]:
    data = json.loads(PAGE_DATA.search(page).group(1))
    events = []
    for e in data["props"]["upcomingEvents"]:
        venue = e.get("venueAddress") or {}
        if venue.get("country") != "US" or e.get("formatType") not in IN_PERSON:
            continue
        events.append(
            Event(
                name=e["name"].strip(),
                url=e.get("websiteUrl") or f"https://www.mlh.com{e['url']}",
                kind="hackathon",
                start=datetime.fromisoformat(e["startsAt"]).date(),
                end=datetime.fromisoformat(e["endsAt"]).date(),
                city=venue.get("city") or "",
                state=venue.get("state") or "",
                sources=["mlh"],
            )
        )
    return events


def fetch(client: httpx.Client) -> list[Event]:
    events: dict[str, Event] = {}
    this_year = date.today().year
    for season in (this_year, this_year + 1):
        response = client.get(SEASON_URL.format(season))
        if response.status_code == 404:  # next season may not be published yet
            continue
        for event in parse_page(response.raise_for_status().text):
            events[event.url] = event
    return list(events.values())
