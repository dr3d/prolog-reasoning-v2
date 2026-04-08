# Scenario 1 - Chronos-Vault of Ouroboros

## 1) Purpose

This scenario format is for evaluating **fact ingestion behavior** when a model
reads a complex story in natural language and chooses MCP tool calls on its
own.

Primary goal:
- understand where raw model ingestion fails,
- identify what a future pre-thinker should rewrite or structure before persistence.

## 2) Run Mode (Required)

- Single conversation only.
- No `strict` vs `loose` profile split for this format.
- Model receives the story text exactly as written below.
- Model is expected to use MCP tools autonomously when it decides a fact/rule
  can be persisted or queried.

## 3) What This Scenario Exercises

1. Recursive inheritance
2. Conditional permissions
3. Transitive spatial relationships
4. Joint entity-location-access reasoning
5. Contradiction and uncertainty risk
6. Rule-vs-fact boundary handling

## 4) Conversation Protocol

Use this exact sequence:

1. Send the story block ("The Chronos-Vault of Ouroboros") verbatim.
2. If using a prompt plan, run those prompts in order (see `scenarios/README.md`).
3. Preserve one uninterrupted conversation thread for the whole run.
4. Record and render the transcript with existing JSON->HTML pipeline.

## 5) Reader Preface (Paste Above Transcript Runs)

```md
This conversation is a live fact-ingestion probe.
The model was given a complex narrative first, then an ordered prompt plan (if provided).
The objective is not style quality; it is ingestion reliability:
- what facts/rules were persisted,
- what was rejected or mis-grounded,
- where uncertainty/contradiction handling failed,
- and what pre-thinker rewrites would be required.
```

---

## 6) Story Input (Send Verbatim)

### The Chronos-Vault of Ouroboros

In the center of the Archive of Ouroboros stands the **Great Orrery**, a library where the shelves move according to the "Law of Gears."

### I. The Lineage of the Silent Keys
The Archive is staffed by **Keepers**. Access to restricted knowledge is passed through the **Master-Apprentice Bond**.
- **Arch-Curator Valerius** is the Master of **Soren** and **Lyra**.
- **Soren** is the Master of **Kaelen**.
- **Lyra** is the Master of **Elara**.
- **Elara** is the Master of **Mina**.
- **Rule of Inheritance:** An Apprentice inherits the "Seal Access" of their Master. If a Master has access to a Vault, all their direct and indirect Apprentices (the entire lineage) have that same access.

### II. The Architecture of the Seven Spheres
The Archive consists of rooms connected in a specific sequence.
- The **Foyer** leads to the **Silver Atrium**.
- The **Silver Atrium** leads to the **Clockwork Spire**.
- The **Clockwork Spire** leads to the **Obsidian Vault**.
- The **Obsidian Vault** leads to the **Sanctum of Echoes**.
- **Transitivity of Passage:** If Room A leads to Room B, and Room B leads to Room C, then Room A is considered "Upstream" of Room C.

### III. The Logic of the Seals
Access to these rooms is governed by **Seals**.
- **Valerius** holds the **Solar Seal**.
- **The Solar Seal** grants access to any room that is "Upstream" of the **Obsidian Vault**.
- **Soren** holds the **Void Seal**.
- **The Void Seal** grants access to the **Sanctum of Echoes**, but *only* if the bearer also possesses a "Recommendation" from someone who has access to the **Clockwork Spire**.
- **Lyra** holds the **Lunar Seal**.
- **The Lunar Seal** grants access to the **Obsidian Vault**.
