#!/usr/bin/env python
"""Build data/fixtures/s3_fixtures.csv — NPL Season 3 schedule.

Sources (pairings/dates accessed 2026-10-24):
- League-stage pairings/dates/match numbers: nepinsights.com fixture list,
  which reproduces the Cricket Association of Nepal (CAN) fixture graphic,
  cross-checked against ipl.com's NPL 2026 schedule (identical pairings and
  dates for every league match). Within a double-header day, the order
  below is the CAN fixture-graphic order (first listed = day match).
- Playoff dates/stages: nepalontheweb.com report of CAN's revised schedule
  (Qualifier 1 Nov 17, Eliminator Nov 18, Qualifier 2 Nov 19, Final Nov 21).
  Playoff teams are not known until the league stage ends -> team fields
  are null and verification_status flags that.

Start times (added 2026-10-24, review fix R1):
- CAN revised the match timings on 2026-10-20 when Hawk-Eye DRS was
  introduced: the evening start moved from 16:30 to 17:00. The revised
  rule, as reported from CAN's press statement by nepalontheweb.com
  ("NPL Season 3 to feature Hawk-Eye DRS, revised schedule announced",
  published 2026-10-20) and english.khabarhub.com ("DRS to be used in
  all NPL matches; schedule revised", 2026-10-20) -- both pages opened
  and read on 2026-10-24 -- is: on double-header days the first match
  starts 12:30 and the second 17:00; on single-match days the match
  starts 17:00. Playoff days are single-match days, so playoffs are
  17:00 under the same rule. This supersedes the earlier conflicting
  listings (revised CAN graphic 12:30/17:00 vs cricketer.io 12:15/16:15)
  that previously forced start_time_local to be left blank.
- Every fixture therefore carries a verified slot time, a per-row
  start_time_source and start_time_accessed timestamp. Any future row
  whose slot cannot be verified must stay blank with the reason in
  start_time_verification -- never guessed.

Team names use the repo/cricsheet canonical forms -- note several
schedule sources spell Kathmandu's team "Gurkhas"; the canonical name in
all project data (and cricsheet) is "Kathmandu Gorkhas".

Team order within a fixture carries no meaning (no home team in NPL);
team_1/team_2 are stored alphabetically, matching the matches parquet
convention. Venue is TU International Cricket Ground, Kirtipur for all
matches (CAN announcement via nepalontheweb.com).
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "fixtures" / "s3_fixtures.csv"
VENUE = "Tribhuvan University International Cricket Ground"
SRC_LEAGUE = ("nepinsights.com (CAN fixture graphic) cross-checked "
              "ipl.com NPL 2026 schedule")
SRC_PLAYOFF = "nepalontheweb.com (CAN revised schedule announcement)"
SRC_TIME = ("CAN revised timings announced 2026-10-20 (evening start moved "
            "16:30 -> 17:00 for DRS): double-header days 12:30 + 17:00, "
            "single-match days 17:00 — reported by nepalontheweb.com and "
            "english.khabarhub.com from CAN's press statement")
TIME_ACCESSED = "2026-10-24"
DAY_START = "12:30"     # first match on a double-header day
EVENING_START = "17:00"  # second match on double-header days; all single-match days

# (match_number, date, team_a, team_b) — league stage, CAN graphic order
LEAGUE = [
    (1, "2026-10-26", "Lumbini Lions", "Sudurpaschim Royals"),
    (2, "2026-10-27", "Biratnagar Kings", "Chitwan Rhinos"),
    (3, "2026-10-27", "Karnali Yaks", "Janakpur Bolts"),
    (4, "2026-10-28", "Pokhara Avengers", "Sudurpaschim Royals"),
    (5, "2026-10-29", "Janakpur Bolts", "Kathmandu Gorkhas"),
    (6, "2026-10-29", "Karnali Yaks", "Biratnagar Kings"),
    (7, "2026-10-31", "Lumbini Lions", "Chitwan Rhinos"),
    (8, "2026-10-31", "Sudurpaschim Royals", "Biratnagar Kings"),
    (9, "2026-11-01", "Janakpur Bolts", "Pokhara Avengers"),
    (10, "2026-11-02", "Kathmandu Gorkhas", "Karnali Yaks"),
    (11, "2026-11-02", "Sudurpaschim Royals", "Chitwan Rhinos"),
    (12, "2026-11-03", "Biratnagar Kings", "Janakpur Bolts"),
    (13, "2026-11-03", "Lumbini Lions", "Pokhara Avengers"),
    (14, "2026-11-05", "Lumbini Lions", "Janakpur Bolts"),
    (15, "2026-11-05", "Kathmandu Gorkhas", "Biratnagar Kings"),
    (16, "2026-11-06", "Sudurpaschim Royals", "Karnali Yaks"),
    (17, "2026-11-06", "Chitwan Rhinos", "Pokhara Avengers"),
    (18, "2026-11-07", "Kathmandu Gorkhas", "Lumbini Lions"),
    (19, "2026-11-09", "Pokhara Avengers", "Karnali Yaks"),
    (20, "2026-11-09", "Chitwan Rhinos", "Kathmandu Gorkhas"),
    (21, "2026-11-10", "Sudurpaschim Royals", "Janakpur Bolts"),
    (22, "2026-11-12", "Biratnagar Kings", "Pokhara Avengers"),
    (23, "2026-11-12", "Karnali Yaks", "Lumbini Lions"),
    (24, "2026-11-13", "Kathmandu Gorkhas", "Sudurpaschim Royals"),
    (25, "2026-11-13", "Janakpur Bolts", "Chitwan Rhinos"),
    (26, "2026-11-14", "Biratnagar Kings", "Lumbini Lions"),
    (27, "2026-11-15", "Chitwan Rhinos", "Karnali Yaks"),
    (28, "2026-11-15", "Pokhara Avengers", "Kathmandu Gorkhas"),
]
# (match_number, date, stage)
PLAYOFFS = [
    (29, "2026-11-17", "Qualifier 1"),
    (30, "2026-11-18", "Eliminator"),
    (31, "2026-11-19", "Qualifier 2"),
    (32, "2026-11-21", "Final"),
]

FIELDS = ["match_id", "season", "match_number", "match_date", "stage",
          "team_1_name", "team_2_name", "venue_name", "city",
          "start_time_local", "source", "verification_status",
          "start_time_source", "start_time_accessed",
          "start_time_verification"]


def slot_times(dates_in_order):
    """Assign CAN revised slot times for one day's matches, in fixture
    order: a single match -> 17:00; a double-header -> 12:30 then 17:00.
    Returns a list parallel to the input ('' if a slot is not covered
    by the verified rule)."""
    n = len(dates_in_order)
    if n == 1:
        return [EVENING_START]
    if n == 2:
        return [DAY_START, EVENING_START]
    return [""] * n  # no verified rule for 3+ matches in a day: leave blank


def main():
    league_by_date = {}
    for num, d, a, b in LEAGUE:
        league_by_date.setdefault(d, []).append((num, a, b))
    times = {}
    for d, ms in league_by_date.items():
        for (num, _a, _b), t in zip(ms, slot_times(ms)):
            times[num] = t
    rows = []
    for num, d, a, b in LEAGUE:
        t1, t2 = sorted([a, b])
        t = times[num]
        rows.append({
            "match_id": f"s3_2026_{num:02d}", "season": "S3",
            "match_number": num, "match_date": d, "stage": "League",
            "team_1_name": t1, "team_2_name": t2, "venue_name": VENUE,
            "city": "Kirtipur", "start_time_local": t,
            "source": SRC_LEAGUE, "verification_status": "VERIFIED_TWO_SOURCES",
            "start_time_source": SRC_TIME if t else "",
            "start_time_accessed": TIME_ACCESSED if t else "",
            "start_time_verification": (
                "VERIFIED_SLOT_RULE" if t else
                "UNVERIFIED: slot not covered by the CAN revised-timing rule"),
        })
    for num, d, stage in PLAYOFFS:
        rows.append({
            "match_id": f"s3_2026_{num:02d}", "season": "S3",
            "match_number": num, "match_date": d, "stage": stage,
            "team_1_name": "", "team_2_name": "", "venue_name": VENUE,
            "city": "Kirtipur", "start_time_local": EVENING_START,
            "source": SRC_PLAYOFF,
            "verification_status": "DATE_VERIFIED_TEAMS_TBA",
            "start_time_source": SRC_TIME,
            "start_time_accessed": TIME_ACCESSED,
            "start_time_verification": "VERIFIED_SLOT_RULE_SINGLE_MATCH_DAY",
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    filled = sum(1 for r in rows if r["start_time_local"])
    print(f"Wrote {len(rows)} fixtures to {OUT} ({filled} with verified start times)")


if __name__ == "__main__":
    main()
