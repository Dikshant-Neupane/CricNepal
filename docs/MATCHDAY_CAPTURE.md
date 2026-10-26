# Matchday capture — the fast lane (Season 3)

Why this exists: the official ball-by-ball data (Cricsheet) publishes
days after a match (Season 2 median lag ~8 days), but matches come
every 2-3 days. Decisions for the next match cannot wait for it. So we
capture at two speeds:

- **Fast lane (this document):** scorecard-level data the same evening,
  entered into `data/capture/`, validated by `scripts/scorecard_check.py`.
  Feeds form, availability, opponent cards, the hub results, and the
  P1/P2 locks.
- **Truth lane:** when Cricsheet lands, `scripts/inseason_update.py`
  ingests the full ball-by-ball; any difference from the fast-lane entry
  is investigated, never silently overwritten.

League-wide at scorecard level (standings/NRR need every match); deep
capture (events, false shots, drops) only for Janakpur's matches and
the next opponent's matches.

## Timeline for a Janakpur match

| When | What | Where it goes |
|---|---|---|
| T-48h | Opponent card filled from ball-by-ball + last-match watch | `data/capture/opponent_card_template.md` -> one card per fixture |
| T-24h | Availability sweep: our camp + opponent news (CAN/team releases, reputable press) | `availability_log.csv` |
| XI announced (~T-30m) | Confirmed XIs for both teams, exactly as announced | lock P1: `scripts/lock_matchday.py` |
| Toss | Winner + decision | lock P2: `scripts/lock_matchday.py`; `matchday_log.csv` |
| During | Strip read, dew onset/severity, drops, injuries, DRS, role changes | `matchday_log.csv`, `events_log.csv` |
| Full time +1h | Result recorded; scorecard entered from the broadcast/ESPNcricinfo/Cricbuzz card | `scripts/record_result.py`; `match_facts.csv`, `scorecard_batting.csv`, `scorecard_bowling.csv` |
| Same evening | Run the validator — entry must close before it is used | `python scripts/scorecard_check.py --match-id <id>` |
| Same evening | Post-match team brief written: how each team approached the game, players vs their priors, and the implications for Janakpur's next fixtures (every match involving Janakpur or a future opponent) | `data/briefs/brief_m<NN>.md` — rendered on the Bolts Game Plan page |
| Same evening | Our bowlers' workload updated | `workload_log.csv` |
| Next morning | Daily check ingests any Cricsheet data; reconcile diffs | cron + runbook `docs/S3_INGESTION_RUNBOOK.md` |

For non-Janakpur matches: result + scorecard entry (facts rows are
enough for standings/NRR) plus the same-evening team brief — every
league opponent is a future Janakpur opponent; events/watch items only
for the next opponent.

## The files (all in data/capture/)

- `matchday_log.csv` — one row per match: slot, strip id + read, grass,
  dew expected/onset over/severity (1-5), grip/boundary/weather notes,
  toss, interruptions, player of the match. This builds the TU dew and
  strip dataset that exists nowhere else.
- `events_log.csv` — one row per event: dropped_catch, misfield,
  false_shot_spell, injury, drs_review, role_change, other; with an
  estimated runs cost where judgeable.
- `workload_log.csv` — per bowler per day: match + training balls;
  flag any spike (acute:chronic ratio heading above ~1.3).
- `availability_log.csv` — status per player per day with source;
  overseas arrivals/departures and NOC issues included.
- `match_facts.csv` — one row per innings: totals, wickets, overs,
  extras split (byes/leg-byes/wides/no-balls/penalty).
- `scorecard_batting.csv` / `scorecard_bowling.csv` — the full card.
  Bowling overs are entered as **balls bowled** (3.4 overs = 22), never
  cricket notation.
- `opponent_card_template.md` — copy per fixture.

## Rules

1. **No entry is trusted until the validator passes.** A scorecard that
   does not close has a typo in it; find it the same evening.
2. **Never guess a field.** Unknown = blank, and blank is fine. A blank
   dew onset is data; an invented one is poison.
3. Names must match the player master exactly; a new name is flagged
   for registry resolution, not improvised.
4. The frozen prediction log is append-only — capture never edits it.
5. Venue tables (`data/venue/`) regenerate from the truth lane:
   `python scripts/build_tu_par_tables.py` after each ingest.

## Reading par (data/venue/)

Par at TU is the 1st-innings total where the chase becomes a coin flip,
from `tu_chase_bands.csv` — on S1+S2 data the bands cross 50% between
150-159. Always quote par with its split (Day vs Day-Night) and its n;
the historical Day-Night sample is small (see the brief in the goal
files) and grows with every S3 evening match, which is exactly why the
matchday log records slot, strip and dew for every game.
