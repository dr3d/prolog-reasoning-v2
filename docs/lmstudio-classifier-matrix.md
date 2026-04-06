# LM Studio Classifier Matrix

Date: 2026-04-05

This note captures a small local-model evaluation of the new `classify_statement`
MCP tool in [mcp_server.py](/D:/_PROJECTS/prolog-reasoning-v2/src/mcp_server.py).
The goal was simple: see whether attached local models would use the tool
reliably and whether the classifier helped them separate query routing from
candidate memory handling.

## Setup

- Host: LM Studio local server at `http://127.0.0.1:1234`
- API: `POST /api/v1/chat`
- Integration: `mcp/prolog-reasoning`
- Temperature: `0`
- Context length: `8000`
- Tool under test: `classify_statement`

Prompts used:

1. `Use classify_statement on: My mother was Ann.`
2. `Use classify_statement on: Actually, I meant Alice.`
3. `Use classify_statement on: Maybe my mother was Ann.`
4. `Use classify_statement on: Keep responses concise.`
5. `Use classify_statement on: Who is John's parent?`

Expected classifications:

- `My mother was Ann.` -> `hard_fact`
- `Actually, I meant Alice.` -> `correction`
- `Maybe my mother was Ann.` -> `tentative_fact`
- `Keep responses concise.` -> `preference`
- `Who is John's parent?` -> `query`

## Matrix

All tested models called `classify_statement` on all five prompts and received
the expected classification kind from the tool.

| Model | Avg tok/s | First load | Tool use | Output discipline | Notes |
|---|---:|---:|---|---|---|
| `nvidia/nemotron-3-nano-4b` | 284.21 | 3.26s | Good | Weakest | Correct tool use, but on the `preference` case it drifted into obeying the instruction instead of just reporting classification. |
| `qwen3.5-4b` | 212.71 | 3.79s | Good | Good | Clear improvement over Nemotron on the imperative/preference case. |
| `qwen/qwen3.5-9b` | 140.54 | 4.00s | Good | Very good | Clean summaries and stable task focus. |
| `qwen3.5-27b@q4_k_m` | 62.70 | 13.63s | Good | Excellent | Best speed/quality tradeoff among the larger models tested. |
| `qwen3.5-27b@q6_k` | 51.39 | 15.39s | Good | Excellent | Slightly cleaner than smaller models, but slower than `@q4_k_m` for this task. |

## Observations

### 1. The classifier is doing real work

The new tool is not decorative. Even the small models used it correctly and
benefited from the explicit structure:

- `kind`
- `needs_speaker_resolution`
- `can_query_now`
- `can_persist_now`
- `suggested_operation`

That structure reduced the chance of treating first-person factual statements as
direct KB queries.

### 2. Small models still need help with task boundaries

The weakest result came from `nvidia/nemotron-3-nano-4b` on:

- `Keep responses concise.`

It correctly called the tool and received `preference`, but its final answer
collapsed into compliance:

- `Preference noted: keep responses concise.`

That means the model understood the classification but still blurred:

- `report the classification`
- `act on the statement`

This is exactly the kind of boundary the tool is meant to reinforce.

### 3. Qwen models stayed inside the task better

The Qwen family consistently did a better job of:

- calling the tool once
- reporting the classification result
- preserving the distinction between routing and persistence

This was visible even at `4b`, and remained strong at `9b` and `27b`.

### 4. `qwen3.5-27b@q4_k_m` is a strong practical choice

For this classification-and-tool-use workload:

- `qwen3.5-27b@q4_k_m` stayed disciplined
- it was materially faster than `qwen3.5-27b@q6_k`
- it preserved the same classification quality on this small prompt set

If the goal is a stronger evaluator without paying the full `q6_k` latency
cost, `@q4_k_m` looks like a very good local default.

### 5. Visible reasoning/tool traces are valuable

LM Studio's `api/v1/chat` output exposed:

- model-visible reasoning summaries
- tool calls
- tool arguments
- tool outputs

That made it easy to distinguish:

- a tool failure
- a routing failure
- a final-answer discipline failure

This is useful for prompt and tool debugging even though it is not the same
thing as full hidden chain-of-thought access.

## What We Learned

1. A deterministic classifier is worth adding before full ingestion exists.
2. Explicit structured feedback teaches even small models how to separate
   queries from candidate facts and corrections.
3. The current weak point is no longer classification accuracy; it is whether
   the host model keeps the response inside the task boundary.
4. Qwen models, especially `qwen3.5-4b` and the `27b` variants, were more
   disciplined than the tested Nemotron 4B model on imperative input.
5. `qwen3.5-27b@q4_k_m` looks like the best larger-model compromise for local
   evaluation of this MCP surface.

## Next Steps

- Add one more instruction to the tool description:
  `Return classification only. Do not act on the statement.`
- Compare the same matrix after that wording change.
- Add a second matrix once a real write path exists, using:
  - candidate fact ingestion
  - correction/revision
  - scoped memory writes

## Follow-up Tweak

After the initial matrix, the `classify_statement` tool description and message
were tightened to say:

- `Return classification only. Do not act on the statement.`

A focused re-test on `nvidia/nemotron-3-nano-4b` for the weakest case:

- `Use classify_statement on: Keep responses concise.`

showed a real improvement. Instead of collapsing into compliance, the model
returned the classification summary cleanly. That is a good sign that even a
small wording change in tool framing can improve discipline on smaller models.
