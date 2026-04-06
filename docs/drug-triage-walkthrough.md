# Drug Interaction Triage Walkthrough (Level 5)

Status: Active  
Date: 2026-04-06

Canonical ladder:

- [walkthrough-ladder.md](walkthrough-ladder.md)

## Goal

Show deterministic safety classification over medication candidates.

## Run

```bash
python scripts/demonstrate_drug_triage_tool.py
```

## What to Look For

- explicit `contraindicated` / `caution` / `safe` outcomes
- multi-hop constraints (allergy + interactions + risk profile)
- explainable deterministic reasoning instead of plausibility prose

## Next

- Level 6: [drug-triage-agent-mcp-walkthrough.md](drug-triage-agent-mcp-walkthrough.md)
