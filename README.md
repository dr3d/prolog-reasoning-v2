# Prolog Reasoning v2

**Memories are timestamped. Facts are not. Hallucinations begin when facts collapse into memories.**

Prolog Reasoning v2 is a local-first neuro-symbolic reliability layer for LLM agents. It combines deterministic symbolic reasoning, structured validation, and human-readable explanations, then exposes that through practical integration paths like MCP.

[![Tests](https://img.shields.io/badge/tests-68%20passed-brightgreen)](tests/)
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

## What This Project Is

This repo is best understood through four pillars:

1. **Deterministic reasoning**
   A pure Python Prolog interpreter answers the same query the same way and can show its proof steps.

2. **Validation before belief**
   Natural-language inputs are grounded into structured representations and checked before they are allowed to act like facts.

3. **Failure explanations for humans**
   The system tries to teach when something is wrong instead of returning cryptic failure modes.

4. **Practical integration**
   MCP, agent-facing skill wrappers, demos, and manifests make the symbolic layer usable from real agent workflows.

## What Is Real Today

These parts are implemented and working:

- Prolog engine with unification, backward chaining, backtracking, and built-ins in [src/engine/core.py](src/engine/core.py)
- Structured IR and schema validation in [src/ir/schema.py](src/ir/schema.py)
- Semantic grounding and semantic validation pipeline in [src/parser/semantic.py](src/parser/semantic.py)
- Failure explanation layer in [src/explain/failure_translator.py](src/explain/failure_translator.py)
- MCP server for local LLM integration in [src/mcp_server.py](src/mcp_server.py)
- Constraint propagation engine in [src/engine/constraint_propagation.py](src/engine/constraint_propagation.py)
- Test suite currently passing: `68 passed`

What is still simplified or partly mocked:

- some demo and agent paths use stub knowledge-base loading rather than full `.pl` parsing
- the default semantic grounding path still includes a mock LLM mode
- the graphics editor is exploratory and not the mainline product focus

That is intentional to state plainly: the core symbolic layer is real, but not every surrounding integration path is equally mature yet.

## Quick Start

```bash
git clone <repo>
cd prolog-reasoning-v2
pip install -r requirements.txt

# Verify the current baseline
python -m pytest tests -q

# Try semantic grounding
python scripts/demonstrate_semantic.py

# Try failure explanations
python scripts/demonstrate_failures.py

# Try the agent-facing skill demo
python scripts/demonstrate_agent.py

# Run benchmark evaluation
python data/evaluate.py
```

## Choose Your Path

### Use It

- Ask natural-language questions through `SemanticPrologSkill`
- Run the MCP server for local LLM tools via [src/mcp_server.py](src/mcp_server.py)
- Use the constraint propagation runner via [src/engine/runner.py](src/engine/runner.py)

### Understand It

- Architecture: [architecture.md](architecture.md)
- Semantic grounding: [docs/semantic-grounding.md](docs/semantic-grounding.md)
- Failure explanations: [docs/failure-explanations.md](docs/failure-explanations.md)
- LM Studio + MCP guide: [docs/lm-studio-mcp-guide.md](docs/lm-studio-mcp-guide.md)
- Session summaries: [sessions.md](sessions.md) and [docs/sessions/parts/2026-part-01.md](docs/sessions/parts/2026-part-01.md)

### Build On It

- Current implementation status: [status.md](status.md)
- Planned work: [roadmap.md](roadmap.md)
- Ontology routing spec: [docs/ontology-context-routing-spec.md](docs/ontology-context-routing-spec.md)
- Memory ingestion notes: [docs/memory-ingestion-and-revision-notes.md](docs/memory-ingestion-and-revision-notes.md)
- Pre-thinker control plane: [docs/pre-thinker-control-plane.md](docs/pre-thinker-control-plane.md)

## Architecture Snapshot

The main execution path is:

1. Natural language arrives.
2. Semantic grounding converts it into structured IR.
3. Validation checks whether the representation is grounded and coherent.
4. The symbolic engine resolves the query deterministically.
5. Explanation and failure layers translate the result back into something an agent or human can use.

This keeps neural and symbolic responsibilities separate:

- language models help interpret intent
- symbolic structures hold explicit facts and rules
- the engine decides truth

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
docs/            Design docs, guides, reviews, and session notes
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

- [docs/constraint-editor-mvp-playbook.md](docs/constraint-editor-mvp-playbook.md)

## Current Status

The project has a working symbolic core, validation layer, failure-explanation layer, MCP server, and constraint propagation engine.

The next serious work is around:

- temporal reasoning
- dependency separation
- multi-session isolation
- ontology-aware routing
- memory ingestion and revision workflows

See [status.md](status.md), [roadmap.md](roadmap.md), and [sessions.md](sessions.md) for the current planning picture.

## License

MIT License. See [LICENSE](LICENSE).
