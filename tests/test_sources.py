import json
from datetime import date

import httpx

from canthackit.sources import dev_conferences, eventbrite, hackclub, luma, mlh
from canthackit.sources.devpost import parse_page


def client_returning(payload) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    )


def test_devpost_page_us_address():
    ld = {
        "@type": "Event",
        "startDate": "2026-09-22T18:00:00.000-04:00",
        "endDate": "2026-12-07T17:00:00.000-05:00",
        "location": {
            "address": {
                "addressLocality": "Philadelphia",
                "addressRegion": "Pennsylvania",
                "streetAddress": "3317 Chestnut St, Philadelphia, PA, USA",
            }
        },
    }
    page = f'<html><script type="application/ld+json">{json.dumps(ld)}</script></html>'
    assert parse_page(page) == {
        "start": ld["startDate"],
        "end": ld["endDate"],
        "city": "Philadelphia",
        "state": "Pennsylvania",
        "us": True,
    }


def test_devpost_page_non_us_and_missing():
    ld = {
        "@type": "Event",
        "startDate": "2026-11-07",
        "location": {"address": {"addressLocality": "Ottawa", "addressRegion": "Ontario"}},
    }
    page = f'<script type="application/ld+json">{json.dumps(ld)}</script>'
    assert parse_page(page)["us"] is False
    assert parse_page("<html>no data</html>") is None


def test_hackclub_keeps_us_in_person_only():
    base = {
        "website": "https://x",
        "start": "2027-01-09T08:00:00.000Z",
        "end": "2027-01-10T08:00:00.000Z",
        "city": "Sunnyvale",
        "state": "California",
    }
    payload = [
        {**base, "name": "Keep", "countryCode": "US", "virtual": False},
        {**base, "name": "Virtual", "countryCode": None, "virtual": True},
        {**base, "name": "Canada", "countryCode": "CA", "virtual": False},
    ]
    events = hackclub.fetch(client_returning(payload))
    assert [e.name for e in events] == ["Keep"]
    assert events[0].start == date(2027, 1, 9) and events[0].location == "Sunnyvale, California"


def test_dev_conferences_filters_country_status_and_past():
    future_ms = 4102444800000  # 2100-01-01
    payload = [
        {
            "name": "Keep",
            "hyperlink": "https://k",
            "date": [future_ms],
            "city": "Austin, TX",
            "country": "USA",
            "status": "open",
        },
        {
            "name": "Paris",
            "hyperlink": "https://p",
            "date": [future_ms],
            "country": "France",
            "status": "open",
        },
        {"name": "Old", "hyperlink": "https://o", "date": [0], "country": "USA", "status": "open"},
        {
            "name": "Moved online",
            "hyperlink": "https://v",
            "date": [future_ms],
            "country": "USA",
            "status": "Virtualized",
        },
    ]
    events = dev_conferences.fetch(client_returning(payload))
    assert [e.name for e in events] == ["Keep"]
    assert events[0].start == events[0].end == date(2100, 1, 1)


def test_mlh_keeps_us_in_person():
    base = {"startsAt": "2026-10-09T01:11:11Z", "endsAt": "2026-10-11T20:00:00Z", "url": "/e/x"}
    upcoming = [
        {
            **base,
            "name": "HackNC",
            "formatType": "physical",
            "websiteUrl": "https://hacknc.com/",
            "venueAddress": {"city": "Chapel Hill", "state": "North Carolina", "country": "US"},
        },
        {
            **base,
            "name": "Online",
            "formatType": "digital",
            "websiteUrl": "https://o",
            "venueAddress": {"country": "US"},
        },
        {
            **base,
            "name": "Canada",
            "formatType": "physical",
            "websiteUrl": "https://c",
            "venueAddress": {"country": "CA"},
        },
    ]
    data = json.dumps({"props": {"upcomingEvents": upcoming}})
    page = f'<script data-page="app" type="application/json">{data}</script>'
    events = mlh.parse_page(page)
    assert [e.name for e in events] == ["HackNC"]
    assert (
        events[0].start == date(2026, 10, 9) and events[0].location == "Chapel Hill, North Carolina"
    )


def test_luma_entry_filtering_and_urls():
    def entry(name, country="US", location_type="offline", url="slug"):
        return {
            "event": {
                "name": name,
                "url": url,
                "location_type": location_type,
                "start_at": "2026-10-07T00:00:00.000Z",
                "end_at": "2026-10-07T03:00:00.000Z",
                "geo_address_info": {
                    "city": "San Francisco",
                    "region": "California",
                    "country_code": country,
                },
            }
        }

    assert luma.to_event(entry("AI Night")).url == "https://luma.com/slug"
    assert luma.to_event(entry("AI Night")).kind == "meetup"
    assert luma.to_event(entry("Agent Hackathon")).kind == "hackathon"
    assert luma.to_event(entry("x", url="https://partiful.com/e/1", location_type=None)).url == (
        "https://partiful.com/e/1"
    )
    assert luma.to_event(entry("Zoom call", location_type="zoom")) is None
    assert luma.to_event(entry("Bucharest", country="RO")) is None


def test_eventbrite_skipped_without_token(monkeypatch):
    monkeypatch.delenv("EVENTBRITE_TOKEN", raising=False)
    assert eventbrite.fetch(client_returning({})) == []


def test_eventbrite_event_filtering():
    def ev(online=False, country="US"):
        return {
            "name": {"text": "Data Summit"},
            "url": "https://eb/1",
            "online_event": online,
            "start": {"local": "2026-11-03T09:00:00"},
            "end": {"local": "2026-11-04T17:00:00"},
            "venue": {"address": {"city": "Austin", "region": "TX", "country": country}},
        }

    event = eventbrite.to_event(ev())
    assert (event.kind, event.location, event.end) == (
        "conference",
        "Austin, TX",
        date(2026, 11, 4),
    )
    assert eventbrite.to_event(ev(online=True)) is None
    assert eventbrite.to_event(ev(country="CA")) is None
