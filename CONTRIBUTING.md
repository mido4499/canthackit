# Contributing to canthackit

Thanks for helping students and job seekers find their next event! This guide gets you from
zero to an open pull request. You don't need any accounts or API keys to work on canthackit
locally. Everything except sending email runs without them.

**Contents**
[Ways to help](#ways-to-help) ·
[Set up your copy](#set-up-your-copy) ·
[Make a change](#make-a-change) ·
[How the code is organized](#how-the-code-is-organized) ·
[Adding a new source](#adding-a-new-source) ·
[Known limitations](#known-limitations) ·
[Ground rules](#ground-rules)

## Ways to help

| Effort | Contribution |
|---|---|
| 5 minutes, no code | **Follow a Luma calendar.** Add its name to [`config.toml`](config.toml) and open a pull request. You can do this entirely on github.com with the ✏️ edit button. |
| 5 minutes, no code | **Report a problem.** [Open an issue](https://github.com/mido4499/canthackit/issues/new) for an event that's missing, duplicated, in the wrong place or filed under the wrong type. Include its link. |
| An afternoon | **Add a source**, a site that lists US hackathons, conferences or meetups. See [Adding a new source](#adding-a-new-source). |
| A weekend | **Fix a [known limitation](#known-limitations).** |

If you plan something bigger than a small fix, open an issue first so we can agree on the
approach before you put in the time.

## Set up your copy

You need [Git](https://git-scm.com/downloads), a [GitHub account](https://github.com/signup)
and [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs the right
Python version for you.

### 1. Fork the repo

Click **Fork** at the top right of
[github.com/mido4499/canthackit](https://github.com/mido4499/canthackit). This gives you your
own copy on GitHub, which you can push to freely.

### 2. Clone your fork

```sh
git clone https://github.com/<your-username>/canthackit.git
cd canthackit
```

### 3. Connect it to the original repo

This lets you pull in other people's changes later.

```sh
git remote add upstream https://github.com/mido4499/canthackit.git
git remote -v   # origin = your fork, upstream = the original
```

### 4. Install and check that everything works

```sh
uv sync                                  # installs Python and the dependencies
uv run pytest                            # runs the tests (a second or two, no network)
uv run python -m canthackit --dry-run    # fetches every live source and prints the email
```

`--dry-run` fetches from the real sites and prints the digest it would send, without sending
anything or touching `data/events.json`. Expect it to take a minute or two. Always use it
locally: without it, the script rewrites `data/events.json`. It does refresh Devpost's cache,
`data/devpost_cache.json`, so discard that afterward with
`git checkout data/devpost_cache.json`.

To preview the events page:

```sh
python3 -m http.server 8000
# open http://localhost:8000/site/
```

## Make a change

1. **Sync with the original and create a branch** named after what you're doing:

   ```sh
   git switch main
   git pull upstream main
   git switch -c add-acm-source
   ```

2. **Make your change**, and add or update a test in `tests/` if you touched Python.

3. **Run the same checks CI runs** on every pull request:

   ```sh
   uv run ruff format            # auto-formats your code
   uv run ruff check             # lint
   uv run pytest                 # tests
   ```

4. **Commit and push to your fork:**

   ```sh
   git add -A
   git commit -m "Add ACM hackathons as a source"
   git push -u origin add-acm-source
   ```

5. **Open a pull request.** GitHub shows a **Compare & pull request** button on your fork
   right after you push. Say what you changed and why. For a new source, paste the
   `--dry-run` line showing how many events it found.

Don't include changes to `data/events.json` or `data/devpost_cache.json`. The daily job owns
those files.

Your fork won't run the daily job or send email. GitHub turns off scheduled workflows on
forks, and forks don't get this repo's secrets. If you want your own running instance, see
[Run your own copy](README.md#run-your-own-copy).

## How the code is organized

```
canthackit/
├── __main__.py        # the daily run: fetch → dedupe → save → maybe email
├── models.py          # Event, the shared format every source returns, and guess_kind()
├── sources/           # one module per site, each with fetch(client) -> list[Event]
│   └── __init__.py    # the SOURCES registry
├── dedupe.py          # decides whether two listings are the same event
├── notify.py          # builds the digest and sends it through Brevo
└── us.py              # US state names and abbreviations
site/index.html        # the events page: plain HTML, CSS and JavaScript, no build step
config.toml            # Luma calendars and Eventbrite organizers to follow
data/events.json       # every upcoming event; written by the daily job
tests/                 # pytest; network calls are mocked
.github/workflows/     # CI, the daily job, and the Pages deploy
```

## Adding a new source

A source is one module in `canthackit/sources/` with a `fetch` function. Here's
[`hackclub.py`](canthackit/sources/hackclub.py), the simplest one, in full:

```python
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
```

**The contract:**
- **Return only US events with a physical location.** Drop online-only events. Hybrid ones
  are fine.
- **Use the `client` you're given** for every request. It already sets canthackit's user
  agent and a timeout.
- **Raise on failure** (`raise_for_status()`) instead of returning an empty list. The run
  catches it, reports the source as failed and carries on with the others.
- **Set `kind`** to `"hackathon"`, `"conference"` or `"meetup"`. If a site mixes types, use
  `guess_kind(name)` from `models.py`.
- **Prefer official APIs, open datasets and schema.org data** over scraping page layouts, which
  break whenever a site is redesigned.

**Then:**
1. **Register it** in [`canthackit/sources/__init__.py`](canthackit/sources/__init__.py).
2. **Add a test** in [`tests/test_sources.py`](tests/test_sources.py) that feeds it a small,
   fake response, using `client_returning(...)` or `httpx.MockTransport`, and checks that
   only the US in-person events come back. Tests must never call the real site.
3. **Add a row** to the sources table in the [README](README.md#where-the-events-come-from).

Don't worry about the first run flooding subscribers: a new source's first batch is stored
without emailing.

## Known limitations

These are real gaps, roughly from most to least impactful. Comment on or open an issue
before starting one, so two people don't do the same work.

1. **Locations are messy in the email.** Sources disagree on format: "Austin" + "Texas",
   "Austin, TX", "TX", a state name in the city field, or no state at all. The events page
   cleans this up in JavaScript (`normalize()` in `site/index.html`), but the email shows the
   raw values, like "Reston" with no state or "San Juan, San Juan". The fix is to do this
   cleanup once in Python, in `us.py` or as each `Event` is created, so both the page and the
   email get clean data.
2. **The event type is guessed from the name.** For Luma and Eventbrite, `guess_kind()` only
   looks for words like "hackathon" or "summit", so plenty of talks and happy hours end up as
   "conference" and some hackathons as "meetup". Better signals, like a source's own
   categories or keyword lists, would make the filters more trustworthy.
3. **dev.events blocks GitHub's servers.** It was the biggest conference source, but it
   returns 403 to GitHub Actions, so it was removed. If you find an official API, feed or
   another sanctioned way to get the data, it could come back. Please don't try to get
   around the block.
4. **One broken source fails the whole run.** The other sources still get saved, but the job
   goes red. Sites change their pages without warning, so it'd help to separate "a source is
   temporarily down" from "something's really wrong", for example a source failing several
   days in a row.
5. **Luma adds a lot of noise.** About half of all events come from Luma, many of them happy
   hours during tech weeks. Ideas welcome: a quality filter, per-type limits, or
   letting subscribers choose.
6. **Everyone gets the same digest.** Subscribers can't choose their state or event types. Brevo
   contacts support custom attributes, so the form could ask, and the digest could be split
   by preference.
7. **The page could do more.** For example: a text search, a "new this week" badge (each
   event already has `first_seen`), a way to add an event to your calendar (.ics), or
   remembering filters in the URL so you can share a filtered view.
8. **Deduplication isn't perfect.** `dedupe.py` uses fuzzy name matching plus dates and
   places. Real duplicates that slip through, or different events that get merged, are
   great test cases. Add them to `tests/test_dedupe.py`.
9. **There are no tests for the page.** `site/index.html` has real logic (filters, date
   ranges, location cleanup) and no automated tests.
10. **Eventbrite is off.** The integration exists but follows no organizers yet. Adding
    good US tech organizers to `config.toml` would turn it on, though running it needs an
    `EVENTBRITE_TOKEN` secret.

## Ground rules

- **Be a polite guest on other people's sites.** canthackit fetches each source once a day,
  with an honest user agent. Don't add tight loops, parallel request floods, or anything that
  disguises the client or gets around blocks or rate limits.
- **Never commit secrets.** API keys go in `.env` locally (it's gitignored) or in GitHub
  secrets.
- **Keep it free to run.** No servers, databases or paid services. The project's main
  advantage is that anyone can fork it and run it on GitHub's free tier.
- **Be kind** in issues and reviews. Lots of contributors here are students opening their
  first pull request.
