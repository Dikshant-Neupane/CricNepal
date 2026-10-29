# Post-match brief — evidence template (plan task 6.4, S2/S5)

Every observation in a brief follows this shape. A brief that cannot
fill the evidence line does not carry the observation.

## Per-observation block

- **Observation:** what happened, stated as an observed fact (scores,
  phases, dismissals), never as a model estimate.
- **Evidence:** the numbers behind it, each traceable to a named
  source file (scorecard capture, approach profiles, priors), with
  sample size (n) and the baseline it is compared against.
- **Limitation:** what the evidence cannot support — small samples,
  single-match noise, missing fields. "Weakness" labels are forbidden
  on Limited evidence (< 30 balls); causal language is forbidden for
  descriptive statistics — use "contributing factors".
- **Possible action:** the coaching option the evidence suggests,
  plus the alternative. Expected effects may only be stated when a
  validated model can estimate them, with uncertainty.
- **Model note (separate):** what the frozen lines did, labelled as
  model output, never merged into the observed facts.

## Pre-publication check

Run the number validator against the brief and its sources; every
number must trace or be explicitly allowed (dates, quotas):

    python scripts/validate_brief_numbers.py data/briefs/brief_mNN.md \
        --sources data/capture/match_facts.csv \
                  data/capture/scorecard_batting.csv \
                  data/capture/scorecard_bowling.csv \
                  data/predictions/player_priors.csv \
                  data/approach/team_approach_profiles.csv \
        --allow 2026 20
