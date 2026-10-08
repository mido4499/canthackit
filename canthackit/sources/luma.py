"""Luma community calendars: https://luma.com

Luma has no public search API, but calendar pages and their (undocumented) JSON endpoints are
public. Luma can't filter a city to tech events, so instead we follow tech calendars: the ones
listed in config.toml plus whatever Luma features on its Tech and AI category pages.
"""

import json
import re
import time
from datetime import datetime

import httpx

from canthackit import load_config
from canthackit.models import Event, guess_kind

API = "https://api2.luma.com"
CATEGORY_PAGES = ("https://luma.com/tech", "https://luma.com/ai")
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
MAX_PAGES_PER_CALENDAR = 5  # 50 events each


def featured_calendars(client: httpx.Client) -> list[str]:
    ids = []
    for url in CATEGORY_PAGES:
        page = client.get(url).raise_for_status().text
        data = json.loads(NEXT_DATA.search(page).group(1))["props"]["pageProps"]["initialData"]
        for key in ("featured_calendars", "timeline_calendars"):
            ids += [c["calendar"]["api_id"] for c in data["data"].get(key, [])]
    return ids


def calendar_id(client: httpx.Client, name: str) -> str:
    if name.startswith("cal-"):
        return name
    found = client.get(f"{API}/url", params={"url": name}).raise_for_status().json()
    return found["data"]["calendar"]["api_id"]


def to_event(entry: dict) -> Event | None:
    e = entry["event"]
    geo = e.get("geo_address_info") or {}
    # Events hosted elsewhere (e.g. Partiful) have no location_type but do have an address.
    if geo.get("country_code") != "US" or e.get("location_type") not in ("offline", None):
        return None
    url = e["url"] if e["url"].startswith("http") else f"https://luma.com/{e['url']}"
    return Event(
        name=e["name"].strip(),
        url=url,
        kind=guess_kind(e["name"]),
        start=datetime.fromisoformat(e["start_at"]).date(),
        end=datetime.fromisoformat(e.get("end_at") or e["start_at"]).date(),
        city=geo.get("city") or "",
        state=geo.get("region") or "",
        sources=["luma"],
    )


def calendar_events(client: httpx.Client, cal_id: str) -> list[Event]:
    events = []
    params = {"calendar_api_id": cal_id, "period": "future", "pagination_limit": 50}
    for _ in range(MAX_PAGES_PER_CALENDAR):
        page = client.get(f"{API}/calendar/get-items", params=params).raise_for_status().json()
        events += filter(None, map(to_event, page["entries"]))
        if not page.get("has_more"):
            break
        params["pagination_cursor"] = page["next_cursor"]
        time.sleep(0.5)
    return events


def fetch(client: httpx.Client) -> list[Event]:
    ids = featured_calendars(client)
    for name in load_config()["luma"]["calendars"]:
        try:
            ids.append(calendar_id(client, name))
        except httpx.HTTPStatusError as exc:
            print(f"luma: skipping calendar {name!r}: {exc.response.status_code}")

    events: dict[str, Event] = {}
    for cal_id in dict.fromkeys(ids):  # dedupe, keep order
        # One unreadable calendar (e.g. featured but "not launched yet") shouldn't sink the rest.
        try:
            calendar = calendar_events(client, cal_id)
        except httpx.HTTPStatusError as exc:
            print(f"luma: skipping calendar {cal_id}: {exc.response.text[:100]}")
            continue
        for event in calendar:
            events[event.url] = event  # the same event can be on several calendars
        time.sleep(0.5)
    return list(events.values())
