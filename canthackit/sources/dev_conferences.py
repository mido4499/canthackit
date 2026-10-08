"""Developers Conferences Agenda: https://github.com/scraly/developers-conferences-agenda"""

from datetime import UTC, date, datetime

import httpx

from canthackit.models import Event

URL = "https://developers.events/all-events.json"


def _date(ms: int) -> date:
    return datetime.fromtimestamp(ms / 1000, UTC).date()


def fetch(client: httpx.Client) -> list[Event]:
    today = date.today()
    return [
        Event(
            name=e["name"].strip(),
            url=e["hyperlink"],
            kind="conference",
            start=_date(e["date"][0]),
            end=_date(e["date"][-1]),
            city=e.get("city") or "",  # already includes the state, e.g. "Austin, TX"
            sources=["developers.events"],
        )
        for e in client.get(URL).raise_for_status().json()
        if e.get("country") == "USA"
        and e.get("status") == "open"
        and _date(e["date"][-1]) >= today  # the file goes back years
    ]
