# 02 - Memory and Inference Map

This infographic captures the current architecture thinking around:
- two memory systems
- two inference systems
- how they cooperate per turn

```mermaid
flowchart TD
    U[User turn] --> LLM[LLM conversational layer]

    subgraph M1[Memory A: Active Conversation Memory]
        ST1[Recent turns]
        ST2[Session intent and goals]
        ST3[Current ontology context]
    end

    subgraph M2[Memory B: Symbolic Fact Memory]
        LT1[Prolog facts and rules]
        LT2[Context tags and metadata]
        LT3[Manifest and schema constraints]
    end

    subgraph I1[Inference A: Neural and Semantic Inference]
        N1[Intent parsing]
        N2[Entity grounding]
        N3[Context routing]
    end

    subgraph I2[Inference B: Symbolic and Deterministic Inference]
        S1[Backward chaining]
        S2[Constraint propagation]
        S3[Proof and failure traces]
    end

    LLM --> ST1
    LLM --> ST2
    LLM --> ST3

    ST1 --> N1
    ST2 --> N1
    ST3 --> N3

    N1 --> N2
    N2 --> N3

    N3 -->|scoped query and write policy| LT1
    N3 -->|scoped query and write policy| LT2
    N3 -->|validation boundaries| LT3

    LT1 --> S1
    LT1 --> S2
    LT2 --> S1
    LT3 --> S3

    S1 --> OUT[Deterministic answer]
    S2 --> OUT
    S3 --> OUT2[Explanation and failure guidance]

    OUT --> LLM
    OUT2 --> LLM

    LLM --> SAVE[Store or update facts with context tags]
    SAVE --> LT1
    SAVE --> LT2
```

## Reading Guide

1. Active conversation memory keeps short-horizon focus for the current turn.
2. Symbolic fact memory stores long-horizon truth and constraints.
3. Neural and semantic inference determines intent, grounding, and context scope.
4. Symbolic deterministic inference executes logic and produces reliable answers.
5. The LLM orchestrates both systems and records validated facts back into symbolic memory.

## Two Memory Modes

- Active conversation memory (short-term): transient, turn-focused, fast context shaping.
- Symbolic fact memory (long-term): persistent, structured, explicit truth maintenance.

## Two Inference Modes

- Neural and semantic inference: interpretation and routing under ambiguity.
- Symbolic deterministic inference: proof-driven reasoning with stable outcomes.

## Why This Split

- Better focus: scoped retrieval reduces irrelevant matches.
- Better reliability: final answers come from deterministic execution.
- Better explainability: proof traces and failure causes are explicit.
