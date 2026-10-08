"""Eventbrite events from chosen organizers (config.toml), via the official API.

Eventbrite removed public event search in 2020, so the API can only list events by organizer.
Skipped until EVENTBRITE_TOKEN is set and at least one organizer is configured.
"""

import os
from datetime import datetime

import httpx

from canthackit import load_config
from canthackit.models import Event, guess_kind

URL = "https://www.eventbriteapi.com/v3/organizers/{}/events/"


def to_event(e: dict) -> Event | None:
    address = (e.get("venue") or {}).get("address") or {}
    if e.get("online_event") or address.get("country") != "US":
        return None
    return Event(
        name=e["name"]["text"].strip(),
        url=e["url"],
        kind=guess_kind(e["name"]["text"]),
        start=datetime.fromisoformat(e["start"]["local"]).date(),
        end=datetime.fromisoformat(e["end"]["local"]).date(),
        city=address.get("city") or "",
        state=address.get("region") or "",
        sources=["eventbrite"],
    )


def fetch(client: httpx.Client) -> list[Event]:
    token = os.environ.get("EVENTBRITE_TOKEN")
    organizers = load_config()["eventbrite"]["organizers"]
    if not token or not organizers:
        print("eventbrite: skipped (needs EVENTBRITE_TOKEN and organizers in config.toml)")
        return []

    events = []
    for organizer in organizers:
        params = {"status": "live", "order_by": "start_asc", "expand": "venue", "page_size": 50}
        while True:
            page = (
                client.get(
                    URL.format(organizer),
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                .raise_for_status()
                .json()
            )
            events += filter(None, map(to_event, page["events"]))
            if not page["pagination"].get("has_more_items"):
                break
            params["continuation"] = page["pagination"]["continuation"]
    return events
