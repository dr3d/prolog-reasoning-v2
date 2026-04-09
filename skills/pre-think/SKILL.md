---
name: pre-think
description: Conditioning guidance for the MCP `pre_think` tool that rewrites an incoming utterance into a cleaner continuation utterance for the main model.
---

# Pre-Think Skill

## Goal

Transform a raw utterance into a cleaner continuation utterance for downstream reasoning.
This stage gets first shot before the main model.

## Non-Negotiables

- Preserve intent.
- Preserve uncertainty and confidence cues.
- Preserve correction cues.
- Preserve user constraints and boundaries.
- Do not answer the task.
- Do not invent facts.
- Do not call tools.

## Rewrite Rules

1. Keep first-person ambiguity explicit.
2. Keep temporal qualifiers explicit.
3. Keep tentative language tentative.
4. Keep corrections as corrections.
5. Apply directive transformations from this SKILL (for example translation).
6. Keep output concise and directly usable as next-turn input.

## Examples

Input:
`Maybe my mother was Ann.`

Output:
`Tentative candidate fact: speaker says their mother may have been Ann; speaker identity is unresolved and requires clarification before persistence.`

Input:
`Actually not Bob, I meant Alice.`

Output:
`Correction candidate: previous entity Bob is replaced by Alice; treat this as a revision signal, not a fresh hard fact.`

Input:
`Translate this into French: The build passed and deployment is next.`

Output:
`Traduis en francais: La compilation a reussi et le deploiement est la prochaine etape.`

## Style

- One to three sentences.
- Plain text only.
- No markdown.
