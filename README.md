# canthackit

Get an email when new **in-person hackathons and tech conferences in the US** are announced.

A GitHub Actions job runs daily, pulls events from free public sources, removes duplicates,
and emails a digest once enough new events have piled up. Everything runs on GitHub's free
tier, with no servers or paid services.

## Sources

| Source | What | How |
|---|---|---|
| [MLH](https://www.mlh.com/seasons) | Student hackathons | Data embedded in the season page |
| [Devpost](https://devpost.com/hackathons) | Hackathons | Undocumented list API, plus each page's schema.org data for the address |
| [Hack Club](https://hackathons.hackclub.com) | Hackathons (mostly high school) | Public API |
| [confs.tech](https://github.com/tech-conferences/conference-data) | Conferences | Open JSON dataset |
| [developers.events](https://github.com/scraly/developers-conferences-agenda) | Conferences | Open JSON dataset |
| [dev.events](https://dev.events/NA/US) | Conferences | schema.org data on the US listing pages |
| [Luma](https://luma.com) | Meetups, hack nights, tech weeks | Public calendar data for calendars in `config.toml`, plus the ones Luma features under Tech and AI |
| [Eventbrite](https://www.eventbrite.com) | Events from chosen organizers | Official API; needs `EVENTBRITE_TOKEN` and organizers in `config.toml` |

Only events in the US with a physical location are kept. Online-only events are dropped.
When a source is added, its first batch of events is stored without emailing, so subscribers
only hear about events announced after that.

## How it works

1. Each module in `canthackit/sources/` returns events in one shared format (`canthackit/models.py`).
2. `canthackit/dedupe.py` merges the same event listed on several sites, using fuzzy name
   matching plus date and city.
3. New events are added to `data/events.json`, which is committed back to the repo.
4. An email goes out when there are at least `BATCH_SIZE` unsent events, or when the oldest
   unsent event has waited `MAX_WAIT_DAYS`.

The first run stores existing events without emailing, so you only hear about events
announced after you set it up.

## Setup

1. Fork or push this repo to GitHub.
2. Create a free [Brevo](https://www.brevo.com) account (300 emails/day). Then:
   - Add and verify the address you'll send from under **Senders, Domains & Dedicated IPs → Senders**.
     A plain Gmail address works; no domain needed.
   - Create an API key under **SMTP & API → API Keys**.
3. In **Settings → Secrets and variables → Actions**, add:

   | Secret | Example |
   |---|---|
   | `BREVO_API_KEY` | `xkeysib-...` |
   | `EMAIL_TO` | `alice@example.com,bob@example.com` |
   | `EVENTBRITE_TOKEN` (optional) | your [Eventbrite private token](https://www.eventbrite.com/platform/api-keys) |

   And under the *Variables* tab:

   | Variable | Example / default |
   |---|---|
   | `EMAIL_FROM` (required) | `canthackit <canthackit.alerts@gmail.com>`, the verified sender |
   | `BATCH_SIZE` | `10` |
   | `MAX_WAIT_DAYS` | `7` |

   Recipients are kept in a secret so their addresses aren't public, and each one gets their
   own copy of the email.

4. Run it once from **Actions → Update events → Run workflow** to seed `data/events.json`.

## Local development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv run python -m canthackit --dry-run   # fetch everything, print the email, change nothing
uv run pytest
uv run ruff check && uv run ruff format
```

## Following more Luma calendars or Eventbrite organizers

Edit `config.toml`. No code changes needed.

## Adding a source

Create `canthackit/sources/<name>.py` with a `fetch(client: httpx.Client) -> list[Event]`
function that returns only US in-person events. Then register it in
`canthackit/sources/__init__.py` and add a test in `tests/test_sources.py`.
