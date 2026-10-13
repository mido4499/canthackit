"""Keep an events snapshot in README.md, since GitHub can't run the events page there.

The daily run rewrites only the text between the START and END markers.
"""

from datetime import date, timedelta
from pathlib import Path

from canthackit.models import Event

START = "<!-- upcoming-events:start -->"
END = "<!-- upcoming-events:end -->"
ROWS = 10
NEW_DAYS = 7  # how long an event counts as "just announced"


def _cell(s: str) -> str:
    # Event names come from other sites, so keep them from breaking the Markdown table.
    for char, escaped in (("\\", "\\\\"), ("|", "\\|"), ("[", "\\["), ("]", "\\]"), ("<", "&lt;")):
        s = s.replace(char, escaped)
    return " ".join(s.split())


def _when(e: Event) -> str:
    """'Oct 16', 'Oct 12–24' or 'Oct 30–Nov 2', kept on one line in narrow table columns."""
    nbsp, dash = "\u00a0", "\u2060–\u2060"  # word joiners stop browsers breaking after the dash
    start = f"{e.start:%b}{nbsp}{e.start.day}"
    if e.start == e.end:
        return start
    if (e.start.year, e.start.month) == (e.end.year, e.end.month):
        return f"{start}{dash}{e.end.day}"
    return f"{start}{dash}{e.end:%b}{nbsp}{e.end.day}"


def _table(events: list[Event], with_kind: bool) -> str:
    head = "| Event | When | Where |" + (" Type |" if with_kind else "")
    rule = "|---|---|---|" + ("---|" if with_kind else "")
    rows = [
        f"| [{_cell(e.name)}]({e.url.replace(' ', '%20').replace(')', '%29')}) | {_when(e)} "
        f"| {_cell(e.location) or 'TBA'} |" + (f" {e.kind.capitalize()} |" if with_kind else "")
        for e in events[:ROWS]
    ]
    return "\n".join([head, rule, *rows])


def snapshot(events: list[Event], today: date, site_url: str) -> str:
    upcoming = sorted((e for e in events if e.end >= today), key=lambda e: (e.start, e.name))
    counts = {k: sum(e.kind == k for e in upcoming) for k in ("hackathon", "conference", "meetup")}
    # Meetups far outnumber the rest, so list new hackathons and conferences first.
    priority = {"hackathon": 0, "conference": 1, "meetup": 2}
    new = sorted(
        (e for e in upcoming if e.first_seen > today - timedelta(days=NEW_DAYS)),
        key=lambda e: priority[e.kind],
    )
    hackathons = [e for e in upcoming if e.kind == "hackathon" and e.start >= today]

    see_all = f"[Browse and filter all of them →]({site_url})" if site_url else ""
    parts = [
        f"**{len(upcoming)} upcoming events**: {counts['hackathon']} hackathons, "
        f"{counts['conference']} conferences and {counts['meetup']} meetups. {see_all}",
        f"<sub>Updated automatically every day. "
        f"Last update: {today:%B} {today.day}, {today.year}.</sub>",
    ]
    if new:
        parts += [f"### 🆕 Just announced ({len(new)} this week)", _table(new, with_kind=True)]
    if hackathons:
        parts += ["### 🏁 Next hackathons", _table(hackathons, with_kind=False)]
    return "\n\n".join(parts)


def update(path: Path, events: list[Event], today: date, site_url: str) -> bool:
    """Replace the snapshot in `path`. Returns False if the markers are missing."""
    text = path.read_text()
    start, end = text.find(START), text.find(END)
    if start == -1 or end < start:
        return False
    body = snapshot(events, today, site_url)
    path.write_text(f"{text[: start + len(START)]}\n{body}\n{text[end:]}")
    return True
