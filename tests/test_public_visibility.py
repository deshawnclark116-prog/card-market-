"""Public prospect rank is a veto, NEVER proof that a missing name is unhyped."""
from prehype.sources.public_visibility import (
    extract_ranked_text,public_top100_flags,
)
MOCK="""<html><body><h1>MLB Pipeline Top 100 Prospects 2026</h1>
<a href='/one'>#1 Jesus Made Brewers SS AA $200</a>
<a href='/walker'>#15 Walker Jenkins Twins CF MLB $85</a>
<a href='/lazaro'>#53 Lazaro Montes Mariners RF MLB $61</a>
<a href='/edward'>#32 Edward Florentino Pirates CF A+ $72</a>
<h2>Ranked but omitted (no 1st CPA on market)</h2></body></html>"""


def test_top100_positive_evidence_filters_already_famous_names():
    values,ok=public_top100_flags([
        "Walker Jenkins","Lazaro Montes","Edward Florentino",
        "Sebastian Dos Santos"],loader=lambda:MOCK)
    assert ok
    assert values["Walker Jenkins"] is True
    assert values["Lazaro Montes"] is True
    assert values["Edward Florentino"] is True
    assert values["Sebastian Dos Santos"] is False


def test_unknown_rankings_are_not_proof_of_low_collector_hype():
    empty,ok=public_top100_flags(["Walker Jenkins"],loader=lambda:"")
    assert not ok
    assert empty["Walker Jenkins"] is None


def test_name_match_requires_full_player_identity():
    flags,ok=public_top100_flags(["Walker Jen","Lazaro Mon"],
        loader=lambda:MOCK)
    assert ok
    assert not any(flags.values())


def test_names_in_nonranked_section_do_not_count():
    page=MOCK.replace("Ranked but omitted", "Ranked but omitted")+"<p>Random Obscure Player</p>"
    flags,ok=public_top100_flags(["Random Obscure Player"],loader=lambda:page)
    assert ok and flags["Random Obscure Player"] is False
