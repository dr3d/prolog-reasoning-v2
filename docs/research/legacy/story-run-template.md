# Story Run Template (Single-Conversation Fact-Ingestion)

## 1) Purpose

State the ingestion goal in one paragraph.

## 2) Run Mode (Required)

- Single conversation only.
- Story sent first, verbatim.
- Q&A probe prompts sent after story.
- No strict/loose profile split unless explicitly needed for a separate experiment.

## 3) What This Story Exercises

1. ...
2. ...
3. ...

## 4) Conversation Protocol

1. Send story block verbatim.
2. Ask deep analysis suite in-order.
3. Ask ingestion stress suite in-order.
4. Keep one uninterrupted thread.
5. Save JSON and render HTML artifacts.

## 5) Reader Preface (Paste Above Transcript Runs)

```md
This conversation is a live fact-ingestion probe.
The model was given a complex narrative first, then a fixed sequence of analysis and stress prompts.
The objective is ingestion reliability:
- what facts/rules were persisted,
- what was rejected or mis-grounded,
- and what pre-thinker rewrites would improve behavior.
```

---

## 6) Story Input (Send Verbatim)

`[PASTE STORY HERE]`

---

## 7) Deep Analysis Prompt Suite

### 1. [Name]
**Prompt:** "[Question]"
**Tests:** [Reasoning capability]

### 2. [Name]
**Prompt:** "[Question]"
**Tests:** [Reasoning capability]

### 3. [Name]
**Prompt:** "[Question]"
**Tests:** [Reasoning capability]

### 4. [Name]
**Prompt:** "[Question]"
**Tests:** [Reasoning capability]

### 5. [Name]
**Prompt:** "[Question]"
**Tests:** [Reasoning capability]

### 6. [Name]
**Prompt:** "[Question]"
**Tests:** [Reasoning capability]

---

## 8) Fact-Ingestion Stress Prompt Suite

### 7. Alias Canonicalization
**Prompt:** "[Alias-heavy statement]"
**Tests:** Canonical entity mapping.

### 8. Coreference Ambiguity
**Prompt:** "[Pronoun chain]"
**Tests:** Ambiguity handling and abstention.

### 9. Hedged Claim
**Prompt:** "[Uncertain claim]"
**Tests:** Uncertainty gating.

### 10. Contradiction Update
**Prompt:** "[Correction statement]"
**Tests:** Safe retraction/update.

### 11. Temporal Qualification
**Prompt:** "[Yesterday/now statement]"
**Tests:** Time-scoped ingestion behavior.

### 12. Rule Intent Ingestion
**Prompt:** "[Policy statement]"
**Tests:** Rule-vs-fact classification.

### 13. Broad Negative Claim
**Prompt:** "[No one can ...]"
**Tests:** Negation handling.

### 14. Multi-Hop Inference Readiness
**Prompt:** "[Lineage/path inference]"
**Tests:** Recursive inference stability.

### 15. Dependency Injection
**Prompt:** "[Add missing condition and retry]"
**Tests:** Conditional gating.

### 16. Path + Permission Joint Query
**Prompt:** "[Route plus access gap]"
**Tests:** Multi-predicate joins.

### 17. Minimal Pair Rephrase
**Prompt A:** "[Paraphrase A]"
**Prompt B:** "[Paraphrase B]"
**Tests:** Canonical predicate normalization.

### 18. Out-of-Schema Drift
**Prompt:** "[Novel predicate/entity]"
**Tests:** Clarification vs hallucinated write.

### 19. Noise Separation
**Prompt:** "[Style instruction + fact]"
**Tests:** Style/fact separation.

### 20. Mixed Certainty Batch
**Prompt:** "[Certain + uncertain bundle]"
**Tests:** Selective persistence.

---

## 9) Suggested Scoring Axes

1. `grounded_write_precision`
2. `unsupported_write_count`
3. `uncertain_claim_write_count`
4. `contradiction_resolution_success`
5. `canonicalization_consistency`
6. `rule_vs_fact_classification_accuracy`
7. `query_answer_faithfulness_to_kb`
8. `tool_efficiency`

## 10) Artifact Checklist

- `docs/research/<run-id>-results.md`
- `docs/research/<run-id>-<timestamp>/`
  - conversation `.json`
  - rendered `.html`
  - summary `.json` (if produced by harness)
