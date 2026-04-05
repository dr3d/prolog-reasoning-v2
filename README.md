# Prolog Reasoning v2
Structured fact storage with backward-chaining inference to support deterministic reasoning in LLM agents.

[![Tests](https://img.shields.io/badge/tests-60%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

This is a research-grade implementation exploring how deterministic symbolic reasoning can address context decay in long-horizon agent memory.

## Why This Project

LLMs lose precision over long horizons:
- **Summaries degrade**: "Scott's family in Ohio" becomes "family in Midwest"
- **Vector stores approximate**: they answer "similar to?" rather than "is true?"
- **Model weights confabulate**: facts get blurred under recall pressure

This project stores hard facts in Prolog and derives answers through explicit inference:

```prolog
parent(john, alice).
parent(alice, bob).
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).

?- ancestor(john, bob).  % true (derived, never stored)
```

## Key Features

- **Lossless**: facts do not degrade through summarization
- **Deterministic**: the same query succeeds or fails the same way
- **Explainable**: answers can be traced through proof steps
- **Schema-safe**: IR validation prevents malformed structured facts
- **Composable**: rules derive new facts from stored ones
- **Agent-ready**: usable from MCP and agent frameworks

## Quick Start

```bash
# Clone and setup
git clone <repo>
cd prolog-reasoning-v2
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Try failure explanations
python scripts/demonstrate_failures.py

# Try natural language queries
python scripts/demonstrate_semantic.py

# Run benchmark evaluation
python data/evaluate.py

# Generate KB manifest for agents
python scripts/generate_manifest.py
```

## Natural Language Queries

The system supports natural language queries through semantic grounding:

```python
from src.parser.semantic import SemanticPrologSkill

skill = SemanticPrologSkill()
result = skill.query_nl("Who is John's parent?")
# Returns: success, bindings, explanation, confidence, proof traces
```

Supported query types:
- Variable queries: "Who is John's parent?"
- Fact checks: "Is Alice allowed to read?"
- Assertions: "John is Alice's parent"
- Complex reasoning: "Who are Bob's ancestors?"

## Failure Explanations

When a query fails, the system provides structured explanations instead of cryptic errors:

```text
Query: "Who is Charlie's parent?"

Response:
- Status: undefined entity 'charlie'
- Known entities: john, alice, bob, admin, ...
- Suggestion: define charlie or use a known entity
```

Run the demo:

```bash
python scripts/demonstrate_failures.py
```

## Architecture

See [architecture.md](architecture.md) for full design.

Key layers:
1. **Prolog Engine** — Pure Python interpreter with unification and backtracking
2. **IR Schema** — Structured intermediate representation with validation
3. **Semantic Grounding** — Natural language to IR conversion
4. **IR Compiler** — JSON to Prolog conversion with deduplication
5. **Explanation Layer** — Proof traces and human-readable outputs
6. **Agent Integration** — Skill interfaces for LLM frameworks and MCP

## File Structure

```text
prolog-reasoning-v2/
├── src/
│   ├── engine/                   # Prolog interpreter and propagation engine
│   ├── ir/                       # Intermediate representation
│   ├── compiler/                 # IR → Prolog compiler
│   ├── parser/                   # Semantic grounding (NL → IR)
│   ├── explain/                  # Proof trace generation
│   └── agent_skill.py            # Agent framework integration
├── tests/                        # Unit and integration tests
├── data/                         # Benchmarks and evaluation
├── scripts/                      # Demo and utility scripts
├── docs/                         # Documentation
├── prolog/                       # Prolog knowledge bases
└── requirements.txt              # Python dependencies
```

## Integration with LM Studio

To use this system with a local LLM via MCP (Model Context Protocol):

```bash
# 1. Start the MCP server
python src/mcp_server.py --stdio

# 2. Configure LM Studio
# 3. Chat with your local LLM
```

Capabilities:
- Deterministic queries against structured facts
- Traceable reasoning with explicit proof chains
- Validation feedback for grounding issues
- Session-based fact management

Resources:
- [LM Studio MCP Guide](docs/lm-studio-mcp-guide.md)
- [Course 04: Local LLM + MCP Integration](training/04-lm-studio-mcp.md)

## Constraint Propagation

The repository also includes a deterministic constraint propagation layer for building constraint-management applications.

What it provides:
- Known-state propagation via implication rules (fixed-point closure)
- Degree-of-freedom propagation via domain narrowing
- Contradiction detection when domains become infeasible

Run the example:

```bash
python src/engine/runner.py --propagate --problem-json data/propagation_example.json
```

Core files:
- `src/engine/constraint_propagation.py`
- `src/engine/runner.py`
- `data/propagation_example.json`
- `tests/test_constraint_propagation.py`
- `tests/test_runner_propagation.py`

## Getting Started Resources

If you want guided material first, start with the [training library](training/):
- [01 - LLM Memory and Symbolic Reasoning](training/01-llm-memory-magic.md)
- [02 - Knowledge Bases 101](training/02-knowledge-bases-101.md)
- [03 - Learning from Failures](training/03-learning-from-failures.md)
- [04 - Local LLM + MCP Integration](training/04-lm-studio-mcp.md)

## Use Cases

This approach is suited for domains where accurate fact recall is important.

### Healthcare: Medication Safety

Managing medication records and allergy tracking:

```prolog
patient(john_smith, id_12345).
takes_medication(john_smith, metformin, 500, bid).
takes_medication(john_smith, lisinopril, 10, daily).
allergy(john_smith, penicillin, severe).
lab_result(john_smith, creatinine, 1.8, "2024-01-15").

contraindicated(Patient, Drug) :- allergy(Patient, Drug, severe).
contraindicated(Patient, Drug) :- takes_medication(Patient, Drug2, _, _),
                                  interacts(Drug, Drug2).

interacts(metformin, penicillin).
```

Query: `?- contraindicated(john_smith, penicillin).` → `true`

### Cybersecurity: Access Control

Tracking access permissions and detecting policy violations:

```prolog
employee(bob_johnson, emp_456).
role(bob_johnson, senior_engineer).
access_level(bob_johnson, admin).
clearance(bob_johnson, level_3).

can_access(User, Resource) :- role(User, admin).
can_access(User, Resource) :- granted_permission(User, Resource, active).

suspicious_activity(User) :- access_attempt(User, Resource, denied),
                             access_attempt(User, Resource, denied),
                             time_window(attempts, 300).

revoked_access(User, Resource) :- security_incident(User, Resource, _).
```

Query: `?- suspicious_activity(bob_johnson).` → `true`

### Financial Services: Compliance

Monitoring transaction patterns for regulatory compliance:

```prolog
account_holder(account_789012, john_doe).
transaction(account_789012, xyz_corp, 50000, "2024-01-20").
owns_business(john_doe, abc_industries).

high_risk_transaction(Account, Amount) :- transaction(Account, _, Amount, _),
                                         Amount > 10000.

money_laundering_risk(Account) :- transaction(Account, offshore_entity, _, _),
                                  transaction(Account, offshore_entity, _, _),
                                  time_window(transactions, 30).

sanctions_violation(Account) :- account_holder(Account, Person),
                               sanctioned_entity(Person, _).
```

Query: `?- money_laundering_risk(account_789012).` → `true`

### Legal: Contract Analysis

Tracking contract terms and detecting potential breaches:

```prolog
contract(techcorp_startupxyz_merger, parties(techcorp, startupxyz)).
value(techcorp_startupxyz_merger, 50000000).
condition(techcorp_startupxyz_merger, regulatory_approval, required).
condition(techcorp_startupxyz_merger, ip_transfer, required).
condition(techcorp_startupxyz_merger, employee_retention, required).

breach_of_contract(Contract) :- condition(Contract, Condition, required),
                                not_satisfied(Condition).

regulatory_violation(Contract) :- condition(Contract, regulatory_approval, required),
                                  approval_status(regulatory_approval, denied).

liability_risk(Contract) :- breach_of_contract(Contract).
liability_risk(Contract) :- regulatory_violation(Contract).
```

Query: `?- liability_risk(techcorp_startupxyz_merger).` → `true`

### Supply Chain: Dependency Tracking

Tracking component suppliers and sourcing locations:

```prolog
component(widget_a, part_x).
component(widget_a, part_y).
supplier(part_x, s1_taiwan).
supplier(part_y, s2_vietnam).
assembly_location(widget_a, mexico_plant).

supply_chain_risk(Product) :- component(Product, Component),
                              supplier(Component, Location),
                              geopolitical_risk(Location, high).

production_delay_risk(Product) :- supply_chain_risk(Product).
production_delay_risk(Product) :- assembly_location(Product, Location),
                                  labor_dispute(Location, active).

critical_path_impact(Product, Delay) :- production_delay_risk(Product),
                                        depends_on(critical_customer, Product).
```

Query: `?- critical_path_impact(widget_a, severe).` → `true`

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_engine.py -v

# Run benchmark evaluation
python data/evaluate.py
```

## Project Status

For current implementation status, see [status.md](status.md).

For future priorities and planned work, see [roadmap.md](roadmap.md).

## Experimental: Constraint-Based Graphics Editor

Status: early exploratory prototype, not production-ready.

This explores whether the constraint propagation layer can support a graphics editor with rule-based layout behavior.

- [Constraint Editor MVP Playbook](docs/constraint-editor-mvp-playbook.md)

Local handoff notes for MVP iterations are kept outside published docs.

This is not the main focus of the project.

## Contributing

This is research software. Contributions are welcome:

1. Bug reports via GitHub issues
2. Feature requests via issue discussion
3. Code contributions via pull request with tests
4. Research collaboration by direct contact

## Citation

If you use this work in research:

```bibtex
@software{prolog_reasoning_v2,
  title = {Prolog Reasoning v2: Lossless Symbolic Memory for LLM Agents},
  author = {Your Name},
  year = {2026},
  url = {https://github.com/your-repo/prolog-reasoning-v2}
}
```

## License

MIT License. See [LICENSE](LICENSE).

## Related Work

- Original Prolog Reasoning repository
- Symbolic AI systems for reliable reasoning
- Neuro-symbolic systems that combine neural and symbolic components
- Agent memory systems for long-horizon reasoning
