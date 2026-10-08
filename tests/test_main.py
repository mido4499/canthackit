import json
import sys
from datetime import date, timedelta

import pytest

import canthackit.__main__ as app
from canthackit.models import Event

SOON = date.today() + timedelta(days=30)


def ev(name, source):
    return Event(
        name=name, url=f"https://{name}", kind="meetup", start=SOON, end=SOON, sources=[source]
    )


@pytest.fixture
def run(tmp_path, monkeypatch):
    """Run main() against fake sources with a temporary data file; return what was emailed."""
    monkeypatch.setattr(app, "EVENTS_FILE", tmp_path / "events.json")
    monkeypatch.setattr(sys, "argv", ["canthackit"])
    monkeypatch.setenv("BATCH_SIZE", "1")
    monkeypatch.setenv("BREVO_LIST_ID", "2")
    monkeypatch.setenv("EMAIL_FROM", "bot@x.com")
    monkeypatch.setenv("BREVO_API_KEY", "key")
    sent = []
    monkeypatch.setattr(app, "send", lambda email, *a: sent.append(email))

    def _run(sources):
        monkeypatch.setattr(
            app, "SOURCES", {n: (lambda c, evs=evs: evs) for n, evs in sources.items()}
        )
        sent.clear()
        assert app.main() == 0
        return sent[:]

    return _run


def test_new_source_backlog_is_not_emailed(run):
    assert run({"a": [ev("one", "a")]}) == []  # very first run: silent
    assert (
        run({"a": [ev("one", "a")], "b": [ev("two", "b")]}) == []
    )  # source b's first batch: silent
    emailed = run({"a": [ev("one", "a"), ev("three", "a")], "b": [ev("two", "b")]})
    assert len(emailed) == 1 and "three" in emailed[0]["text"]


def test_source_with_no_events_is_not_seeded(run):
    run({"a": [ev("one", "a")], "b": []})
    assert json.loads(app.EVENTS_FILE.read_text())["seeded_sources"] == ["a"]
    assert run({"a": [ev("one", "a")], "b": [ev("two", "b")]}) == []  # b's first real batch
