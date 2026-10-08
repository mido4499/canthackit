"""Each source module exposes `fetch(client) -> list[Event]` returning US in-person events.

To add a source, write a module with that function and register it below. Order matters a
little: when two sources list the same event, the stored copy keeps the first one's details.
"""

from collections.abc import Callable

import httpx

from canthackit.models import Event
from canthackit.sources import (
    confs_tech,
    dev_conferences,
    dev_events,
    devpost,
    eventbrite,
    hackclub,
    luma,
    mlh,
)

SOURCES: dict[str, Callable[[httpx.Client], list[Event]]] = {
    "mlh": mlh.fetch,
    "devpost": devpost.fetch,
    "hackclub": hackclub.fetch,
    "confs.tech": confs_tech.fetch,
    "developers.events": dev_conferences.fetch,
    "dev.events": dev_events.fetch,
    "luma": luma.fetch,
    "eventbrite": eventbrite.fetch,
}
