from datetime import date, timedelta

import httpx
import pytest

from canthackit.models import Event
from canthackit.notify import build_email, send, should_send

TODAY = date(2026, 10, 6)


def ev(name, kind="hackathon", seen=TODAY):
    return Event(
        name=name,
        url="https://x.example",
        kind=kind,
        start=date(2026, 11, 1),
        end=date(2026, 11, 2),
        city="Austin",
        state="Texas",
        sources=["a"],
        first_seen=seen,
    )


def test_nothing_pending():
    assert not should_send([], batch_size=10, max_wait_days=7, today=TODAY)


def test_waits_for_batch():
    assert not should_send([ev("a")] * 9, batch_size=10, max_wait_days=7, today=TODAY)
    assert should_send([ev("a")] * 10, batch_size=10, max_wait_days=7, today=TODAY)


def test_sends_small_batch_after_max_wait():
    stale = ev("a", seen=TODAY - timedelta(days=7))
    assert should_send([stale], batch_size=10, max_wait_days=7, today=TODAY)


def test_email_groups_kinds_and_escapes_html():
    email = build_email([ev("<Hack>"), ev("PyCon", kind="conference")])
    assert email["subject"] == "2 new in-person tech events in the US"
    assert "Hackathons" in email["text"] and "Conferences" in email["text"]
    assert "Austin, Texas" in email["text"]
    assert "&lt;Hack&gt;" in email["html"]


def test_send_one_version_per_recipient(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append((json, headers))
        return httpx.Response(201, json={"messageId": "<1>"})

    monkeypatch.setattr(httpx, "post", fake_post)
    email = {"subject": "s", "text": "t", "html": "h"}
    send(email, "canthackit <bot@gmail.com>", ["a@x.com", "b@x.com"], "xkeysib-key")
    ((body, headers),) = calls
    assert body["sender"] == {"email": "bot@gmail.com", "name": "canthackit"}
    assert body["messageVersions"] == [
        {"to": [{"email": "a@x.com"}]},
        {"to": [{"email": "b@x.com"}]},
    ]
    assert (body["subject"], body["textContent"], body["htmlContent"]) == ("s", "t", "h")
    assert headers == {"api-key": "xkeysib-key"}


def test_send_raises_on_brevo_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(401, text="unauthorized"))
    with pytest.raises(RuntimeError, match="401"):
        send({"subject": "s", "text": "t", "html": "h"}, "bot@gmail.com", ["a@x.com"], "key")
