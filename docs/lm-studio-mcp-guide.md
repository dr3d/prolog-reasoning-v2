# Using Prolog Reasoning with LM Studio via MCP

**Model Context Protocol (MCP) integration for local LLMs in LM Studio**

This guide walks you through setting up and using the Prolog Reasoning system as an MCP server in LM Studio, enabling your local LLM to perform deterministic logical reasoning with guaranteed accuracy.

---

## What is MCP and Why Use It?

**MCP (Model Context Protocol)** allows AI tools (servers) to expose capabilities as tools to language models.

**Why this matters for Prolog Reasoning:**
- Your local LLM can query a deterministic knowledge base
- Guaranteed correct answers (not hallucinated)
- Confidence scores show reliability level
- Error messages explain what went wrong
- No external API calls needed

**The benefit:** Your LLM gets "perfect memory + logical reasoning" as a tool!

---

## Prerequisites

- LM Studio installed ([download here](https://lmstudio.ai/))
- Python 3.12+ 
- Prolog Reasoning repo cloned
- Virtual environment set up (`pip install -r requirements.txt`)

---

## Step 1: Start the MCP Server

### Option A: Quick Start (Recommended for Testing)

```bash
cd d:\\_PROJECTS\prolog-reasoning

# Test that everything works
python src/mcp_server.py --test

# You should see:
# MCP Server initialized successfully
# Available Tools:
#   - query_logic: ...
#   - query_rows: ...
#   - list_known_facts: ...
#   - explain_error: ...
#   - show_system_info: ...
```

### Option B: Run in Interactive Mode (for debugging)

```bash
python src/mcp_server.py

# You'll get an interactive prompt
# > logic parent(john, X).
# > list
# > info
# > quit
```

### Option C: Run with Stdio (for LM Studio)

```bash
python src/mcp_server.py --stdio
```

This is the transport LM Studio will use. In normal use, LM Studio should launch this process for you from `mcp.json` rather than you keeping it running manually in a separate terminal.

---

## Step 2: Configure LM Studio

### Step 2a: Access LM Studio Settings

1. Open **LM Studio**
2. Click **Settings** (bottom right)
3. Go to **Developer** -> **Model Context Protocol (MCP)**
4. You should see a "servers" configuration section

### Step 2b: Add the Prolog Server

Add this configuration to your `servers` list. Replace `<PYTHON_EXE>` with the Python interpreter from the environment where you installed this repo's dependencies, and replace `<REPO_ROOT>` with your clone path:

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

**Examples for `<PYTHON_EXE>`**:
- Windows global Python: `C:\\Users\\<YourUsername>\\AppData\\Local\\Programs\\Python\\Python312\\python.exe`
- Windows virtualenv Python: `C:\\path\\to\\your\\env\\Scripts\\python.exe`
- macOS/Linux virtualenv Python: `/path/to/your/env/bin/python`

### Step 2c: Test the Connection

1. Restart LM Studio
2. Open a chat with your local model
3. You should see **Prolog Reasoning** in the available tools list
4. The tools should show:
   - query_logic
   - query_rows
   - classify_statement
   - set_pre_think_session
   - pre_think
   - show_pre_think_state
   - list_known_facts
   - assert_fact
   - bulk_assert_facts
   - retract_fact
   - reset_kb
   - empty_kb
   - explain_error
   - show_system_info

Use the tool names above in day-to-day chat. The MCP surface is Prolog-first and expects literal Prolog queries.

Pre-think session toggle note:
- call `set_pre_think_session` with `enabled=true` to request pre-think on subsequent turns
- call it with `enabled=false` to turn it back off
- language directives like "disable pre-think from now on" are also recognized by `pre_think`

### Step 2d: API Token Note (for Scripted MCP Demos)

LM Studio can run in two API-auth modes:

- auth disabled: no token needed
- auth enabled: HTTP calls must include `Authorization: Bearer <token>`

This matters for repo scripts like `scripts/demonstrate_*_agent_mcp.py`, which
call LM Studio's `/api/v1/chat` endpoint while using MCP integrations.

Set a token before running those scripts:

```bash
# PowerShell
$env:LMSTUDIO_API_KEY = "<YOUR_LM_STUDIO_API_TOKEN>"
python scripts/demonstrate_family_tree_agent_mcp.py
```

Or pass it explicitly:

```bash
python scripts/demonstrate_family_tree_agent_mcp.py --api-key "<YOUR_LM_STUDIO_API_TOKEN>"
```

The hospital playbook capture script supports the same auth pattern and includes
an optional validation mode:

```bash
python scripts/capture_hospital_playbook_session.py --validate --out-dir docs/examples
```

For a one-command onboarding smoke check that runs hospital, fantasy, surface-sanity, and indie-launch captures:

```powershell
# Windows / PowerShell
./scripts/onboarding_mcp_smoke.ps1
```

On macOS/Linux, run the same validated checks directly:

```bash
python scripts/capture_hospital_playbook_session.py --validate --out-dir docs/examples
python scripts/capture_fantasy_overlord_session.py --validate --out-dir docs/examples
python scripts/capture_mcp_surface_playbook_session.py --validate --out-dir docs/examples
python scripts/capture_indie_launch_warroom_session.py --validate --out-dir docs/examples
```

If token auth is enabled and no valid token is provided, the script will fail
with `HTTP 401` and a remediation hint. The script checks `LMSTUDIO_API_KEY`
first, then `OPENAI_API_KEY`.

Quick 401 recovery (copy/paste):

```powershell
# Load key from shell or fallback to .env.local, then ping :1234
$key = $env:LMSTUDIO_API_KEY
if (-not $key -and (Test-Path ".env.local")) {
  foreach ($line in Get-Content ".env.local") {
    if ($line -match "^LMSTUDIO_API_KEY=(.+)$") { $key = $Matches[1].Trim(); break }
  }
}
$headers = @{ "Content-Type" = "application/json"; "Authorization" = "Bearer $key" }
$body = @{ model = "qwen/qwen3.5-9b"; input = "Reply with exactly: LM_OK"; temperature = 0; context_length = 256 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:1234/api/v1/chat" -Headers $headers -Body $body
```

If this returns a model response, auth and local API connectivity are good.

---

## Optional: Operator UI (Pre-Think Console)

If you want an operator-facing UI instead of chat-only workflows, run:

```bash
python scripts/prethink_console.py
```

Then open:

`http://127.0.0.1:8765`

What this console gives you:
- session toggles (`enabled`, `handoff_mode`, `kb_ingest_mode`)
- pre-think only runs for raw utterance inspection
- full routed turns (`utterance -> pre_think -> main model`)
- explicit routing timeline per turn (input/pre-think/directive gate/main-model)
- raw vs processed utterance diff view
- KB utilities (`query_rows`, `reset_kb`, `empty_kb`)
- KPI strip with run-level proxies:
  - write precision proxy
  - false-write proxy rate
  - cloud escalation rate
  - pre-think/main/end-to-end latency
- one-click snapshot export (JSON + Markdown) to `docs/research/conversations/prethink-console/`

Defaults can be overridden at launch:

```bash
python scripts/prethink_console.py --model qwen3.5-4b --integration mcp/prolog-reasoning --context-length 4000
```

The console writes JSONL turn logs to:

`.tmp_prethink_console_runs.jsonl`

Use `--run-log-path` if you want a different file.

Snapshot root can also be overridden:

```bash
python scripts/prethink_console.py --snapshot-root docs/research/conversations/prethink-console
```

---

## Step 3: Use with Your LLM

For chat-first copy/paste scenario scripts (including a Critical Path Method
(CPM)-like hospital
dependency risk playbook), see:

- `docs/mcp-chat-playbooks.md`

### Example 1: Simple Question

**You:** Can you find out who John's parent is? Use the Prolog tool to check.

**LLM thinking:** 
```
The user wants me to query a knowledge base. I have access to 
the "query_logic" tool. Let me use it to find John's parent.
```

**LLM action:**
```
Tool: query_logic
Input: {"query": "parent(john, X)."}
```

**Result:**
```json
{
  "status": "success",
  "answer": "SUCCESS: Query 'parent(john, X)' succeeded with 1 solution(s).\n  Bindings: X: alice",
  "confidence": 100.0,
  "parsing_confidence": 95.0,
  "domain": "family"
}
```

**LLM response:** "According to the knowledge base, John's parent is Alice with 100% confidence."

---

### Example 2: Handling Errors Properly

**You:** Check if Charlie is an ancestor of Bob using the knowledge base.

**LLM action:**
```
Tool: query_logic
Input: {"query": "ancestor(charlie, bob)."}
```

**Result:**
```json
{
  "status": "no_results",
  "result_type": "no_result",
  "predicate": "ancestor",
  "prolog_query": "ancestor(charlie, bob)."
}
```

**LLM response:** "No matching ancestor fact was found for charlie and bob. We can inspect known entities with `list_known_facts` or try a simpler query."

---

### Example 3: Exploring What's Known

**You:** Show me what the knowledge base contains.

**LLM action:**
```
Tool: list_known_facts
Input: {}
```

**Result:**
```json
{
  "status": "success",
  "known_entities": [
    "admin", "alice", "bob", "john",
    "read", "write"
  ],
  "supported_predicates": [
    "parent", "sibling", "ancestor", "child",
    "allergic_to", "takes_medication",
    "user", "role", "permission", "access_level",
    "can_access", "granted_permission"
  ]
}
```

**LLM response:** "The knowledge base has information about these people: John, Alice, and Bob. It can answer questions about family relationships and access control."

---

## Best Practices for LLMs Using Prolog Tools

### DO: Use for Deterministic Queries

```
Good uses:
- "Check if John is Alice's ancestor in the knowledge base"
- "What does the system know about Bob?"
- "Are there any access control issues with admin permissions?"
- "Show me all family relationships in the KB"
```

### DON'T: Use for Creative Tasks

```
Bad uses:
- "Invent a new family relationship not in the KB"
- "What MIGHT happen if we added Charlie?"
- "Generate creative facts about fictional characters"

Instead: "The knowledge base only contains verified facts. 
I can't create new information, only reason about what's there."
```

### Handle Errors Gracefully

When the tool returns a validation error:
1. Read the `explanation` field (it's human friendly!)
2. Offer alternatives from `known_entities`
3. Suggest simplifying the query
4. Don't retry with the exact same question

---

## Understanding Tool Responses

### Response Format

Every tool response has this structure:

```json
{
  "status": "success|validation_error|no_results|error",
  "confidence": 0.0-100.0,  // Certainty level
  "explanation": "...",      // What happened
  "suggestion": "..."        // What to try next
}
```

### Status Types

| Status | Meaning | Action |
|--------|---------|--------|
| `success` | Query found an answer | Use the result! |
| `validation_error` | Query has issues (bad entity, etc.) | Check `errors` field for suggestions |
| `no_results` | Query is valid but no answer exists | Try simpler query or add facts |
| `error` | Server error | Check logs, restart server |

### Confidence Scores

- **100%** = Fact explicitly in knowledge base, verified
- **80-99%** = Derived from rules, high confidence
- **50-79%** = Some uncertainty in parsing
- **<50%** = Low confidence, verify before using

---

## Troubleshooting

### Problem: "Tool not found" error

**Cause:** MCP server didn't start properly

**Fix:**
```bash
# Test the server manually
python src/mcp_server.py --test

# Check the output shows the canonical MCP tool set
# If not, you'll see the error
```

### Problem: "Permission denied" when running python

**Cause:** Path issue or permissions

**Fix:**
```bash
# Use the full path to the Python interpreter for the environment where you
# installed this repo's dependencies
<PYTHON_EXE> src/mcp_server.py --stdio

# Or use the Python executable from the environment where you installed
# this repo's dependencies.
```

### Problem: LLM calls tool but gets "undefined entity" for everything

**Cause:** Knowledge base is empty or not loading

**Fix:**
```bash
# Check the KB file exists
ls prolog/core.pl

# Check it has content
cat prolog/core.pl | head -20

# If empty, you need to add facts first
```

### Problem: Very slow responses

**Cause:** Large knowledge base or complex queries

**Fix:**
```bash
# Simplify queries
# Instead of: "Find all relationships between anyone"
# Use: "Who is John's parent?"

# Or add constraints to narrow the search
```

---

## Advanced: Baseline Seed KB (`core.pl`)

`prolog/core.pl` is the baseline seed knowledge base:

- loaded when the MCP server starts
- reloaded when you call `reset_kb`
- source-of-truth starting facts/rules for new sessions

Important:

- runtime tool calls (`assert_fact`, `bulk_assert_facts`, `retract_fact`) mutate in-memory state
- those runtime changes are not written back to `core.pl`
- `core.pl` can be intentionally minimal or even effectively empty; that is valid, but answers will be limited until facts are loaded

### Step 1: Edit Baseline Facts/Rules

Edit `prolog/core.pl` if you want a different reset baseline for your domain:

```prolog
% Your custom domain facts
patient(john).
patient(alice).
allergic_to(john, penicillin, severe).
allergic_to(alice, peanuts, moderate).

% Rules for your domain
at_risk(Patient, Drug) :- allergic_to(Patient, Drug, severe).
safe_to_prescribe(Patient, Drug) :- patient(Patient), \+ at_risk(Patient, Drug).
```

### Step 2: Restart the MCP Server

```bash
# Stop current server (Ctrl+C)
# Then restart:
python src/mcp_server.py --stdio
```

### Step 3: Use with Your LLM

Your LLM now starts from this updated baseline after server start/reset.

---

## Learning More

### Courses on Using This System

1. **[01 - LLM Memory Magic](../training/01-llm-memory-magic.md)** (30 min)
   - Why AI needs external knowledge

2. **[02 - Knowledge Bases 101](../training/02-knowledge-bases-101.md)** (25 min)
   - How to structure facts properly

3. **[03 - Learning from Failures](../training/03-learning-from-failures.md)** (20 min)
   - Understanding error messages

### Technical Documentation

- **[architecture.md](../architecture.md)** - System design
- **[semantic-grounding.md](legacy/semantic-grounding.md)** - NL processing reference notes
- **[failure-explanations.md](failure-explanations.md)** - Error handling

---

## Example Workflow: Medical Assistant

Here's how you might use this with a medical AI:

```
User: "Can we give John the new antibiotic?"

LLM: "Let me check John's allergies and current medications."

Tool: query_rows({"query": "allergic_to(john, Allergen)."})
Result: penicillin (severe), ibuprofen (moderate)

Tool: query_rows({"query": "takes_medication(john, Medication)."})
Result: metformin, lisinopril

LLM: The system confirms John is allergic to penicillin 
(severe) and takes metformin + lisinopril. The new antibiotic 
appears safe based on known allergies. However, verify the drug 
interactions with current medications."
```

---

## Creating a LLM-Friendly Course

Would you like me to create a fourth course specifically for:
- How to set up MCP in LM Studio
- Best practices for LLMs using this tool
- Real-world examples (medical, security, business logic)
- Debugging when things go wrong

This would be **Course 04** in the training library!

---

## Support & Feedback

- GitHub Issues: [prolog-reasoning](https://github.com/dr3d/prolog-reasoning)
- Found a bug? Please report it!
- Want to contribute? PRs welcome!

Happy reasoning!


