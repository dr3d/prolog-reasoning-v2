# Prototypes Workspace

This folder is for exploratory builds that are useful to test, but not yet part
of the core product path.

Use it to keep experiments visible and runnable without mixing uncertain work
into mainline docs or runtime code.

## Status Lanes

- `experimental`: early spike, assumptions still moving.
- `active`: currently being exercised and compared against success criteria.
- `archived`: kept for reference; not actively maintained.

## Folder Layout

```text
prototypes/
  experimental/
  active/
  archived/
  PROTOTYPE_TEMPLATE.md
```

Each prototype should live in exactly one lane directory at a time.

## Required Per-Prototype Files

Every prototype folder should include a local `README.md` with:

1. Problem statement (what gap this explores).
2. Scope (explicitly what is in/out).
3. How to run it.
4. Success criteria (2-4 measurable checks).
5. Known risks and limitations.
6. Promotion decision (`stay prototype`, `promote`, or `archive`).

Use [PROTOTYPE_TEMPLATE.md](PROTOTYPE_TEMPLATE.md) as the starting point.

## Promotion Rules

Promote prototype work to core docs/code only when all are true:

1. Clear user value is demonstrated in at least one realistic scenario.
2. Behavior is repeatable with a documented run path.
3. Tests or validation checks exist at the right layer.
4. Maintenance owner is clear.

If a prototype stalls or fails criteria, move it to `archived/` with a short
final note.

## Timeboxing

Default timebox: one week per major spike before a go/no-go decision.

If no decision is reached, document the blocker and either:

1. Narrow the scope and run one more timebox, or
2. Archive and move on.
