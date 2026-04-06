# Constraint Editor MVP Playbook

Status: Product concept and execution playbook
Audience: Founders, builders, early users, collaborators

## One-Line Vision

Build a modern vector editor where geometry behaves like a spreadsheet: objects can be linked by rules, not just nudged by hand.

## 30-Second Pitch

Most design tools are manual and fragile. Move one object, then spend five minutes re-aligning everything else.

This MVP makes layout relationships explicit:

- Keep these cards evenly spaced.
- Keep this logo lockup ratio fixed.
- Keep this title centered between margins.

Change one value and the whole design updates predictably.

## "Wow, I Can Use This" Demo Set

Each demo should complete in less than 90 seconds.

### Demo 1: Marketing Card Grid

- Create 3 cards.
- Add constraints: equal width, equal height, equal spacing.
- Change one card width.
- Result: all cards update and spacing remains consistent.

### Demo 2: Responsive Social Variants

- One design in a 1:1 artboard.
- Add constraints: pin header, keep center object centered, maintain logo ratio.
- Switch to 4:5 and 16:9 artboards.
- Result: layout adapts without manual rebuild.

### Demo 3: Brand Lockup Guardrail

- Logo + wordmark + tagline group.
- Add constraints: fixed spacing ratios and alignment rules.
- Drag elements incorrectly.
- Result: system corrects or reports rule conflict clearly.

## MVP Scope (Deliberately Small)

### Geometry Primitives

- Point
- Line
- Rectangle
- Circle
- Text box (basic)

### Constraint Types (V1)

- Align left/center/right
- Align top/middle/bottom
- Equal width/height
- Equal spacing
- Fixed distance
- Lock aspect ratio
- Horizontal/vertical

### Variable/Parameter System

- Named values: `margin`, `gutter`, `card_width`
- Constraint expressions can reference names
- Editing one variable updates all dependent geometry

### Required UX Panels

- Layers/objects panel
- Constraints panel
- Variables panel
- Diagnostics panel (under-constrained, over-constrained, contradiction)

## Solver + LLM Contract

Keep responsibilities strict.

### Deterministic Core (Truth)

- Applies constraints
- Computes known state closure
- Computes degrees of freedom
- Detects contradictions

### LLM Layer (Intent and Explanation)

- Translates plain language into structured edits
- Suggests missing constraints
- Explains failures in plain language

LLM never directly mutates geometry without validated structured operations.

## 6-Week Build Plan

### Week 1: Canvas + Object Model

- Create basic drawing canvas and selectable objects
- Implement move/resize interactions
- Persist scene JSON

Exit criteria:

- Can create and edit primitives reliably.

### Week 2: Constraint Data Model + Basic Rules

- Implement constraint schema
- Add align/equal/fixed-distance constraints
- Add first deterministic propagation pass

Exit criteria:

- Rule updates survive drag operations.

### Week 3: DoF and Diagnostics

- Show per-object and global degree-of-freedom indicators
- Add contradiction messages and actionable diagnostics

Exit criteria:

- User can tell why a scene is unstable or conflicting.

### Week 4: Variables and Formula-Like Editing

- Add named variables panel
- Bind constraints to variables
- Live recompute when variables change

Exit criteria:

- One variable change can drive multi-object update.

### Week 5: LLM Assist (Optional but Valuable)

- Add natural-language command box
- Convert user intent to structured constraint ops
- Add confirmation preview before apply

Exit criteria:

- "Make these evenly spaced" works on selected objects.

### Week 6: Polish + Demo Packs

- Package 3 demo templates (card grid, social variants, brand lockup)
- Add onboarding checklist and short in-app tips
- Record 60-90 second demo clips

Exit criteria:

- New user gets first "wow" in less than 3 minutes.

## Low-Friction Onboarding Script

This should be visible on first run.

1. Draw two rectangles.
2. Click "Equal Width".
3. Add third rectangle and click "Equal Spacing".
4. Change `card_width` variable from 240 to 320.
5. See full layout update instantly.

## Early Monetizable Use Cases

- Social media asset packs
- Brand kits and lockups
- Presentation templates
- Ecommerce listing image families

## Risks and Mitigations

### Risk: Constraint UX feels too technical

Mitigation:

- Keep default actions visual first, formulas optional.

### Risk: Over-constrained scenes frustrate users

Mitigation:

- Diagnostics panel always offers "fix options".

### Risk: LLM actions feel unpredictable

Mitigation:

- Require structured preview and user confirmation before apply.

## Track 2 MVP: Rules of Music (Same Engine, New Domain)

Use the same propagation architecture for musical constraints.

### Concept

- Objects: notes, chords, bars, sections
- Constraints: key signature, scale membership, harmonic progression bounds, voice-leading limits
- DoF: remaining harmonic/rhythmic options

### Example "Wow"

- User sets: "8-bar progression in C minor, avoid parallel fifths, keep melody range within one octave"
- System proposes valid options and flags violations with explanations.

### Why it matters

- Proves the engine is domain-general.
- Opens creative tooling beyond graphics.

## Immediate Next Tasks

1. Define JSON schema for drawing entities + constraint ops.
2. Build first interactive canvas with 3 primitive types.
3. Integrate current propagation engine behind canvas edits.
4. Produce Demo 1 (marketing card grid) end to end.
