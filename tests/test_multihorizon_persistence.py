"""Multi-horizon detector: distinguish emerging, supported and fluky changes."""
from datetime import date,timedelta
from prehype.early_radar import change_signal,compare_window
from prehype.sources.milb import MilbBatter

NOW=date(2026,11,10)

def batter():
    return MilbBatter(player_id="99",name="Long Window Prospect",level="AA",
                      age=20,pa=440,ops=.790,bb_rate=.12,k_rate=.19,hr=9)

def series(chunks, *, team_change_at=None):
    """One 14-game chunk per tuple (strikeouts, walks, doubles, at bats)."""
    out=[]
    start=date(2026,4,1)
    for ci,(ks,walks,dbl,ab) in enumerate(chunks):
        for day in range(14):
            out.append({
                "date":(start+timedelta(days=ci*14+day)).isoformat(),
                "game":10000+ci*14+day,
                "team":"700" if team_change_at is not None and ci>=team_change_at else "500",
                "pa":ab+walks, "ab":ab,
                "h":max(2,dbl), "dbl":dbl,"trp":0,"hr":0,
                "bb":walks,"k":ks,"hbp":0,"sf":0,
            })
    return out

def sustained():
    return series([
        (2,0,0,4),(2,0,0,4),(2,0,0,4),
        (2,0,0,4),(1,1,1,4),(0,2,2,4),
    ])

def short_spike():
    return series([
        (0,2,2,4),(0,2,2,4), # earlier 28: good skills
        (2,0,0,4), (0,2,2,4), # last 28: fake improvement at tail
    ])

def test_true_multihorizon_persistent_signal():
    row=change_signal(batter(),sustained(),NOW)
    assert row
    assert row["evidence_tier"]=="SUSTAINED_ACROSS_14_28_42"
    assert row["max_comparison_games"]==84
    for n in (14,28,42):
        comp=row["comparisons"][str(n)]
        assert comp["status"]=="AVAILABLE"
        assert comp["confirmed"]
        assert comp["old"]["games"]==n
        assert comp["new"]["games"]==n
        assert comp["delta"]["K"]<0
        assert comp["delta"]["ISO"]>0
        assert comp["direction_support"]["K"]>=.75
    assert "Nested" in row["comparisons"]["14"]["note"]


def test_28_game_improvement_without_84_game_history_is_building():
    row=change_signal(batter(),sustained()[28:],NOW)
    assert row
    assert row["comparisons"]["14"]["status"]=="AVAILABLE"
    assert row["comparisons"]["28"]["confirmed"]
    assert row["comparisons"]["42"]["status"]=="INSUFFICIENT_GAMES"
    assert row["evidence_tier"]=="BUILDING_14_AND_28"


def test_short_spike_is_not_mistaken_for_sustained_breakout():
    row=change_signal(batter(),short_spike(),NOW)
    assert row
    assert row["comparisons"]["14"]["confirmed"]
    assert row["comparisons"]["28"]["status"]=="AVAILABLE"
    assert not row["comparisons"]["28"]["confirmed"]
    assert row["evidence_tier"]=="SHORT_SPIKE_NOT_CONFIRMED"
    assert "NOT confirmed" in row["reason"]


def test_28_game_insufficient_is_unconfirmed_not_a_fluke_label():
    row=change_signal(batter(),sustained()[-28:],NOW)
    assert row
    assert row["evidence_tier"]=="EARLY_14_ONLY"
    assert row["comparisons"]["28"]["status"]=="INSUFFICIENT_GAMES"
    assert "NOT yet confirmed" in row["reason"]


def test_longer_windows_must_not_mix_promoted_team_stints():
    logs=series([
        (2,0,0,4),(2,0,0,4),(2,0,0,4),
        (2,0,0,4),(1,1,1,4),(0,2,2,4),
    ],team_change_at=2)
    row=change_signal(batter(),logs,NOW)
    assert row
    assert row["comparisons"]["14"]["status"]=="AVAILABLE"
    assert row["comparisons"]["28"]["status"]=="AVAILABLE"
    assert row["comparisons"]["42"]["status"]=="TEAM_CHANGE"
    assert row["evidence_tier"]=="BUILDING_14_AND_28"


def test_deterministic_sampling_and_different_players_do_not_use_future_games():
    rows=sustained()
    signal1=change_signal(batter(),rows,NOW)
    signal2=change_signal(batter(),rows,NOW)
    assert signal1["comparisons"]==signal2["comparisons"]
    # Leak check: as_of before the most recent 14 means the visible signal
    # must be computed ONLY on games already played.
    early=date.fromisoformat(rows[-20]["date"])
    leaked=change_signal(batter(),rows,early)
    assert leaked is None or leaked["last_game"]<=early.isoformat()


def test_uncertainty_weakly_supports_a_tiny_sample_not_a_breakout_probability():
    tiny=series([(2,0,0,4),(0,2,2,4)])
    row=change_signal(batter(),tiny,NOW)
    assert row
    assert row["sample_warning"]
    assert "NOT a calibrated" in row["comparisons"]["14"]["note"]
    support=row["comparisons"]["14"]["direction_support"]
    assert all(0<=v<=1 for v in support.values())
    assert "future-breakout" in row["sample_warning"].lower() or "future" in row["sample_warning"].lower()
