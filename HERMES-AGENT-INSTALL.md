# Hermes Agent Install Instructions

This is an agent-execution playbook, not a general user tutorial.

Read this file fully before taking action. It is written for an agent with filesystem and shell tools that must configure `prolog-reasoning-v2` for Hermes.

The goal is to make `prolog-reasoning-v2` discoverable as a Hermes skill and add the smallest useful Hermes prefill so the agent is more likely to actually use it.

This file is intentionally practical:
- install the skill,
- verify it is in the right place,
- add a minimal Hermes prefill,
- and smoke-test the integration.

If you are a human reading this, treat it as a precise checklist an agent can execute end to end.

## What This Installs

This repo can help Hermes in two different ways:

1. As a skill folder discovered from `~/.hermes/skills/prolog-reasoning-v2`
2. As a small behavioral prefill that biases the agent to use the skill for symbolic questions

Important current limitation:
- the repo has a root `SKILL.md`,
- but Hermes may still need a behavioral nudge before it consistently reaches for the skill,
- especially for factual questions that the base model is tempted to answer from memory.

Installing the repo gives Hermes access to the skill.
The prefill does not add logic. It makes the agent more likely to load and use the installed skill.

Important maintenance rule:
- `SKILL.md` is the behavioral source of truth.
- The prefill should stay tiny and generic.
- Do not duplicate detailed policy or capability lists in the prefill.

This guide recommends a static prefill, not a computed manifest.
Reason:
- no regenerate-on-write loop,
- no stale manifest debugging,
- no dependency on KB summaries to get the routing behavior,
- and much lower setup friction.

## Step 1: Verify Python

```bash
python3 --version
```

Required:
- Python 3.9 or higher

If `python3` is missing, stop and tell the user Python is required.

## Step 2: Install Or Update The Skill Folder

Check whether the skill already exists:

```bash
ls ~/.hermes/skills/prolog-reasoning-v2 2>/dev/null && echo EXISTS || echo MISSING
```

If `MISSING`, install it:

```bash
mkdir -p ~/.hermes/skills
git clone <REPO_URL> ~/.hermes/skills/prolog-reasoning-v2
```

If `EXISTS`, update it:

```bash
cd ~/.hermes/skills/prolog-reasoning-v2
git pull
```

Do not continue until this file exists:

```bash
ls ~/.hermes/skills/prolog-reasoning-v2/SKILL.md
```

## Step 3: Install Python Dependencies

From inside the skill repo:

```bash
cd ~/.hermes/skills/prolog-reasoning-v2
python3 -m pip install -r requirements.txt
```

If the user prefers a virtual environment, that is fine. Hermes should then be configured to use the Python interpreter from that environment when launching any helper commands.

## Step 4: Smoke-Test The Repo

From the repo root:

```bash
cd ~/.hermes/skills/prolog-reasoning-v2
python3 src/mcp_server.py --test
```

Expected result:
- the server initializes,
- the canonical MCP tools are listed (query/query_rows/assert/retract/reset/classify/list/explain/info),
- and the command exits cleanly.

If this fails, stop and fix the repo installation before editing Hermes config.

## Step 4.5: Fast MCP Wiring (Recommended)

If the repo is already cloned and dependencies are installed, use the installer
script instead of editing `~/.hermes/config.yaml` by hand:

```bash
cd ~/.hermes/skills/prolog-reasoning-v2
python3 scripts/install_hermes_mcp.py
```

What it does:
- adds/updates `mcp_servers.prolog_reasoning` in `~/.hermes/config.yaml`
- points Hermes at this repo's `src/mcp_server.py`
- sets `--kb-path` to this repo's `prolog/core.pl`
- creates a timestamped config backup before writes

Optional dry run:

```bash
python3 scripts/install_hermes_mcp.py --dry-run
```

You can still follow the manual config steps below if you prefer.

## Step 5: Create The Minimal Prefill File

Create:

```bash
mkdir -p ~/.hermes
cat > ~/.hermes/prolog-reasoning-v2-prefill.json << 'EOF'
[
  {
    "role": "system",
    "content": "You have access to the prolog-reasoning-v2 skill. Use it for symbolic factual questions and candidate memory statements instead of defaulting to model memory."
  }
]
EOF
```

Verify the file:

```bash
python3 -m json.tool ~/.hermes/prolog-reasoning-v2-prefill.json >/dev/null && echo VALID || echo INVALID
```

If it is invalid JSON, fix it before continuing.

## Step 6: Wire Prefill Into Hermes Config

Check whether the config file exists:

```bash
ls ~/.hermes/config.yaml 2>/dev/null && echo EXISTS || echo MISSING
```

If `MISSING`, create:

```bash
cat > ~/.hermes/config.yaml << 'EOF'
agent:
  prefill_messages_file: ~/.hermes/prolog-reasoning-v2-prefill.json
EOF
```

If `EXISTS`, inspect whether `prefill_messages_file` already exists under `agent:`:

```bash
grep -A2 "^agent:" ~/.hermes/config.yaml
```

Rules:
- `prefill_messages_file` must be nested under `agent:`
- do not append a second `agent:` block
- do not keep conflicting top-level `prefill_messages_file` keys

Desired shape:

```yaml
agent:
  prefill_messages_file: ~/.hermes/prolog-reasoning-v2-prefill.json
```

## Step 7: Restart Hermes And Run A Live Probe

Start a fresh Hermes session and try:

```text
Who is John's parent?
```

Good sign:
- Hermes reaches for the skill or its symbolic tools
- answer is grounded in the symbolic layer

Also try:

```text
My mother was Ann.
```

Good sign:
- Hermes treats this as a candidate fact to classify,
- does not answer it like a proved query,
- and does not claim it stored it unless a write path exists.

## Step 8: Use The Ingestion Test Pack

For a stronger evaluation, run the prompts in:

- `docs/agent-ingestion-tests.md`

This is the fastest way to see whether Hermes is:
- really querying before answering,
- distinguishing statement from question,
- respecting tentative memory,
- and recognizing correction cues.

## Current Reality Check

What should work today:
- skill discovery from the Hermes skills directory
- query/explain behavior when the agent decides to use the skill
- better trigger odds with a small behavioral prefill

Why this guide uses a static prefill instead of a manifest:
- the goal here is skill routing, not ambient KB introspection
- static instructions are enough to bias skill loading
- manifests can come later if you want entity-aware orientation on top of this

What is not fully live yet:
- durable natural-language fact insertion
- retract/supersede event handling through a finished write path
- guaranteed Hermes-side routing without prompt support

## Done

Tell the user:
- where the skill repo lives
- whether prefill was configured or intentionally skipped
- where the prefill file lives
- which Python interpreter Hermes should rely on for this repo
- whether the live probe behaved like query, ingestion, or memory fallback
