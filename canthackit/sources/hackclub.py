"""Hack Club's public hackathon directory: https://hackathons.hackclub.com"""

from datetime import datetime

import httpx

from canthackit.models import Event

URL = "https://hackathons.hackclub.com/api/events/upcoming/"


def fetch(client: httpx.Client) -> list[Event]:
    return [
        Event(
            name=e["name"].strip(),
            url=e["website"],
            kind="hackathon",
            start=datetime.fromisoformat(e["start"]).date(),
            end=datetime.fromisoformat(e["end"]).date(),
            city=e.get("city") or "",
            state=e.get("state") or "",
            sources=["hackclub"],
        )
        for e in client.get(URL).raise_for_status().json()
        if e.get("countryCode") == "US" and not e.get("virtual")
    ]
