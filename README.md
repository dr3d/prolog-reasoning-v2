# Prolog Reasoning v2

**Memories are timestamped. Facts are not. Hallucinations begin when facts collapse into memories.**

Prolog Reasoning v2 is a local-first deterministic logic layer for LLM agents. It combines symbolic reasoning, structured validation, and human-readable explanations, then exposes that through practical integration paths like MCP. The longer-term direction is to pair that logic layer with a classifier-driven fact intake pipeline for curated symbolic memory.

Here, `local-first` means the core reasoning loop can run on your own machine with local files, local models, and local tooling first, rather than depending on a cloud service as the source of truth.

[![Tests](https://img.shields.io/badge/tests-105%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

![Two memory systems, two inference systems](infographics/02-memory-and-inference-map.png)

## Why This Exists

LLMs are good at language, but weak at durable truth.

- Summaries drift.
- Retrieval approximates.
- Model weights blur facts under pressure.

This repository explores a stricter contract:

- use symbolic structure for facts and rules
- use deterministic execution for truth conditions
- use natural language only as an interface layer
- explain failures instead of hiding them

## Help It Grow

If you want to help this repo "sprout legs," start here:

- Collaboration map and idea prompts: [docs/research/collaboration-map.md](docs/research/collaboration-map.md)

If you have a great idea to improve it: pull the repo, load it up with your AI
of choice, play around, ask it to explain things, try your own ideas, and map
the dead ends and unexplored crevices that lead to better solutions.

We are especially interested in collaborators who want to improve:

- grounding quality (NL -> IR)
- fact intake and memory curation
- reproducible benchmarks
- real domain case studies
- agent workflow reliability

## What This Project Is

This repo is best understood in three layers:

1. **Deterministic logic layer**
   A pure Python Prolog interpreter and a deterministic propagation engine answer the same inputs the same way and can show why.

2. **Fact intake / memory curation layer**
   Natural-language inputs are classified, grounded, validated, and eventually routed toward hard fact, tentative memory, session state, preference, or rejection.

3. **Agent integration layer**
   MCP, agent-facing skill wrappers, LM Studio workflows, and install playbooks make the symbolic layer callable from real agent systems.

## What Is Real Today

These parts are implemented and working:

- Prolog engine with unification, backward chaining, backtracking, and built-ins in [src/engine/core.py](src/engine/core.py)
- Structured IR and schema validation in [src/ir/schema.py](src/ir/schema.py)
- Semantic grounding and semantic validation pipeline in [src/parser/semantic.py](src/parser/semantic.py)
- Failure explanation layer in [src/explain/failure_translator.py](src/explain/failure_translator.py)
- MCP server for local LLM integration in [src/mcp_server.py](src/mcp_server.py)
- Statement classification layer in [src/parser/statement_classifier.py](src/parser/statement_classifier.py)
- Constraint propagation engine in [src/engine/constraint_propagation.py](src/engine/constraint_propagation.py)
- Test suite currently passing: `105 passed`

Runtime boundary (important for reviewers):

- MCP supports runtime in-memory fact mutation (`assert_fact`, `bulk_assert_facts`, `retract_fact`, `reset_kb`) for scenario simulation.
- Runtime mutations are process-local and reset to `prolog/core.pl`; they are not durable journaled memory writes.
- Pre-thinker, ontological routing, and clarification-eagerness are documented future/control tracks and are not enabled as default runtime behavior.

What is still simplified or partly mocked:

- some demo and agent paths use stub knowledge-base loading rather than full `.pl` parsing
- the default semantic grounding path still includes a mock LLM mode
- the write path for durable memory is still a design/early-engineering area rather than a finished subsystem
- the graphics editor is exploratory and not the mainline product focus

That is intentional to state plainly: the core symbolic layer is real, but not every surrounding integration path is equally mature yet.

## Quick Start

```bash
git clone <repo>
cd prolog-reasoning-v2
pip install -r requirements.txt

# Verify the current baseline
python -m pytest tests -q

# Quick docs drift check
python scripts/check_docs_consistency.py

# PR1 smoke (Windows/PowerShell; includes live MCP surface by default)
./scripts/pr1_smoke.ps1
```

Then start with a markdown walkthrough:

- Chat-first MCP playbook (no coding required): [docs/mcp-chat-playbooks.md](docs/mcp-chat-playbooks.md)
- LM Studio MCP setup guide: [docs/lm-studio-mcp-guide.md](docs/lm-studio-mcp-guide.md)

If you want runnable Python demos after that:

```bash
python scripts/demonstrate_semantic.py
python scripts/demonstrate_failures.py
python scripts/demonstrate_agent.py
python data/evaluate.py
```

## Choose Your Path

### Use It

- Ask natural-language questions through MCP tools (`query_prolog`, `query_logic`, `query_rows`)
- Run the MCP server for local LLM tools via [docs/lm-studio-mcp-guide.md](docs/lm-studio-mcp-guide.md)
- Use the constraint propagation runner via [src/engine/runner.py](src/engine/runner.py)
- Configure Hermes agent skill usage with [HERMES-AGENT-INSTALL.md](HERMES-AGENT-INSTALL.md)
- Configure OpenClaw agent skill usage with [OPENCLAW-AGENT-INSTALL.md](OPENCLAW-AGENT-INSTALL.md)

### Understand It

- Docs map: [docs/README.md](docs/README.md)
- Architecture: [architecture.md](architecture.md)
- Semantic grounding (legacy reference): [docs/legacy/semantic-grounding.md](docs/legacy/semantic-grounding.md)
- Failure explanations: [docs/failure-explanations.md](docs/failure-explanations.md)
- LM Studio + MCP guide: [docs/lm-studio-mcp-guide.md](docs/lm-studio-mcp-guide.md)
- MCP chat playbooks (copy/paste): [docs/mcp-chat-playbooks.md](docs/mcp-chat-playbooks.md)
- Session summaries: [sessions.md](sessions.md) (long-form session logs stay local-only until explicitly published)

### Build On It

- Current implementation status: [status.md](status.md)
- Planned work: [roadmap.md](roadmap.md)
- Unified intake/memory/write spec: [docs/fact-intake-pipeline.md](docs/fact-intake-pipeline.md)
- Split-note compatibility stubs: [docs/memory-ingestion-and-revision-notes.md](docs/memory-ingestion-and-revision-notes.md), [docs/write-path-spec.md](docs/write-path-spec.md)
- LM Studio classifier evaluation: [docs/research/lmstudio-classifier-matrix.md](docs/research/lmstudio-classifier-matrix.md)
- Pre-thinker LoRA playbook: [docs/research/prethinker-lora-playbook.md](docs/research/prethinker-lora-playbook.md)
- Collaboration lanes and idea prompts: [docs/research/collaboration-map.md](docs/research/collaboration-map.md)
- Pre-thinker control plane: [docs/pre-thinker-control-plane.md](docs/pre-thinker-control-plane.md)
- Ontology routing spec (secondary track): [docs/secondary/ontology-context-routing-spec.md](docs/secondary/ontology-context-routing-spec.md)

## Architecture Snapshot

The main execution path is:

1. Natural language arrives.
2. Semantic grounding converts it into structured IR.
3. Validation checks whether the representation is grounded and coherent.
4. The symbolic engine resolves the query deterministically.
5. Explanation and failure layers translate the result back into something an agent or human can use.

This keeps neural and symbolic responsibilities separate:

- language models help interpret intent
- intake logic decides what deserves symbolic treatment
- symbolic structures hold explicit facts and rules
- the engine decides truth and consequences

## Repo Map

```text
src/
  engine/        Prolog interpreter and propagation engine
  ir/            Structured intermediate representation
  compiler/      IR to Prolog conversion
  parser/        Natural-language grounding
  explain/       Proof traces and failure explanations
  validator/     Semantic validation
  mcp_server.py  MCP integration

scripts/         Demos and utility scripts
tests/           Unit and integration tests
data/            Benchmarks and evaluation artifacts
docs/            Design docs, guides, diagrams, and session notes
training/        Beginner-facing learning materials
prolog/          Knowledge-base files
mvp/             Experimental constraint-graphics prototype
```

## Local LLM Integration

To expose the system to a local LLM through MCP:

```bash
python src/mcp_server.py --stdio
```

For LM Studio, the app should launch the server for you from `mcp.json`. Replace `<PYTHON_EXE>` with the Python interpreter from the environment where you installed this repo's dependencies, and replace `<REPO_ROOT>` with wherever you cloned this repo:

```json
{
  "mcpServers": {
    "prolog-reasoning": {
      "command": "<PYTHON_EXE>",
      "args": [
        "<REPO_ROOT>\\src\\mcp_server.py",
        "--stdio",
        "--kb-path",
        "<REPO_ROOT>\\prolog\\core.pl"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

LM Studio then owns the stdio process; you do not need to keep `mcp_server.py --stdio` running in a separate terminal.

If you run the repo's MCP demo scripts that call LM Studio's HTTP API (for
example `scripts/demonstrate_*_agent_mcp.py`), and LM Studio API auth is
enabled, you must provide a token:

```bash
# PowerShell
$env:LMSTUDIO_API_KEY = "<YOUR_LM_STUDIO_API_TOKEN>"
python scripts/demonstrate_rule_table_agent_mcp.py
```

Or pass it directly:

```bash
python scripts/demonstrate_rule_table_agent_mcp.py --api-key "<YOUR_LM_STUDIO_API_TOKEN>"
```

Relevant references:

- [docs/lm-studio-mcp-guide.md](docs/lm-studio-mcp-guide.md)
- [training/04-lm-studio-mcp.md](training/04-lm-studio-mcp.md)

## Constraint Propagation

The repository also includes a deterministic constraint propagation layer for state and domain reasoning.

It supports:

- known-state fixed-point propagation
- degree-of-freedom propagation via domain narrowing
- contradiction detection when feasible domains collapse

Try the example:

```bash
python src/engine/runner.py --propagate --problem-json data/propagation_example.json
```

This is the foundation behind the repo's experimental constraint-graphics direction.

## Experimental Graphics Editor

There is an exploratory constraint-based graphics editor in [mvp](mvp/). It is not the main focus of the repository, but it demonstrates how the same deterministic philosophy can be applied in an interactive visual domain.

Related doc:

- [docs/prototypes/constraint-editor-mvp-playbook.md](docs/prototypes/constraint-editor-mvp-playbook.md)

## Current Status

The project has a working deterministic logic layer, validation layer,
failure-explanation layer, MCP server, classifier, and constraint propagation
engine.

The next serious work is around:

- fact intake and memory curation
- predicate identification and canonicalization
- tentative memory and revision workflows
- contradiction handling
- later, stateless pre-thinker experiments

See [status.md](status.md), [roadmap.md](roadmap.md), and [sessions.md](sessions.md) for the current planning picture.

## License

MIT License. See [LICENSE](LICENSE).
