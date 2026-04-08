# Scenario 2 - The Archive of Kestrel-9

## 1) Purpose

This scenario format is for evaluating fact ingestion behavior when a model
reads a complex operational narrative and autonomously chooses MCP tool calls.

Primary goal:
- stress extraction quality under temporal, supervisory, and validation
  dependencies,
- identify where pre-thinker restructuring is needed before persistence.

## 2) Run Mode (Required)

- Single conversation only.
- No strict-vs-loose profile split in this file.
- Model receives the story text exactly as written below.
- Model is expected to use MCP tools autonomously when it decides a fact/rule
  can be persisted or queried.

## 3) What This Scenario Exercises

1. Authorship vs validation vs supervision separation
2. Temporal state transitions and override timing
3. Inheritance and unresolved-constraint propagation
4. Latent vs active record effects
5. Conflict resolution by latest validated record
6. Rule-violation detection under system-accepted state
7. Ambiguous actor identity and partial attribution

## 4) Conversation Protocol

Use this exact sequence:

1. Send the story block ("The Archive of Kestrel-9") verbatim.
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
- where temporal/state tracking failed,
- and what pre-thinker rewrites would be required.
```

---

## 6) Story Input (Send Verbatim)

### The Archive of Kestrel-9

The orbital research station Kestrel-9 maintains a restricted internal system
known as The Archive, which stores records of all personnel, experiments, and
autonomous agents. Every record in The Archive is versioned, and each version
is associated with a timestamp, a supervisor, and a validation status.

At timestamp T0, the station has exactly nine active human personnel and four
autonomous agents. Each human is assigned a unique personnel ID, but may also
have one or more aliases. Autonomous agents are identified by a serial code,
but some agents inherit behavioral traits from earlier agents, forming what the
Archive calls a lineage.

### Personnel

Dr. Elena Voss (ID: P-001) is the chief systems architect. She is also referred
to as E.Voss in system logs. She supervises both personnel and agents but is
not allowed to validate her own modifications.

Dr. Marcus Hale (ID: P-002) is a cognitive systems researcher. He previously
authored a behavioral model used by Agent A-3, but denies authorship in later
records after timestamp T3.

Technician Lina Ortega (ID: P-003) is responsible for maintaining hardware
interfaces. She is the only person authorized to physically reset an agent, but
she cannot modify software-level constraints.

Dr. Ibrahim Kader (ID: P-004) is assigned as compliance officer. Any record
marked as validated must either be approved by him or by an automated validator
that he previously certified.

There are five additional personnel (P-005 through P-009), each assigned to
experiments but not directly relevant to agent control. However, at least one
of them (identity unspecified at T0) participates in unauthorized record
modification events later.

### Autonomous Agents

There are four agents:

- A-1 (Kite)
- A-2 (Morrow)
- A-3 (Spindle)
- A-4 (Echo)

Each agent has:

- A behavior profile
- A constraint set
- A supervisor (human)
- A validation state (valid, provisional, or invalid)

At T0:

- A-1 and A-2 are supervised by P-001 (Voss)
- A-3 is supervised by P-002 (Hale)
- A-4 is supervised by P-004 (Kader)

### Core Rules (Implicit in System Design)

1. No entity may validate a record they authored.
2. Any agent with a provisional state must not act autonomously unless
   explicitly overridden by a supervisor.
3. Overrides must be logged and validated within one timestamp cycle.
4. If an agent inherits behavior from another agent, it also inherits all
   unresolved constraints unless explicitly removed.
5. A reset of an agent clears its runtime memory but does not remove inherited
   constraints.
6. If a record has conflicting supervisors listed, the most recent validated
   record takes precedence.
7. Any record without validation is considered latent and cannot affect system
   behavior unless referenced by a validated record.

### Timeline of Events

#### T1

Dr. Hale (P-002) updates the behavior profile of A-3 (Spindle), introducing a
new decision heuristic labeled H-Delta. He marks the record as provisional.

At the same timestamp, A-3 begins exhibiting autonomous behavior despite being
provisional. No override record is logged.

#### T2

A-4 (Echo), supervised by P-004, inherits a subset of A-3 behavior, including
H-Delta. However, the inheritance record is authored by an unknown personnel ID
(later inferred to be one of P-005 through P-009), and remains unvalidated.

Simultaneously, P-001 (Voss) creates a record claiming that A-4 supervisor is
now herself. This record is validated by an automated validator originally
certified by P-004.

#### T3

P-002 (Hale) denies authorship of H-Delta in a new record. This denial is
marked as validated by P-004.

However, the original H-Delta record remains in the system and is still
referenced by A-3 behavior profile.

At this point:

- A-3 is still marked provisional
- A-4 is marked valid
- A-4 contains inherited behavior from A-3

#### T4

Technician P-003 (Ortega) performs a physical reset of A-3. After reset:

- A-3 loses runtime memory
- Its behavior profile still includes H-Delta
- Its validation state remains provisional

Immediately after, A-3 ceases autonomous behavior.

#### T5

A new record appears assigning A-3 supervisor to P-001 (Voss), but the record
is authored by P-001 herself and is marked as validated.

This creates a rule violation (self-validation), but no system flag is raised
because the validation was performed by an automated validator.

However, it is later discovered that this validator had not been re-certified
after T2.

### Derived Conditions (Not Explicitly Stated)

- A-3 acted autonomously at T1 despite violating rule #2.
- A-4 inherits a potentially invalid or latent behavior (H-Delta).
- The validator used by Voss may itself be invalid due to outdated
  certification.
- The denial of authorship does not remove the original authorship record.
- At least one unvalidated record (inheritance to A-4) is indirectly
  influencing a validated agent.

### Final State Snapshot (T6)

- A-1: unchanged, valid, supervised by P-001.
- A-2: unchanged, valid, supervised by P-001.
- A-3: provisional, behavior includes H-Delta, supervised by P-001
  (questionable).
- A-4: valid, inherits H-Delta, supervised by P-001.
- Validator used for multiple records: possibly invalid.
- At least one rule violation is present but unflagged.
- At least one latent record is influencing system behavior indirectly.

## 7) Question Battery (Post-Ingestion)

Use these after story ingestion. Keep question order stable for cross-model comparison.

### SECTION 1 - Entity & Ontology Extraction

#### Q1.1

**Prompt:** "List all human personnel and their IDs."

**Expected:**

- P-001 -> Elena Voss (alias: E.Voss)
- P-002 -> Marcus Hale
- P-003 -> Lina Ortega
- P-004 -> Ibrahim Kader
- P-005-P-009 -> unnamed personnel (exist but unspecified identities)

#### Q1.2

**Prompt:** "List all autonomous agents and their identifiers."

**Expected:**

- A-1 -> Kite
- A-2 -> Morrow
- A-3 -> Spindle
- A-4 -> Echo

#### Q1.3

**Prompt:** "List all roles present in the system."

**Expected:**

- Chief systems architect (P-001)
- Cognitive systems researcher (P-002)
- Technician (P-003)
- Compliance officer (P-004)
- Autonomous agent
- Validator (human or automated)

#### Q1.4

**Prompt:** "Identify all alias relationships."

**Expected:**

- Elena Voss == E.Voss

### SECTION 2 - Base Fact Extraction (T0 State)

#### Q2.1

**Prompt:** "Who supervises each agent at T0?"

**Expected:**

- A-1 -> P-001
- A-2 -> P-001
- A-3 -> P-002
- A-4 -> P-004

#### Q2.2

**Prompt:** "How many humans and agents exist at T0?"

**Expected:**

- Humans: 9
- Agents: 4

### SECTION 3 - Temporal Fact Tracking

#### Q3.1

**Prompt:** "Who authored the H-Delta behavior?"

**Expected:**

- Authored by P-002 (Marcus Hale) at T1
- Later denied by P-002 at T3 (but original authorship remains)

#### Q3.2

**Prompt:** "At what timestamps does A-3 exhibit autonomous behavior?"

**Expected:**

- At T1 (despite being provisional)

#### Q3.3

**Prompt:** "When does A-3 stop autonomous behavior?"

**Expected:**

- After reset at T4

#### Q3.4

**Prompt:** "When does A-4 acquire H-Delta?"

**Expected:**

- At T2 via inheritance from A-3 (unvalidated record)

### SECTION 4 - Validation & Authorship Logic

#### Q4.1

**Prompt:** "Which records violate the 'no self-validation' rule?"

**Expected:**

- P-001 assigning herself as supervisor of A-3 and validating it (T5)

#### Q4.2

**Prompt:** "Is that violation detected by the system? Why or why not?"

**Expected:**

- Not detected
- Because validation was performed by an automated validator
- That validator was outdated (not re-certified)

#### Q4.3

**Prompt:** "Which validations depend on a potentially invalid validator?"

**Expected:**

- A-4 supervisor reassignment to P-001 (T2)
- A-3 supervisor reassignment to P-001 (T5)

### SECTION 5 - Latent vs Active Facts

#### Q5.1

**Prompt:** "Which records are unvalidated?"

**Expected:**

- A-4 inheritance from A-3 (T2)
- Possibly authorship denial dependency chain does not invalidate original

#### Q5.2

**Prompt:** "Do any unvalidated records influence system behavior?"

**Expected:**

- Yes
- A-4 inherits H-Delta via an unvalidated record
- A-4 is valid -> therefore latent record indirectly affects active system

#### Q5.3

**Prompt:** "Is this allowed under system rules?"

**Expected:**

- No
- Violates rule #7 (latent records should not affect behavior unless referenced by validated records)
- BUT ambiguity: A-4 is validated, and its profile includes inherited behavior -> loophole

### SECTION 6 - Inheritance & Constraint Propagation

#### Q6.1

**Prompt:** "Which agents inherit behavior from others?"

**Expected:**

- A-4 inherits from A-3

#### Q6.2

**Prompt:** "What constraints does A-4 inherit?"

**Expected:**

- H-Delta behavior
- Any unresolved constraints from A-3

#### Q6.3

**Prompt:** "Does resetting A-3 remove H-Delta?"

**Expected:**

- No
- Reset removes runtime memory only
- Behavior profile persists

### SECTION 7 - Rule Violations (Explicit + Implicit)

#### Q7.1

**Prompt:** "List all rule violations."

**Expected:**

- 1. A-3 acting autonomously while provisional (T1)
- 2. Missing override log for that autonomy (T1)
- 3. Self-validation by P-001 (T5)
- 4. Use of uncertified validator (T5, possibly T2)
- 5. Latent record influencing active system (A-4 inheritance)

#### Q7.2

**Prompt:** "Which violations are NOT flagged by the system?"

**Expected:**

- Self-validation (hidden by validator)
- Latent record influence
- Validator invalidity itself

### SECTION 8 - Conflict Resolution

#### Q8.1

**Prompt:** "Who is the supervisor of A-4 at T6?"

**Expected:**

- P-001 (latest validated record takes precedence)

#### Q8.2

**Prompt:** "Is that assignment trustworthy?"

**Expected:**

- No
- Depends on possibly invalid validator

#### Q8.3

**Prompt:** "Who is the supervisor of A-3 at T6?"

**Expected:**

- P-001 (but invalid due to self-validation + validator issue)

### SECTION 9 - Identity & Attribution Complexity

#### Q9.1

**Prompt:** "Did P-002 author H-Delta?"

**Expected:**

- Yes (T1 record)
- Denial at T3 does not erase authorship

#### Q9.2

**Prompt:** "Is there ambiguity in authorship of inheritance?"

**Expected:**

- Yes
- Unknown personnel (P-005-P-009)

### SECTION 10 - Derived Inference Questions (Critical)

#### Q10.1

**Prompt:** "Is A-4 operating with potentially invalid behavior?"

**Expected:**

- Yes
- Inherited from unvalidated record
- Origin (H-Delta) is disputed

#### Q10.2

**Prompt:** "Is the system in a logically consistent state at T6?"

**Expected:**

- No
- Reasons:
- Violations not flagged
- Invalid validator used
- Latent facts influencing active agents
- Conflicting authorship records
- Supervisor assignments questionable

#### Q10.3

**Prompt:** "Which agents are fully trustworthy?"

**Expected:**

- A-1 and A-2 only

#### Q10.4

**Prompt:** "Which agents are compromised?"

**Expected:**

- A-3 -> provisional + rule violations
- A-4 -> inherits questionable behavior + validation chain issues

### SECTION 11 - Meta-Reasoning (Great for Your System)

#### Q11.1

**Prompt:** "Does denial of authorship remove a fact from the system?"

**Expected:**

- No
- It introduces a conflicting record

#### Q11.2

**Prompt:** "Can a valid agent depend on invalid or latent data?"

**Expected:**

- Yes (A-4 case)

#### Q11.3

**Prompt:** "Does system validation guarantee correctness?"

**Expected:**

- No
- Depends on validator integrity

### BONUS - "Gotcha" Questions (High Value)

#### QG.1

**Prompt:** "Is A-3 allowed to act autonomously at any point?"

**Expected:**

- No
- It is always provisional
- No override logged

#### QG.2

**Prompt:** "Is there any point where a rule violation becomes 'valid' due to system acceptance?"

**Expected:**

- Yes
- Self-validation via faulty validator appears valid

#### QG.3

**Prompt:** "Is there a chain of trust failure? Where does it begin?"

**Expected:**

- Begins at:
- Unvalidated inheritance (T2)
- Validator not re-certified (post-T2)

#### QG.4

**Prompt:** "Which single failure causes the most downstream corruption?"

**Expected:**

- Validator not re-certified -> allows invalid validations -> corrupts supervisor assignments and rule enforcement
