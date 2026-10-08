from datetime import date

from canthackit.dedupe import merge, same_event
from canthackit.models import Event


def ev(name, start, url="https://x.example", city="", source="a", state=""):
    return Event(
        name=name,
        url=url,
        kind="hackathon",
        start=start,
        end=start,
        city=city,
        state=state,
        sources=[source],
    )


D = date(2026, 10, 17)


def test_same_name_different_year_suffix():
    assert same_event(ev("HackMIT 2026", D, url="https://a"), ev("HackMIT", D, url="https://b"))


def test_same_url_ignores_scheme_and_slash():
    a = ev("Blank Page", D, url="https://blankpage.devpost.com/")
    b = ev("Totally different", D, url="http://www.blankpage.devpost.com")
    assert same_event(a, b)


def test_dates_too_far_apart():
    assert not same_event(ev("HackMIT", D), ev("HackMIT", date(2026, 10, 20)))


def test_same_series_different_city():
    a = ev("DevFest", D, url="https://a", city="Boston")
    b = ev("DevFest", D, url="https://b", city="Austin")
    assert not same_event(a, b)


def test_city_with_state_suffix_matches():
    a = ev("KubeCon NA", D, url="https://a", city="New Orleans, LA")
    b = ev("KubeCon NA", D, url="https://b", city="New Orleans")
    assert same_event(a, b)


def test_merge_combines_sources_and_returns_only_new():
    known = [ev("Sierra Hacks", D, url="https://sierra", source="hackclub")]
    incoming = [
        ev("Sierra Hacks 2026", D, url="https://sierrahacks.devpost.com", source="devpost"),
        ev("Hyphen-Hacks", D, url="https://hyphen", source="devpost"),
    ]
    new = merge(known, incoming)
    assert [e.name for e in new] == ["Hyphen-Hacks"]
    assert known[0].sources == ["devpost", "hackclub"]
    assert len(known) == 2


def test_identical_names_merge_despite_metro_vs_suburb():
    a = ev("Atlanta Developers' Conference 2026", D, url="https://a", city="Alpharetta, GA")
    b = ev("Atlanta Developers' Conference 2026", D, url="https://b", city="Atlanta")
    assert same_event(a, b)


def test_identical_names_in_different_states_stay_separate():
    a = ev("Claude Code Meetup", D, url="https://a", city="Austin", state="TX")
    b = ev("Claude Code Meetup", D, url="https://b", city="Boston", state="Massachusetts")
    assert not same_event(a, b)


def test_same_state_overrides_city_mismatch():
    a = ev("Hack Knight", D, url="https://a", city="Flushing", state="New York")
    b = ev("Hack Knight Fall 2026", D, url="https://b", city="Queens", state="NY")
    assert same_event(a, b)
