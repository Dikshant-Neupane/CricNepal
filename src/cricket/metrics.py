"""Cricket arithmetic: the exact definitions of master prompt Section 4.

This module is the ONLY implementation of these definitions in the
project. Every function states its formula; undefined cases return
None (never a silent zero, never a division by zero). Pure functions
over plain delivery records (mappings with runs_off_bat, runs_extras,
extras_type, is_wicket, dismissal_type), so they work on cricsheet
rows, capture rows, or hand-built examples alike.

Definitions (Section 4):
  - A legal ball is one that is neither a wide nor a no-ball.
  - An over = 6 legal balls. Overs notation "18.3" = 18 overs + 3
    balls = 111 balls = 18.5 decimal overs. Arithmetic is done on
    ball counts, never on the x.y float.
  - Balls faced by a batter: all deliveries faced except wides
    (no-balls count as a ball faced).
  - Balls bowled (for economy / strike rate): legal balls only.
  - Batter runs exclude all extras. Bowler runs conceded = batter
    runs + wides + no-ball penalty (and runs off a no-ball, which are
    batter runs); byes and leg-byes are EXCLUDED.
  - Team total = batter runs + all extras.
  - Dot ball: a legal delivery with zero runs to the batting side
    (a wide is never a dot: it concedes a run and is not legal).
  - Bowler-credited dismissals: bowled, caught, caught and bowled,
    lbw, stumped, hit wicket. NOT credited: run out, retired out,
    retired hurt, obstructing the field, hit the ball twice, timed
    out, handled the ball.
  - Phases use 1-indexed over numbers: Powerplay = overs 1-6,
    Middle = 7-15, Death = 16-20. The project data stores 0-indexed
    overs; phase_for_over_index0 converts.
"""
from __future__ import annotations

BALLS_PER_OVER = 6
DEFAULT_QUOTA_BALLS = 120  # 20 overs

_WIDES = "wides"
_NOBALLS = "noballs"

BOWLER_CREDITED_WICKETS = frozenset({
    "bowled", "caught", "caught and bowled", "lbw", "stumped",
    "hit wicket",
})


def _clean(value) -> str:
    """Normalise a source field that may be None or NaN (parquet null)."""
    if value is None or (isinstance(value, float) and value != value):
        return ""
    return str(value).strip().lower()


def _norm_extras(extras_type) -> str:
    return _clean(extras_type)


def is_legal_ball(extras_type) -> bool:
    """Legal ball: neither a wide nor a no-ball."""
    return _norm_extras(extras_type) not in (_WIDES, _NOBALLS)


def is_ball_faced(extras_type) -> bool:
    """A batter is charged a ball faced for every delivery except a
    wide (no-balls count as faced)."""
    return _norm_extras(extras_type) != _WIDES


def is_bowler_credited(dismissal_type) -> bool:
    """True iff the dismissal is credited to the bowler (Section 4)."""
    d = _clean(dismissal_type).replace("&", "and")
    if not d:
        return False
    return d in BOWLER_CREDITED_WICKETS


def overs_to_balls(overs: str) -> int:
    """"18.3" -> 111 balls. The fractional digit is BALLS (0-5), not a
    decimal fraction; anything else raises ValueError."""
    whole, _, part = str(overs).partition(".")
    balls = int(part) if part else 0
    if balls >= BALLS_PER_OVER:
        raise ValueError(f"invalid overs notation: {overs!r}")
    return int(whole) * BALLS_PER_OVER + balls


def balls_to_overs(balls: int) -> str:
    """111 -> "18.3" (display notation only; never do arithmetic on it)."""
    return f"{balls // BALLS_PER_OVER}.{balls % BALLS_PER_OVER}"


def balls_to_decimal_overs(balls: int) -> float:
    """111 -> 18.5 decimal overs (balls / 6)."""
    return balls / BALLS_PER_OVER


def phase_for_over(over_number: int) -> str:
    """Phase for a 1-indexed over number: 1-6 Powerplay, 7-15 Middle,
    16-20 Death."""
    if over_number <= 6:
        return "Powerplay"
    if over_number <= 15:
        return "Middle"
    return "Death"


def phase_for_over_index0(over_index0: int) -> str:
    """Phase for the project's stored 0-indexed over (over 0 = over 1)."""
    return phase_for_over(over_index0 + 1)


def innings_summary(deliveries) -> dict:
    """Aggregate one innings from delivery records.

    Returns batter_runs, extras_breakdown (runs by extras type),
    extras_total, team_total, legal_balls, balls_faced, bowler_runs
    (Section 4 attribution), wickets_lost (all dismissals incl.
    retired out; retired hurt is not a wicket lost), bowler_wickets
    (credited only), dot_balls.
    """
    batter_runs = 0
    breakdown = {"wides": 0, "noballs": 0, "legbyes": 0, "byes": 0}
    legal = faced = bowler_runs = wickets = bowler_wkts = dots = 0
    for d in deliveries:
        off_bat = int(d.get("runs_off_bat") or 0)
        extras = int(d.get("runs_extras") or 0)
        xtype = _norm_extras(d.get("extras_type"))
        batter_runs += off_bat
        if xtype in breakdown:
            breakdown[xtype] += extras
        # Bowler attribution: batter runs + wides + no-ball runs;
        # byes and leg-byes never count against the bowler.
        bowler_runs += off_bat
        if xtype in (_WIDES, _NOBALLS):
            bowler_runs += extras
        if is_legal_ball(xtype):
            legal += 1
            if off_bat + extras == 0:
                dots += 1
        if is_ball_faced(xtype):
            faced += 1
        dismissal = d.get("dismissal_type")
        if d.get("is_wicket") or _clean(dismissal):
            if _clean(dismissal) != "retired hurt":
                wickets += 1
            if is_bowler_credited(dismissal):
                bowler_wkts += 1
    extras_total = sum(breakdown.values())
    return {
        "batter_runs": batter_runs,
        "extras_breakdown": breakdown,
        "extras_total": extras_total,
        "team_total": batter_runs + extras_total,
        "legal_balls": legal,
        "balls_faced": faced,
        "bowler_runs": bowler_runs,
        "wickets_lost": wickets,
        "bowler_wickets": bowler_wkts,
        "dot_balls": dots,
    }


def batting_average(runs: int, dismissals: int):
    """runs / dismissals; None when dismissals = 0 (undefined, shown
    as an em dash by callers, never as the runs value)."""
    if dismissals == 0:
        return None
    return runs / dismissals


def batting_strike_rate(runs: int, balls_faced: int):
    """100 x runs / balls faced; None when balls faced = 0."""
    if balls_faced == 0:
        return None
    return 100.0 * runs / balls_faced


def bowling_average(runs_conceded: int, wickets: int):
    """runs conceded / bowler-credited wickets; None when wickets = 0."""
    if wickets == 0:
        return None
    return runs_conceded / wickets


def bowling_strike_rate(legal_balls: int, wickets: int):
    """legal balls / bowler-credited wickets; None when wickets = 0."""
    if wickets == 0:
        return None
    return legal_balls / wickets


def economy_rate(runs_conceded: int, legal_balls: int):
    """runs conceded / (legal balls / 6); None when legal balls = 0."""
    if legal_balls == 0:
        return None
    return runs_conceded / (legal_balls / BALLS_PER_OVER)


def run_rate(runs: int, legal_balls: int):
    """runs x 6 / legal balls; None when legal balls = 0."""
    if legal_balls == 0:
        return None
    return runs * BALLS_PER_OVER / legal_balls


def required_run_rate(target: int, runs_so_far: int, legal_balls_left: int):
    """(target - runs so far) x 6 / legal balls remaining; 0.0 once the
    target is reached; None when no balls remain and the target has
    not been reached."""
    needed = target - runs_so_far
    if needed <= 0:
        return 0.0
    if legal_balls_left == 0:
        return None
    return needed * BALLS_PER_OVER / legal_balls_left


def adjusted_balls(legal_balls: int, wickets: int,
                   quota_balls: int = DEFAULT_QUOTA_BALLS) -> int:
    """NRR ball accounting: an all-out innings (10 wickets) counts as
    the full quota of balls faced regardless of balls actually used."""
    return quota_balls if wickets >= 10 else legal_balls


def net_run_rate(innings_records, quota_balls: int = DEFAULT_QUOTA_BALLS):
    """Season-aggregated NRR per team (Section 4):

        NRR = (runs scored / overs faced) - (runs conceded / overs bowled)

    aggregated over all matches (never averaged per match), with the
    all-out rule applied on both sides via adjusted_balls and overs in
    decimal (balls / 6). Each record: batting_team, bowling_team,
    runs (team total), legal_balls, wickets. DLS-affected matches are
    the caller's responsibility: exclude and flag them before calling
    (no DLS rule is assumed here).
    """
    scored, faced, conceded, bowled = {}, {}, {}, {}
    for r in innings_records:
        bat, bowl = r["batting_team"], r["bowling_team"]
        adj = adjusted_balls(r["legal_balls"], r["wickets"], quota_balls)
        scored[bat] = scored.get(bat, 0) + r["runs"]
        faced[bat] = faced.get(bat, 0) + adj
        conceded[bowl] = conceded.get(bowl, 0) + r["runs"]
        bowled[bowl] = bowled.get(bowl, 0) + adj
    out = {}
    for team in scored:
        if faced.get(team, 0) == 0 or bowled.get(team, 0) == 0:
            out[team] = None
        else:
            out[team] = (scored[team] / balls_to_decimal_overs(faced[team])
                         - conceded[team]
                         / balls_to_decimal_overs(bowled[team]))
    return out
