# Walkthrough Ladder (Canonical)

Status: Canonical  
Date: 2026-04-06

This is the single walkthrough index for practical demos.

## Shared Setup

For all MCP-based levels:

1. LM Studio running (`http://127.0.0.1:1234`)
2. `mcp/prolog-reasoning` integration enabled
3. If API auth is enabled, set `LMSTUDIO_API_KEY` or pass `--api-key`

For tool-only levels, LM Studio is not required.

## Level Ladder

| Level | Focus | Script | LLM in loop |
|---|---|---|---|
| 1 | Family relationship inference (pure deterministic tool) | `python scripts/demonstrate_family_tree_tool.py` | No |
| 2 | Family inference via MCP tool calls | `python scripts/demonstrate_family_tree_agent_mcp.py` | Yes |
| 3 | Rule-derived table output (pure deterministic tool) | `python scripts/demonstrate_rule_table_tool.py` | No |
| 4 | Rule-derived table via MCP tool orchestration | `python scripts/demonstrate_rule_table_agent_mcp.py` | Yes |
| 5 | Drug triage (deterministic constraint reasoning) | `python scripts/demonstrate_drug_triage_tool.py` | No |
| 6 | Drug triage via MCP tool orchestration | `python scripts/demonstrate_drug_triage_agent_mcp.py` | Yes |
| 7 | Fantasy simulation (pause/edit/resume state + multi-hop chains) | `python scripts/capture_fantasy_overlord_session.py --model qwen/qwen3.5-9b --validate --out-dir docs/examples` | Yes |

## Suggested Run Order

1. Levels 1 and 2 (smallest cognitive ramp)
2. Levels 3 and 4 (table/report style utility)
3. Levels 5 and 6 (higher-stakes logic domain)
4. Level 7 (stateful simulation/control-room style)

## Companion Pages

- [family-tree-walkthrough.md](family-tree-walkthrough.md)
- [family-tree-agent-mcp-walkthrough.md](family-tree-agent-mcp-walkthrough.md)
- [rule-table-walkthrough.md](rule-table-walkthrough.md)
- [rule-table-agent-mcp-walkthrough.md](rule-table-agent-mcp-walkthrough.md)
- [drug-triage-walkthrough.md](drug-triage-walkthrough.md)
- [drug-triage-agent-mcp-walkthrough.md](drug-triage-agent-mcp-walkthrough.md)
- [fantasy-overlord-mcp-walkthrough.md](fantasy-overlord-mcp-walkthrough.md)

## Captured Sessions

- [examples/hospital-cpm-playbook-session.html](https://dr3d.github.io/prolog-reasoning-v2/examples/hospital-cpm-playbook-session.html)
- [examples/fantasy-overlord-session.html](https://dr3d.github.io/prolog-reasoning-v2/examples/fantasy-overlord-session.html)
- [Live pages root](https://dr3d.github.io/prolog-reasoning-v2/examples/)
