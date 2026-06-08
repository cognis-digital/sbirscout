# Demo 01 - Basic SBIR/STTR bid scouting

A small defense/health-tech firm wants to triage this week's solicitation
topics across DoD DSIP, SBIR.gov, and NIH. The firm's edge is autonomous
systems, edge ML, and RF sensing. It prefers Phase I and Direct-to-Phase-II
work, and it does **not** currently have a university research partner (so
pure STTR topics carry a penalty).

## Input

`topics.json` is a normalized digest of 5 topics pulled from three sources.

## Run it

```sh
# Human-readable ranked table
python -m sbirscout scout demos/01-basic/topics.json \
  --capabilities "autonomous systems,edge ml,rf sensing,uas" \
  --phases "I,DIRECT_II" \
  --today 2026-06-08

# Machine-readable digest
python -m sbirscout --format json scout demos/01-basic/topics.json \
  --capabilities "autonomous systems,edge ml,rf sensing,uas" \
  --phases "I,DIRECT_II" --today 2026-06-08

# List supported sources
python -m sbirscout sources
```

## What to expect

* The DoD edge-ML UAS topic should score **GO** (strong capability match,
  preferred phase, near-term deadline, healthy ceiling).
* The NIH STTR topic should be penalized for the missing research partner.
* An already-closed topic is forced to **PASS** regardless of fit.

Scores are fully explainable: each row prints its match/phase/funding/urgency
contributions so a bid/no-bid call can be defended.
