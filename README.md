<div align="center">

# Kan't Hack It

**In-person hackathons, tech conferences and meetups across the US, in one place.**<br>
Checked every day. Emailed to you only when something new shows up.

### [→ Browse upcoming events](https://mido4499.github.io/canthackit/)

[Get the email digest](https://mido4499.github.io/canthackit/#subscribe) ·
[Contribute](CONTRIBUTING.md) ·
[How it works](#how-it-works)

[![Upcoming events](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fmido4499.github.io%2Fcanthackit%2Fevents.json&query=%24.events.length&label=upcoming%20events&color=2563eb)](https://mido4499.github.io/canthackit/)
[![Update events](https://github.com/mido4499/canthackit/actions/workflows/update-events.yml/badge.svg)](https://github.com/mido4499/canthackit/actions/workflows/update-events.yml)
[![CI](https://github.com/mido4499/canthackit/actions/workflows/ci.yml/badge.svg)](https://github.com/mido4499/canthackit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

</div>

---

## Built for you if you're…

- 🎓 **A tech undergrad or grad student** hunting for hackathons to build projects, win
  prizes and get noticed by sponsors.
- 💼 **Looking for a tech job** and want to meet engineers, founders and recruiters in person.

No more checking ten websites. Kan't Hack It checks them for you.

## What you get

- 🗺️ **[A live events page](https://mido4499.github.io/canthackit/)** listing every upcoming
  event, filterable by type, state, city and date.
- 📬 **[An email digest](https://mido4499.github.io/canthackit/#subscribe)** with only the
  events announced since your last email.

**How often:** new events are fetched every morning around 13:00 UTC (8–9 AM Eastern). You get an
email at most once a day, and only when there's news: once 10 new events have piled up, or
a week after the first new one, whichever comes first. Unsubscribe from any email in one
click.

Only in-person events in the US are included. Online-only events are left out on purpose.

## Where the events come from

| Source | What it adds |
|---|---|
| [MLH](https://www.mlh.com/seasons) | The official student hackathon season |
| [Devpost](https://devpost.com/hackathons) | Hackathons of every size, including company-run ones |
| [Hack Club](https://hackathons.hackclub.com) | Hackathons, mostly for high schoolers |
| [confs.tech](https://github.com/tech-conferences/conference-data) | Developer conferences (open dataset) |
| [developers.events](https://github.com/scraly/developers-conferences-agenda) | Developer conferences (open dataset) |
| [Luma](https://luma.com) | Meetups, hack nights and tech weeks from [followed calendars](config.toml), plus the ones Luma features under Tech and AI |
| [Eventbrite](https://www.eventbrite.com) | Events from chosen organizers (off until organizers are added to [`config.toml`](config.toml)) |

When the same event is listed on several sites, it shows up once.

Know a source that's missing? [Adding one](CONTRIBUTING.md#adding-a-new-source) takes a
single Python file.

## How it works

```
 MLH · Devpost · Hack Club · confs.tech · developers.events · Luma · Eventbrite
                                   │
                                   ▼
        canthackit/sources/   each returns US in-person events in one shared format
                                   │
                                   ▼
        canthackit/dedupe.py  merges the same event listed on several sites
                                   │
                                   ▼
        data/events.json      every upcoming event, committed back to this repo
                 │                                   │
                 ▼                                   ▼
        site/ → GitHub Pages                Brevo email digest
        (the events page)                   (new events only)
```

A GitHub Actions job runs this every day at 13:00 UTC. The repo is the database, so there are
no servers to run or pay for. New events are batched into a digest ([how often](#what-you-get))
so you get a useful email instead of a daily trickle.

## Contributing

Contributions are very welcome, and many don't need much code. Some of the most useful ones:

- **Follow a new Luma calendar** by adding one line to [`config.toml`](config.toml).
- **Add a source** for a site that lists hackathons or conferences.
- **Tackle a [known limitation](CONTRIBUTING.md#known-limitations)**, like messy locations in
  the email or events filed under the wrong type.

👉 **[CONTRIBUTING.md](CONTRIBUTING.md)** walks you through forking, running it locally
(no accounts or API keys needed) and opening your first pull request.

## Run your own copy

<details>
<summary>Want alerts for a different focus, or to send them to your own group? Here's how to set up your own instance.</summary>

<br>

1. **Fork this repo**, and keep it public, since free GitHub Pages needs that.
2. **Create a free [Brevo](https://www.brevo.com) account** (300 emails a day). Then:
   - Add and verify a sender under **Senders, Domains & Dedicated IPs**. A custom domain you
     authenticate there (DKIM and DMARC) keeps the digest out of spam far better than a Gmail
     address.
   - Create an API key under **SMTP & API → API Keys**.
   - Fill in your organization's name and postal address under **Settings → Company details**.
     Brevo puts them in every campaign's footer, as anti-spam law requires.
   - Create a list for subscribers under **Contacts → Lists**, and note its ID.
   - Create a subscription form for that list under **Contacts → Forms**, with double opt-in
     on, and put its `action` URL in the subscribe form in [`site/index.html`](site/index.html).
3. **In your fork, go to Settings → Secrets and variables → Actions.**

   | Secrets tab | Example |
   |---|---|
   | `BREVO_API_KEY` | `xkeysib-...` |
   | `EVENTBRITE_TOKEN` (optional) | your [Eventbrite private token](https://www.eventbrite.com/platform/api-keys) |

   | Variables tab | Example / default |
   |---|---|
   | `EMAIL_FROM` (required) | `Kan't Hack It <alerts@yourdomain.com>`, your verified sender |
   | `BREVO_LIST_ID` (required) | `2`, your subscriber list |
   | `BATCH_SIZE` | `10` |
   | `MAX_WAIT_DAYS` | `7` |

4. **Under Settings → Pages**, set the source to **GitHub Actions**.
5. **Run Actions → Update events → Run workflow.** The first run stores existing events
   without emailing, so subscribers only hear about events announced after that. When it
   finishes, *Publish site* puts the page at `https://<you>.github.io/<repo>/`, and the
   digest links to it automatically.

</details>

## License

[MIT](LICENSE). Use it, fork it, make it yours.
