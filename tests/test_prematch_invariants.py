"""Section 5 invariants that already hold on the pre-match path, pinned
so they cannot regress (plan task 4.5; criteria P1, V6).

Read-only: these tests never write to the frozen log or predictions.
Immutability under refresh is pinned structurally — the frozen rows are
compared against the regenerated upcoming_predictions.csv, which the
refresh guard (predict_fixtures) must leave identical for locked
fixtures.
"""
import pandas as pd

FROZEN = "data/predictions/frozen_log.csv"
UPCOMING = "data/predictions/upcoming_predictions.csv"
PROB_COLS = ["p_team_1_win", "p_elo", "p_logistic_challenger"]


def test_probabilities_within_unit_interval():
    for path in (FROZEN, UPCOMING):
        df = pd.read_csv(path)
        for col in PROB_COLS:
            # missing stays missing (SIM shadow rows carry no
            # challenger value); every PRESENT value must be a
            # valid probability.
            assert df[col].dropna().between(0.0, 1.0).all(), (path, col)


def test_complementarity_by_construction():
    # One stored number per fixture: p(team_1) with p(team_2) = 1 - p.
    # The invariant that matters is that the stored value is a valid
    # probability for BOTH sides, i.e. strictly inside [0, 1] so the
    # complement is too.
    df = pd.read_csv(FROZEN)
    comp = 1.0 - df["p_team_1_win"]
    assert comp.between(0.0, 1.0).all()
    assert (df["p_team_1_win"] + comp).sub(1.0).abs().max() < 1e-12


def test_frozen_log_locks_are_unique():
    df = pd.read_csv(FROZEN)
    assert not df.duplicated(subset=["match_id", "stage"]).any()


def test_locked_fixtures_unchanged_in_regenerated_predictions():
    frozen = pd.read_csv(FROZEN)
    p1 = frozen[frozen.stage == "P1_preseason_expected_xi"]
    upcoming = pd.read_csv(UPCOMING).set_index("match_id")
    for _, row in p1.iterrows():
        assert row.match_id in upcoming.index
        assert abs(upcoming.loc[row.match_id, "p_team_1_win"]
                   - row.p_team_1_win) < 1e-9, row.match_id


def test_conflicts_register_surfaces_known_conflict():
    reg = pd.read_csv("data/conflicts_register.csv")
    assert (reg.conflict_id == "CONF-001").any()
    conf = reg[reg.conflict_id == "CONF-001"].iloc[0]
    assert "Kathmandu Gurkhas" in conf.value_b
    # Plan 1.2 (2026-10-29) resolved the served-layer split; the
    # register keeps the row WITH its resolution rather than going
    # silent. CONF-002 (canonical ID split) and CONF-003 (stored
    # overs) were still open then; both were resolved at the source
    # by the 2026-11-10 derived-tables refresh (commit d0426b8 —
    # the canonical layer now carries exactly 8 team IDs and stored
    # overs agree with the NRR derivation on all 152 innings), so
    # the register now records all three as RESOLVED and no row
    # stays open.
    assert "RESOLVED" in conf.status
    assert "sync_final_from_normalized" in conf.resolution
    for cid in ("CONF-002", "CONF-003"):
        row = reg[reg.conflict_id == cid]
        assert len(row) == 1, cid
        assert "RESOLVED 2026-11-10" in row.iloc[0]["status"], cid
    open_rows = reg[reg.status.str.contains("not resolved")]
    assert len(open_rows) == 0
