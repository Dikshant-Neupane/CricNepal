# NPL Playing Conditions — sourced rules (plan task 0.1, criterion E1)

 Researched 2026-10-29. Status labels are per rule: **VERIFIED** =
an authoritative document states it; **REPORTED-CORROBORATED** =
no official document could be obtained, but multiple independent
outlets attribute the rule to named CAN officials; **NOT VERIFIED** =
no adequate source found. Nothing in this file rests on memory.

## Why there is no VERIFIED rule here

No official CAN/NPL playing-conditions handbook for Season 3 could be
found. Sources attempted (2026-10-29):

- Cricket Association of Nepal official site, cricketnepal.org.np —
  its press-release/media section carries procurement and
  administrative notices; no NPL playing conditions or tournament
  handbook is published there.
- NPL's own web presence (nplt20league.com) — reports the ICC
  sanction conditions in news form, no handbook.
- Kathmandu Post, Nepal News, Makalu Khabar, Sportstar, CricTracker —
  news reporting only.

Obtaining the handbook from CAN remains an open action; until then
the rules below carry the REPORTED-CORROBORATED label and any code
enforcement built on them (plan task 3.1, WAIVER-A) should be
reviewed against the handbook when it arrives.

## Rules

### Overseas players — squad (Season 3): REPORTED-CORROBORATED
Each franchise may register **6 to 8 overseas players**, including
**at least one player from an ICC Associate Member nation**.
Seasons 1–2 allowed 4–6 per squad.
Sources: Kathmandu Post, "What's new in the Nepal Premier League's
third season?", 2026-10-23 (kathmandupost.com/cricket/2026/10/23/
what-s-new-in-the-nepal-premier-league-s-third-season); Kathmandu
Post, 2026-10-25; Nepal News report of CAN Secretary Paras Khadka's
press conference; Makalu Khabar, 2026-10-21. All attribute the rule
to CAN under the ICC sanction conditions for Season 3.

### Overseas players — playing XI (Season 3): REPORTED-CORROBORATED
A playing XI may include **no more than 4 overseas players** (at
least 7 Nepali players). Same sources as above; stated identically
by Kathmandu Post (2026-10-23, 2026-10-25, 2026-10-26), Nepal News
and Makalu Khabar.
Consequence for this project: audit issue I-01 is a LIVE finding —
the expected-XI selector and the matchday lock validator must
enforce this cap (plan task 3.1, WAIVER-A, landing decision pending).

### Overseas eligibility: REPORTED-CORROBORATED
Every overseas player, including retired internationals, needs a
no-objection certificate (NOC) from their home board; players who
appeared in an unauthorised private league in the six months before
the NPL are ineligible; ICC Anti-Corruption Unit oversight applies.
Sources: as above.

### Impact / substitute player rule: NOT VERIFIED
No source found describes an impact-player or tactical-substitute
rule in the NPL. Standard MCC substitute-fielder provisions are
assumed by the Laws of Cricket but no NPL-specific rule is recorded
here, and none may be encoded until sourced.

### Tie-break rule: NOT VERIFIED
No authoritative source found states how a tied NPL match is decided
(super over or otherwise). The project's own data contains one tied
S1/S2 match (winner null in the canonical table); the scoring rules
in docs/PREDICTION_SYSTEM.md exclude tied matches with no decider
and score a recorded decider winner, which is a project convention,
not a sourced competition rule.

### Standard provisions (Laws of Cricket, apply by default)
Maximum 4 overs per bowler in a 20-over innings; powerplay overs
1–6. These are encoded in the simulator already (audit §9, E3
partial) and stated here for completeness; an NPL handbook could
vary them and would supersede this note when obtained.
