from datetime import date, timedelta

from canthackit import readme
from canthackit.models import Event

TODAY = date(2026, 10, 13)


def ev(
    name, kind="hackathon", start=TODAY + timedelta(days=3), seen=TODAY, url="https://x.example"
):
    return Event(
        name=name,
        url=url,
        kind=kind,
        start=start,
        end=start,
        city="Austin",
        state="Texas",
        sources=["a"],
        first_seen=seen,
    )


def test_snapshot_counts_new_and_next_hackathons():
    events = [
        ev("Old hack", seen=TODAY - timedelta(days=30)),
        ev("New conf", kind="conference"),
        ev("Ended", start=TODAY - timedelta(days=2)),
    ]
    text = readme.snapshot(events, TODAY, "https://me.github.io/canthackit/")
    assert "**2 upcoming events**: 1 hackathons, 1 conferences and 0 meetups." in text
    assert "[Browse and filter all of them →](https://me.github.io/canthackit/)" in text
    assert "Just announced (1 this week)" in text and "| [New conf](https://x.example) |" in text
    assert "Next hackathons" in text and "[Old hack]" in text and "Ended" not in text


def test_snapshot_escapes_markdown_from_event_names():
    text = readme.snapshot([ev("A | B [beta] <x>")], TODAY, "")
    assert "A \\| B \\[beta\\] &lt;x>" in text


def test_update_replaces_only_between_markers(tmp_path):
    path = tmp_path / "README.md"
    path.write_text(f"# Title\n{readme.START}\nstale\n{readme.END}\nfooter\n")
    assert readme.update(path, [ev("Hack")], TODAY, "")
    text = path.read_text()
    assert text.startswith(f"# Title\n{readme.START}\n") and text.endswith(
        f"{readme.END}\nfooter\n"
    )
    assert "stale" not in text and "[Hack]" in text


def test_update_without_markers_leaves_file_alone(tmp_path):
    path = tmp_path / "README.md"
    path.write_text("# Title\n")
    assert not readme.update(path, [ev("Hack")], TODAY, "")
    assert path.read_text() == "# Title\n"


def test_new_events_list_hackathons_and_conferences_before_meetups():
    events = [ev("Meetup", kind="meetup", start=TODAY), ev("Conf", kind="conference")]
    text = readme.snapshot(events, TODAY, "")
    assert text.index("[Conf]") < text.index("[Meetup]")
