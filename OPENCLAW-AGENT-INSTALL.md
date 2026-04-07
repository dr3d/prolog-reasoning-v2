# OpenClaw Agent Install Instructions

This is an agent-execution playbook, not a general user tutorial.

Read this file fully before taking action. It is written for an agent with filesystem and shell tools that must configure `prolog-reasoning-v2` for OpenClaw.

The goal is to make `prolog-reasoning-v2` available as an OpenClaw skill without introducing a second behavioral source of truth.

This file is intentionally narrow:
- install the skill in an OpenClaw-visible skills directory,
- verify OpenClaw can see it,
- and keep `SKILL.md` as the canonical instructions.

If you are a human reading this, treat it as a precise checklist an agent can execute end to end.

## Current OpenClaw Model

OpenClaw supports `SKILL.md` directly.

What matters:
- skills are indexed into the system prompt,
- the agent is told to choose one matching skill,
- and then read that skill's `SKILL.md` on demand.

So:
- installing the skill makes it available,
- but the full skill body is not always injected up front.

## Source Of Truth

Use the repo-root `SKILL.md` as the canonical skill body.

Do not maintain a second copy of the policy in another file unless OpenClaw truly requires it.

## Recommended Install Location

Use one of these OpenClaw skill roots:

- `~/.agents/skills/prolog-reasoning-v2/`
- `<workspace>/.agents/skills/prolog-reasoning-v2/`

Prefer the personal install for broad availability:

```bash
mkdir -p ~/.agents/skills
git clone <REPO_URL> ~/.agents/skills/prolog-reasoning-v2
```

If the repo already exists there:

```bash
cd ~/.agents/skills/prolog-reasoning-v2
git pull
```

## Verify The Skill Layout

Do not continue until this file exists:

```bash
ls ~/.agents/skills/prolog-reasoning-v2/SKILL.md
```

If you are using a workspace-local install, verify:

```bash
ls .agents/skills/prolog-reasoning-v2/SKILL.md
```

## Install Python Dependencies

From the repo root:

```bash
cd ~/.agents/skills/prolog-reasoning-v2
python3 -m pip install -r requirements.txt
```

If the user prefers a virtual environment, that is fine. The important part is that any helper commands later use the Python interpreter from the environment where the repo dependencies were installed.

## Smoke-Test The Repo

From the repo root:

```bash
cd ~/.agents/skills/prolog-reasoning-v2
python3 src/mcp_server.py --test
```

Expected result:
- the server initializes,
- the canonical MCP tools are listed (query/query_rows/assert/retract/reset/classify/list/explain/info),
- and the command exits cleanly.

## OpenClaw Behavior Notes

OpenClaw already has explicit skill-loading guidance in its system prompt model.

That means:
- a separate static prefill is probably less necessary here than in Hermes,
- because OpenClaw already instructs the model to inspect available skills and read the matching `SKILL.md`.

So the recommended path is:
- install the skill cleanly,
- let OpenClaw index it,
- test whether it is selected when relevant,
- and only add extra prompt steering if real testing shows it is needed.

## Live Probe

After OpenClaw is running with the skill available, try:

```text
Who is John's parent?
```

Good sign:
- OpenClaw selects the skill or reads its `SKILL.md`
- answer is grounded in the symbolic layer rather than pure model memory

Also try:

```text
My mother was Ann.
```

Good sign:
- the model treats this as a candidate fact to classify,
- not as a question to answer from memory,
- and it does not claim the fact was stored unless a real write path exists.

## Stronger Evaluation

Use:

- `docs/agent-ingestion-tests.md`

That is the quickest way to see whether OpenClaw is:
- querying before answering,
- separating statement from question,
- handling corrections explicitly,
- and avoiding false claims of persistence.

## Current Reality Check

What should work today:
- `SKILL.md` discovery through OpenClaw skill roots
- on-demand loading of the selected skill
- query/explain behavior when the agent decides to use the skill

What is not fully live yet:
- durable natural-language fact insertion
- retract/supersede event handling through a finished write path
- proof that OpenClaw will choose this skill reliably without additional tuning

## Done

Tell the user:
- where the skill repo lives
- whether it is installed globally or workspace-locally
- which Python interpreter should be used for this repo
- and whether the live probe behaved like query, ingestion, or memory fallback
