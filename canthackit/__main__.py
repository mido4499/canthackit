"""Fetch events from every source, store new ones, and email a digest when enough pile up.

Usage: python -m canthackit [--dry-run]
"""

import argparse
import json
import os
import sys
from datetime import date

import httpx

from canthackit import DATA_DIR, USER_AGENT
from canthackit.dedupe import merge
from canthackit.models import Event
from canthackit.notify import build_email, send, should_send
from canthackit.sources import SOURCES

EVENTS_FILE = DATA_DIR / "events.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the email instead of sending it, and don't update events.json",
    )
    args = parser.parse_args()
    today = date.today()

    state = (
        json.loads(EVENTS_FILE.read_text())
        if EVENTS_FILE.exists()
        else {"seeded_sources": [], "events": []}
    )
    # Sources that have returned events before. A source's first batch is stored silently,
    # so adding a source (or the very first run) doesn't email its whole backlog.
    seeded = set(state["seeded_sources"])
    known = [e for e in map(Event.model_validate, state["events"]) if e.end >= today]

    fetched: list[Event] = []
    failed: list[str] = []
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
        for name, fetch in SOURCES.items():
            try:
                events = fetch(client)
            except Exception as exc:  # one broken source shouldn't block the others
                print(f"{name}: FAILED: {exc!r}", file=sys.stderr)
                failed.append(name)
                continue
            print(f"{name}: {len(events)} US in-person events")
            fetched += events

    new = merge(known, [e for e in fetched if e.end >= today])
    print(f"{len(new)} new events, {len(known)} upcoming in total")

    first_batch = {s for e in fetched for s in e.sources} - seeded
    for e in new:
        if not seeded & set(e.sources):
            e.notified = True
    if first_batch:
        print(f"First events from {', '.join(sorted(first_batch))}: stored without emailing.")
    seeded |= first_batch

    pending = [e for e in known if not e.notified]
    batch_size = int(os.environ.get("BATCH_SIZE") or 10)
    max_wait = int(os.environ.get("MAX_WAIT_DAYS") or 7)
    if should_send(pending, batch_size, max_wait, today):
        list_id = os.environ.get("BREVO_LIST_ID", "")
        sender = os.environ.get("EMAIL_FROM", "")
        email = build_email(pending)
        if args.dry_run:
            print(email["text"])
        else:
            required = ("BREVO_LIST_ID", "EMAIL_FROM", "BREVO_API_KEY")
            if missing := [name for name in required if not os.environ.get(name)]:
                sys.exit(f"Can't send email: {', '.join(missing)} not set")
            send(email, sender, int(list_id), os.environ["BREVO_API_KEY"])
            print(f"Emailed {len(pending)} events to Brevo list {list_id}")
        for e in pending:
            e.notified = True
    else:
        print(f"{len(pending)} events waiting for the next email (batch size {batch_size})")

    if not args.dry_run:
        known.sort(key=lambda e: (e.start, e.name.lower()))
        state = {
            "seeded_sources": sorted(seeded),
            "events": [e.model_dump(mode="json") for e in known],
        }
        EVENTS_FILE.write_text(json.dumps(state, indent=1) + "\n")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
