"""confs.tech open dataset: https://github.com/tech-conferences/conference-data

Conferences are split into one JSON file per topic per year, and the same conference
can appear under several topics.
"""

import os
from datetime import date

import httpx

from canthackit.models import Event

DIR_API = "https://api.github.com/repos/tech-conferences/conference-data/contents/conferences/{}"


def fetch(client: httpx.Client) -> list[Event]:
    # Unauthenticated GitHub API calls are limited to 60/hour per IP, which shared CI runners
    # can exhaust, so use the Actions token when available.
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    events: dict[tuple[str, str], Event] = {}
    this_year = date.today().year
    for year in (this_year, this_year + 1):
        listing = client.get(DIR_API.format(year), headers=headers)
        if listing.status_code == 404:  # next year's folder may not exist yet
            continue
        for file in listing.raise_for_status().json():
            for c in client.get(file["download_url"]).raise_for_status().json():
                # Online-only conferences have no country.
                if c.get("country") != "U.S.A.":
                    continue
                events[(c["url"], c["startDate"])] = Event(
                    name=c["name"].strip(),
                    url=c["url"],
                    kind="conference",
                    start=date.fromisoformat(c["startDate"]),
                    end=date.fromisoformat(c.get("endDate") or c["startDate"]),
                    city=c.get("city") or "",
                    sources=["confs.tech"],
                )
    return list(events.values())
