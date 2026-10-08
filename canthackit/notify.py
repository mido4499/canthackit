"""Batch new events into a digest email, sent through Brevo (https://brevo.com)."""

import html
from datetime import date, timedelta
from email.utils import parseaddr

import httpx

from canthackit.models import Event

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
MAX_RECIPIENTS_PER_REQUEST = 2000  # Brevo's limit for messageVersions


def should_send(pending: list[Event], batch_size: int, max_wait_days: int, today: date) -> bool:
    """Send once enough events pile up, or when the oldest one has waited too long."""
    if not pending:
        return False
    oldest = min(e.first_seen for e in pending)
    return len(pending) >= batch_size or today - oldest >= timedelta(days=max_wait_days)


def _when(e: Event) -> str:
    if e.start == e.end:
        return e.start.strftime("%b %d, %Y")
    return f"{e.start:%b %d} – {e.end:%b %d, %Y}"


def build_email(events: list[Event]) -> dict[str, str]:
    """Return the digest's subject, plain-text body and HTML body."""
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
            f'<tr><td><a href="{html.escape(e.url)}">{html.escape(e.name)}</a></td>'
            f"<td>{_when(e)}</td><td>{html.escape(e.location or 'TBA')}</td></tr>"
            for e in evs
        )
        body.append(
            f"<h2>{title}</h2>"
            f'<table cellpadding="6" style="border-collapse:collapse">'
            f"<tr><th align=left>Event</th><th align=left>When</th><th align=left>Where</th></tr>"
            f"{rows}</table>"
        )

    return {
        "subject": f"{len(events)} new in-person tech events in the US",
        "text": "\n\n".join(text),
        "html": f"<html><body>{''.join(body)}</body></html>",
    }


def send(email: dict[str, str], sender: str, recipients: list[str], api_key: str) -> None:
    """Send `email` from `sender` ("Name <addr>", a Brevo-verified address) to each recipient."""
    name, address = parseaddr(sender)
    for i in range(0, len(recipients), MAX_RECIPIENTS_PER_REQUEST):
        chunk = recipients[i : i + MAX_RECIPIENTS_PER_REQUEST]
        response = httpx.post(
            BREVO_URL,
            json={
                "sender": {"email": address, **({"name": name} if name else {})},
                "subject": email["subject"],
                "textContent": email["text"],
                "htmlContent": email["html"],
                # One version per recipient, so nobody sees the other addresses.
                "messageVersions": [{"to": [{"email": r}]} for r in chunk],
            },
            headers={"api-key": api_key},
            timeout=30,
        )
        if response.is_error:
            raise RuntimeError(
                f"Brevo rejected the email ({response.status_code}): {response.text}"
            )
