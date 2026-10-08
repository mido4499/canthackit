"""Batch new events into a digest email, sent through Brevo (https://brevo.com)."""

import html
from datetime import date, timedelta
from email.utils import parseaddr

import httpx

from canthackit.models import Event

BREVO_CAMPAIGNS_URL = "https://api.brevo.com/v3/emailCampaigns"


def should_send(pending: list[Event], batch_size: int, max_wait_days: int, today: date) -> bool:
    """Send once enough events pile up, or when the oldest one has waited too long."""
    if not pending:
        return False
    oldest = min(e.first_seen for e in pending)
    return len(pending) >= batch_size or today - oldest >= timedelta(days=max_wait_days)


def _escape(s: str) -> str:
    # Brevo renders campaigns as templates, so braces in an event name could break the email.
    return html.escape(s).replace("{", "&#123;").replace("}", "&#125;")


def _when(e: Event) -> str:
    if e.start == e.end:
        return e.start.strftime("%b %d, %Y")
    return f"{e.start:%b %d} – {e.end:%b %d, %Y}"


# Brevo fills in {{ unsubscribe }} with a link that removes the subscriber from the list.
FOOTER = (
    '<p style="color:#888;font-size:12px">You subscribed to new event alerts from canthackit. '
    '<a href="{{ unsubscribe }}">Unsubscribe</a></p>'
)


def build_email(events: list[Event], site_url: str = "") -> dict[str, str]:
    """Return the digest's subject, plain-text body and HTML body.

    With `site_url`, the email links to the page listing every upcoming event.
    """
    events = sorted(events, key=lambda e: e.start)
    sections = [
        (title, [e for e in events if e.kind == kind])
        for title, kind in (
            ("Hackathons", "hackathon"),
            ("Conferences", "conference"),
            ("Meetups", "meetup"),
        )
    ]
    sections = [(title, evs) for title, evs in sections if evs]

    text = []
    body = []
    for title, evs in sections:
        text.append(
            f"{title}\n"
            + "\n".join(f"- {e.name} | {_when(e)} | {e.location or 'TBA'}\n  {e.url}" for e in evs)
        )
        rows = "".join(
            f'<tr><td><a href="{_escape(e.url)}">{_escape(e.name)}</a></td>'
            f"<td>{_when(e)}</td><td>{_escape(e.location or 'TBA')}</td></tr>"
            for e in evs
        )
        body.append(
            f"<h2>{title}</h2>"
            f'<table cellpadding="6" style="border-collapse:collapse">'
            f"<tr><th align=left>Event</th><th align=left>When</th><th align=left>Where</th></tr>"
            f"{rows}</table>"
        )

    if site_url:
        text.append(f"See all upcoming events: {site_url}")
        link = f'<a href="{_escape(site_url)}"><strong>See all upcoming events &rarr;</strong></a>'
        body.append(f"<p>{link}</p>")

    return {
        "subject": f"{len(events)} new in-person tech events in the US",
        "text": "\n\n".join(text),
        "html": f"<html><body>{''.join(body)}{FOOTER}</body></html>",
    }


def send(email: dict[str, str], sender: str, list_id: int, api_key: str) -> None:
    """Send `email` from `sender` ("Name <addr>", a Brevo-verified address) to a Brevo list.

    It goes out as a campaign, so Brevo adds the unsubscribe link and keeps the list private.
    """
    name, address = parseaddr(sender)
    headers = {"api-key": api_key}
    response = httpx.post(
        BREVO_CAMPAIGNS_URL,
        json={
            "name": f"canthackit digest {date.today()}",
            "subject": email["subject"],
            "sender": {"email": address, **({"name": name} if name else {})},
            "htmlContent": email["html"],
            "recipients": {"listIds": [list_id]},
        },
        headers=headers,
        timeout=30,
    )
    _check(response, "create the campaign")
    response = httpx.post(
        f"{BREVO_CAMPAIGNS_URL}/{response.json()['id']}/sendNow", headers=headers, timeout=30
    )
    _check(response, "send the campaign")


def _check(response: httpx.Response, action: str) -> None:
    if response.is_error:
        raise RuntimeError(f"Brevo couldn't {action} ({response.status_code}): {response.text}")
