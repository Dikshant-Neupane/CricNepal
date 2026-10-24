# Matchday capture — announced XI and toss

On matchdays the predictions stop being based on *expected* XIs. The
announced XI (~30–60 min before the match) and the toss (~15 min
before the first ball) are captured in two small CSVs and locked by
`scripts/lock_matchday.py`. First ball = freeze: after it, no
pre-match or toss-adjusted prediction for that match may be locked.

## xi.csv — announced playing XI

Header: `match_id,team,player,batting_position`

- One row per player, 22 rows per match (11 per team).
- `match_id` is the fixture id from `data/fixtures/s3_fixtures.csv`
  (e.g. `s3_2026_03`).
- `team` is the canonical team name (as in the fixtures file).
- `player` is the player's `player_key` from
  `data/predictions/player_master.csv` (preferred) or their exact
  canonical name.
- `batting_position` is 1–11, the announced batting order.

Validation (enforced by lock_matchday.py): exactly 11 players per
team; every player belongs to that team's squad in the player master;
no duplicates; batting positions unique per team.
**Overseas-player cap: NOT enforced.** No NPL playing-conditions rule
for an XI overseas cap was verified from an opened source during the
Phase 2 build, so no cap check exists — if the league publishes one,
add the check and cite the source here.

## toss.csv — toss result

Header: `match_id,toss_winner,decision`

- `toss_winner` is the canonical team name; `decision` is `bat` or
  `field`.

## Locking

```
# after XI announcement, before the toss:
python scripts/lock_matchday.py --xi-csv data/matchday/<match>_xi.csv
# locks stage P1_post_XI (model v1.1, temperature-calibrated)

# after the toss, before the first ball:
python scripts/lock_matchday.py --toss-csv data/matchday/<match>_toss.csv
# locks stage P2_post_toss (adjusts the locked P1_post_XI if present,
# else the locked pre-season P1; the base stage is recorded)
```

`--dry-run` computes and prints everything and writes locks only to a
temporary directory — production frozen log untouched.
`--make-example-xi <match_id>` writes a starter xi.csv for a fixture
from the expected-XI selector (replace it with the announced XI on the
day; it is a typing aid, not a prediction input until confirmed).

See `example_xi.csv` / `example_toss.csv` in this folder for the exact
formats.
