from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Event(BaseModel):
    """One in-person event, normalized across all sources."""

    name: str
    url: str
    kind: Literal["hackathon", "conference", "meetup"]
    start: date
    end: date
    city: str = ""
    state: str = ""
    sources: list[str]
    first_seen: date = Field(default_factory=date.today)
    notified: bool = False

    @property
    def location(self) -> str:
        return ", ".join(p for p in (self.city, self.state) if p)


def guess_kind(name: str) -> str:
    """For sources that mix event types (Luma, Eventbrite), classify by name."""
    lowered = name.lower()
    if "hackathon" in lowered or "buildathon" in lowered:
        return "hackathon"
    if any(w in lowered for w in ("conference", "summit", "conf ", "symposium", "expo")):
        return "conference"
    return "meetup"
