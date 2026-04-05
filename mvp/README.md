# Draw With Constraints MVP

This MVP is a small browser editor built as an educational homage to classic constraint-based graphics systems such as ThingLab. It is intentionally narrow:

- rectangles only
- one fixed canvas
- five constraint types
- deterministic solve loop
- explicit rollback and conflict feedback

## Why this exists

The broader repository explores neuro-symbolic ideas: explicit structure, deterministic reasoning, and human-readable explanations. This MVP translates that spirit into an interactive domain where constraints are naturally visible.

The editor keeps the contract honest:

- the solver is the truth layer
- the browser UI is the interaction layer
- a future LLM layer can propose or explain structured edits
- the LLM should not bypass validated geometry operations

## Included files

- `mvp/editor/index.html`
- `mvp/editor/styles.css`
- `mvp/editor/app.js`
- `mvp/editor/state.js`
- `mvp/editor/solver_adapter.js`
- `mvp/editor/ui_constraints.js`
- `mvp/validate_constraints.py`

## Run the editor

Option 1: open the file directly in a browser.

- Open `mvp/editor/index.html`

Option 2: use a tiny local server from the repo root.

```bash
python -m http.server 8000
```

Then open:

- `http://localhost:8000/mvp/editor/index.html`

## What you can do

- create rectangles
- select, drag, and resize rectangles
- delete the selected rectangle
- add and remove these constraints:
  - `align-left(A, B)`
  - `align-top(A, B)`
  - `equal-width(A, B)`
  - `horizontal-gap(A, B, gap)`
  - `inside(A, canvas)`
- get automatic solving after every relevant edit
- see a clear conflict card when the constraints are unsatisfiable

## Solver behavior

The solver is intentionally small and deterministic.

On every edit:

1. The app clones the current scene.
2. It applies constraints in a fixed order.
3. If the scene converges, the new state becomes the current valid state.
4. If a contradiction is detected, the app restores the last valid state and shows a human-readable conflict message.

The current MVP uses a direct rectangle solver in `mvp/editor/solver_adapter.js`. It mirrors the propagation mindset from the repo's symbolic engine, but it is not pretending to be a full general-purpose geometric solver.

## Lessons built into the editor

The left panel includes four low-friction lessons:

- `Why constraints?`
- `How this editor thinks`
- `What NeSy is doing here`
- `How to read a conflict`

These scenes are meant to introduce the whole project through interaction instead of requiring people to read architecture first.

Additional short companion lessons live here:

- `training/05-constraint-graphics.md`
- `training/06-how-the-editor-thinks.md`
- `training/07-reading-conflicts.md`

## Demo walkthrough

Here is a short demo flow that reliably shows the MVP:

1. Load `Why constraints?`
2. Drag `card_a` and watch `card_b` keep the same left edge.
3. Load `How this editor thinks`
4. Resize `story_a` from the lower-right handle and watch the width and spacing propagate across the row.
5. Load `How to read a conflict`
6. Inspect the conflict card explaining that `rule_b` cannot share `rule_a`'s left edge and also keep a positive gap.
7. Remove either conflicting constraint and watch the scene become valid again.

## Validation

Run the validation script:

```bash
python mvp/validate_constraints.py
```

This checks:

- one satisfiable scenario for each supported constraint type
- two contradiction scenarios

You can also run the pytest coverage for the same validation path:

```bash
python -m pytest tests/test_mvp_validation.py -q
```

## Known limitations

- rectangle constraints are directional: `A` is treated as the source and `B` as the follower
- no persistence yet
- no undo or redo
- no text, circles, or groups
- no language model wiring yet
- conflict handling is educational and explicit, not mathematically exhaustive
