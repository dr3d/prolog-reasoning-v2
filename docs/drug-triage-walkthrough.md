# Drug Interaction Triage Walkthrough (Level 5)

Status: Draft  
Date: 2026-04-06

This walkthrough shows a hard-logic safety task that is easy to understand:
deterministic medication triage.

The script uses explicit facts plus rules to classify candidate drugs as:

- `contraindicated`
- `caution`
- `safe`

## Run It

From the repo root:

```bash
python scripts/demonstrate_drug_triage_tool.py
```

## What It Demonstrates

- allergy constraints (`penicillin_allergy`)
- current-medication interaction checks (`major_interaction`)
- risk-profile checks (`renal_risk_nsaid`)
- deterministic status rollup per candidate drug

## Why This Is A Good "Wow" Demo

- the domain is intuitive
- the consequences are multi-step
- output is table-shaped and explainable
- a plain LLM should present this, not invent it

## Expected Pattern

You should see a markdown triage table and a short connect-the-dots summary.
For the seeded data, `acetaminophen` should emerge as the safe option for
`alice`, while other options are flagged via explicit reasons.
