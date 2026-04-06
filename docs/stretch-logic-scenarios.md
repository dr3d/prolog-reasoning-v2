# Stretch Logic Scenarios

Status: Draft  
Date: 2026-04-06

This note proposes harder "connect-the-dots" problems where an LLM + symbolic
tool pairing can produce unexpectedly strong answers from structured facts.

The goal is not brute complexity. The goal is domains where:

- pure language guessing degrades quickly
- multi-step deterministic consequences matter
- explanations are part of the value

## 1. Clinical Drug Interaction Triage

### Why it is hard

- many interacting constraints
- contraindications, age limits, allergy conflicts, renal flags
- a single missed rule can be harmful

### Symbolic value

- deterministic conflict detection
- explicit rule path for each warning
- can generate ranked action table:
  - safe
  - caution
  - contraindicated

### "Wow" query

"Given this med list, comorbidities, and allergies, what combination is safest
and why?"

## 2. Multi-Hop Compliance Eligibility

### Why it is hard

- policy rules are layered and exception-heavy
- evidence comes from many facts across time
- one clause can invalidate an otherwise plausible outcome

### Symbolic value

- eligibility as deterministic closure
- contradiction reports for missing/invalid evidence
- explainable denial reasons

### "Wow" query

"Which applicants qualify, which fail, and what single missing fact would make
each failed case pass?"

## 3. Incident Causality and Blast Radius

### Why it is hard

- causal chains span services, dependencies, versions, regions
- humans miss second-order consequences under pressure

### Symbolic value

- deterministic dependency graph reasoning
- explicit "if A fails, what must fail next?" paths
- can emit ranked blast-radius table

### "Wow" query

"If service X is degraded and feature flag Y is off, what downstream user
capabilities fail within 10 minutes?"

## 4. Contract Obligation Tracking

### Why it is hard

- obligations trigger from conditions and deadlines
- exceptions and supersessions change status
- auditability matters

### Symbolic value

- deterministic obligation state machine
- explicit trigger / exception traces
- compliant / at-risk / breached table output

### "Wow" query

"Which obligations are active today, what evidence satisfies them, and what is
the earliest breach risk?"

## 5. Supply Chain Substitution Planner

### Why it is hard

- part compatibility constraints
- vendor restrictions
- regional shipping and regulatory constraints

### Symbolic value

- valid/invalid substitution enumeration
- deterministic rejection reasons
- candidate ranking with hard constraint filters first

### "Wow" query

"If component A is unavailable, what substitutions keep all regulatory and
compatibility constraints valid in region R?"

## 6. Security Entitlement Drift

### Why it is hard

- role inheritance plus ad-hoc grants over time
- stale grants survive org changes
- violations are often subtle combinations

### Symbolic value

- deterministic entitlement closure
- least-privilege gap detection
- "why this account is over-privileged" explanations

### "Wow" query

"Show every user whose effective permissions exceed role policy, and prove the
minimal fact set that causes each drift case."

## 7. Why These Scenarios Are Good Research Targets

Each scenario naturally tests the same project thesis:

- language model interprets intent and orchestrates calls
- symbolic layer computes hard consequences
- output is not only correct, but explainable and reproducible

They also map cleanly to your roadmap:

- fact intake quality
- predicate mapping quality
- revision / supersede semantics
- contradiction handling
- agent-facing logic utility

## 8. Suggested First Stretch Pick

If you want one that is both impressive and feasible:

- start with **Security Entitlement Drift** or **Multi-Hop Compliance Eligibility**

Both domains:

- are easy to understand
- have clear table outputs
- reward deterministic reasoning
- and can produce genuinely surprising "connect-the-dots" findings.
