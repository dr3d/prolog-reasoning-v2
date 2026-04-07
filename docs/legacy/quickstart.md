# Prolog Reasoning v2 — Developer Quick Start

## Setup

```bash
# Clone repo
git clone <repo>
cd prolog-reasoning

# Install dependencies
pip install -r requirements.txt

# Run tests to verify installation
python -m pytest tests/test_engine.py -v
```

## Project Structure

```
src/
  ├── engine/          # Prolog interpreter (core.py, runner.py)
  ├── ir/              # Intermediate representation schema
  ├── compiler/        # IR → Prolog translator
  ├── parser/          # Semantic grounding (NL → IR)
  ├── explain/         # Proof trace generation
  └── agent_skill.py   # Agent framework integration

tests/                 # Unit and integration tests
  └── test_engine.py   # 21 comprehensive Prolog engine tests

data/                  # Benchmark datasets and evaluation
  ├── benchmark.py     # 13 test cases across 4 domains
  └── evaluate.py      # Evaluation harness

scripts/               # Demo and utility scripts
  ├── demonstrate_agent.py     # Agent integration demo
  ├── demonstrate_semantic.py  # Semantic grounding demo
  └── generate_manifest.py     # KB manifest generator

prolog/                # Prolog knowledge bases
  └── core.pl          # Base rules (family, access, etc.)

docs/                  # Documentation
  ├── architecture.md          # Full system design
  ├── agent-integration.md     # Agent framework integration
  └── semantic-grounding.md    # NL processing guide
```

## Key Components

### 1. Prolog Engine (src/engine/core.py)
Pure Python implementation with:
- Unification algorithm with occurs check
- Backward chaining with backtracking
- Built-in predicates (arithmetic, comparison, negation, cut)
- Depth limit to prevent infinite loops
- Variable renaming and substitution tracking

**Usage:**
```python
from src.engine.core import PrologEngine, Term, Clause

engine = PrologEngine()
# Add facts and rules...
solutions = engine.resolve(query_term)
```

### 2. Semantic Grounding (src/parser/semantic.py)
Natural language to logic conversion:
- LLM-assisted parsing with error correction
- Query intent classification
- Confidence scoring and validation
- Multiple query types supported

**Usage:**
```python
from src.parser.semantic import SemanticPrologSkill

skill = SemanticPrologSkill()
result = skill.query_nl("Who is John's parent?")
print(result["bindings"])  # {"X": "alice"}
```

### 3. Agent Integration (src/agent_skill.py)
Framework-ready interfaces:
- AutoGen/CrewAI compatible
- Structured response formats
- External KB with manifest injection

**Usage:**
```python
from src.agent_skill import PrologSkill

skill = PrologSkill()
result = skill.query("parent(john, X).")
```

## Quick Examples

### 1. Direct Prolog Query
```bash
cd src
python -c "
from agent_skill import PrologSkill
skill = PrologSkill()
result = skill.query('parent(john, X).')
print('Success:', result['success'])
print('Bindings:', result['bindings'])
"
```

### 2. Natural Language Query
```bash
cd src
python -c "
from parser.semantic import SemanticPrologSkill
skill = SemanticPrologSkill()
result = skill.query_nl('Who is John\\'s parent?')
print('Answer:', result['explanation'])
"
```

### 3. Run All Tests
```bash
python -m pytest tests/test_engine.py -v
# Should show: 21 passed
```

### 4. Run Semantic Demo
```bash
python scripts/demonstrate_semantic.py
```

### 5. Run Benchmark Evaluation
```bash
python data/evaluate.py
```

## Development Workflow

### Adding New Features
1. **Engine changes**: Add tests in `tests/test_engine.py`
2. **New predicates**: Update IR schema in `src/ir/schema.py`
3. **Semantic patterns**: Extend mock LLM in `src/parser/semantic.py`
4. **Documentation**: Update relevant docs in `docs/`

### Testing
```bash
# Run specific tests
python -m pytest tests/test_engine.py::TestUnification -v

# Run with coverage
python -m pytest --cov=src tests/

# Run benchmark
python data/evaluate.py
```

### Code Quality
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Lint
flake8 src/ tests/
```

## Common Issues

### Import Errors
```bash
# Make sure you're in the project root
cd /path/to/prolog-reasoning

# Or add src to Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

### Test Failures
- Check that all dependencies are installed
- Verify you're using Python 3.12+
- Run `python -m pytest tests/test_engine.py -v` for details

### Semantic Parsing Issues
- The mock LLM handles specific patterns
- For real LLM integration, set API keys
- Check confidence scores in responses

## Architecture Overview

The system follows a layered architecture:

1. **Natural Language** → Semantic Grounding → **IR**
2. **IR** → Compiler → **Prolog Syntax**
3. **Prolog Syntax** → Engine → **Solutions**
4. **Solutions** → Explanation → **Human-Readable Output**

Each layer is independently testable and can be swapped out.

## Next Steps

- **Real LLM Integration**: Replace mock with OpenAI/Anthropic APIs
- **Extended Benchmarks**: Add 50+ test cases
- **Research Paper**: Draft methods and results sections
- **Agent Plugins**: Create AutoGen/CrewAI integrations

## Getting Help

- **Issues**: GitHub issues for bugs/features
- **Discussions**: GitHub discussions for questions
- **Research**: Email for academic collaboration

Happy coding! 🚀

engine = PrologEngine()
engine.add_clause(Clause(Term("parent", [Term("john"), Term("alice")])))

query = Term("parent", [Term("john"), Term("X", is_variable=True)])
solutions = engine.resolve(query)
```

### 2. Structured IR (src/ir/schema.py)
Type-safe intermediate representation between NL and Prolog.

**Example:**
```python
from ir.schema import AssertionIR

ir = AssertionIR(
    predicate="parent",
    args=["john", "alice"],
    confidence=0.95
)

prolog_fact = ir.to_prolog()  # "parent(john, alice)."
```

### 3. IR Compiler (src/compiler/ir_compiler.py)
Converts IR to Prolog facts/rules with validation.

```python
from compiler.ir_compiler import IRCompiler
from engine.core import PrologEngine

engine = PrologEngine()
compiler = IRCompiler(engine)

ir = AssertionIR(predicate="parent", args=["john", "alice"])
compiler.compile_and_add(ir)  # Adds to engine KB
```

### 4. Explanation Layer (src/explain/explanation.py)
Generates proof traces and human-readable justifications.

```python
from explain.explanation import ExplanationGenerator

gen = ExplanationGenerator()
explanation = gen.generate_explanation(solutions, goal)
# Returns: success, proof_trace, explanation text, etc.
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/test_engine.py::TestUnification -v

# Run with coverage
pytest tests/ --cov=src
```

## Running Benchmarks

```bash
# Generate benchmark dataset
python data/benchmark.py

# Run evaluation
python data/evaluate.py

# View results
cat data/evaluation_report.json
```

## Key Invariants

1. **Losslessness**: Facts never degrade
2. **Determinism**: Same query always returns same result
3. **Explainability**: All answers have proof chains
4. **Schema Safety**: IR enforces predicates
5. **Composability**: Rules can compose

## Next Steps

1. ✅ Core engine implementation
2. ✅ IR schema design
3. ✅ Based compiler
4. ✅ Explanation generation
5. ⚠️ Semantic parser (LLM grounding)
6. ⚠️ Full test suite
7. ⚠️ Extended benchmarks
8. ⚠️ Paper draft

## Performance Notes

- Current engine: ~10ms per query (simple facts)
- Depth limit: 500 (prevents infinite recursion)
- Most bottleneck: LLM semantic parsing (not engine)

## Common Issues

**Query returns no results:**
- Check predicate name in KB
- Verify variable naming (capitalized)
- Use `engine.clauses` to inspect KB

**"Depth limit exceeded":**
- Check for infinite recursion in rules
- Verify base case in recursive predicates

**Variables show as _G123:**
- Unresolved terms - ensure query binds all variables

## Contributing

- Add tests for new features
- Update architecture.md for design changes
- Keep engine pure Python (no external deps)
- Document changes in docstrings
