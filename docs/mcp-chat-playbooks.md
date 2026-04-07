# MCP Chat Playbooks (Copy/Paste, No Python Required)

Status: Draft  
Date: 2026-04-06

These playbooks are for direct chat use with MCP enabled in LM Studio.

Goal: turn on `mcp/prolog-reasoning`, paste prompts, and watch the model call
deterministic tools.

Preferred tool names in this guide are the clean aliases (`query_rows`, `assert_fact`, `reset_kb`, etc.). Legacy `_raw` names still work for backward compatibility.

## Before You Start

1. Enable `mcp/prolog-reasoning` in LM Studio.
2. Start a fresh chat.
3. Paste this first:

```text
Use show_system_info and list_known_facts first.
Confirm that query_logic, query_rows, assert_fact, bulk_assert_facts, retract_fact, and reset_kb are available.
Then wait for my next instruction.
```

If LM Studio API auth is enabled, set `LMSTUDIO_API_KEY` before running scripted
API demos. In normal interactive chat use, LM Studio handles MCP tool transport.

### Fast Success Check (Recommended)

Before manual chat copy/paste, you can run a scripted capture with validation:

```powershell
# Windows / PowerShell
./scripts/onboarding_mcp_smoke.ps1
```

This runs four onboarding gates (hospital + fantasy + surface sanity + indie launch war room) and returns one pass/fail summary.

On macOS/Linux, run the four validated gates directly:

```bash
python scripts/capture_hospital_playbook_session.py --validate --out-dir docs/examples
python scripts/capture_fantasy_overlord_session.py --validate --out-dir docs/examples
python scripts/capture_mcp_surface_playbook_session.py --validate --out-dir docs/examples
python scripts/capture_indie_launch_warroom_session.py --validate --out-dir docs/examples
```

Or run the hospital gate directly:

```bash
# PowerShell (only needed if LM Studio API auth is enabled)
$env:LMSTUDIO_API_KEY = "<YOUR_LM_STUDIO_API_TOKEN>"

# Runs the full hospital playbook and validates ingest/count invariants
python scripts/capture_hospital_playbook_session.py --validate --out-dir docs/examples
```

Expected success signal:

- `Validation passed.`
- `ONBOARDING MCP SMOKE: PASS` (if using the combined script)

If you get `HTTP 401`, your API token is missing or invalid for LM Studio's HTTP API.

## How "Entries" Work In Chat

For these playbooks, entries are facts asserted at runtime:

- `assert_fact` adds a fact to the current in-memory KB
- `retract_fact` removes a fact
- `reset_kb` resets to baseline

This is perfect for what-if sessions: you can simulate disruptions and recoveries
without editing code.

## Playbook A: Hospital Build Dependency Risk (CPM: Critical Path Method, PERT-like)

This is a rich project-control scenario for architecture/hospital delivery.
Here, CPM means Critical Path Method. The flow is CPM/PERT-like in spirit:
deterministic dependency propagation and milestone risk tracing.

### Step A1: Reset Runtime

Paste:

```text
Call reset_kb, confirm reset succeeded, then wait.
```

### Step A2: Ingest Baseline Givens

Paste:

```text
Use bulk_assert_facts with the full fact list below.
Then run these verification queries with query_rows and report row counts:
- task(Task).
- depends_on(Task, Prereq).
- task_supplier(Task, Supplier).
- supplier_status(Supplier, Status).
- completed(Task).
- milestone(M).
If any count is lower than expected, stop and say ingestion is incomplete.
Expected counts are:
- task: 16
- depends_on: 20
- task_supplier: 3
- supplier_status: 3
- completed: 3
- milestone: 3
- asserted_count from bulk_assert_facts: 55

task(site_prep).
task(foundation).
task(structural_frame).
task(mep_rough_in).
task(fireproofing).
task(enclosure_glazing).
task(roofing).
task(interior_buildout).
task(hvac_commissioning).
task(medical_gas_cert).
task(or_fitout).
task(imaging_suite_install).
task(it_network_core).
task(regulatory_inspection).
task(occupancy_permit).
task(go_live).

depends_on(foundation, site_prep).
depends_on(structural_frame, foundation).
depends_on(mep_rough_in, structural_frame).
depends_on(fireproofing, structural_frame).
depends_on(enclosure_glazing, structural_frame).
depends_on(roofing, structural_frame).
depends_on(interior_buildout, mep_rough_in).
depends_on(interior_buildout, fireproofing).
depends_on(hvac_commissioning, interior_buildout).
depends_on(medical_gas_cert, interior_buildout).
depends_on(or_fitout, medical_gas_cert).
depends_on(imaging_suite_install, interior_buildout).
depends_on(it_network_core, interior_buildout).
depends_on(regulatory_inspection, hvac_commissioning).
depends_on(regulatory_inspection, medical_gas_cert).
depends_on(regulatory_inspection, it_network_core).
depends_on(occupancy_permit, regulatory_inspection).
depends_on(go_live, occupancy_permit).
depends_on(go_live, or_fitout).
depends_on(go_live, imaging_suite_install).

duration_days(site_prep, 12).
duration_days(foundation, 21).
duration_days(structural_frame, 35).
duration_days(interior_buildout, 40).
duration_days(regulatory_inspection, 14).
duration_days(occupancy_permit, 7).
duration_days(go_live, 2).

task_supplier(enclosure_glazing, glass_vendor).
task_supplier(medical_gas_cert, medgas_vendor).
task_supplier(imaging_suite_install, imaging_vendor).

supplier_status(glass_vendor, on_time).
supplier_status(medgas_vendor, on_time).
supplier_status(imaging_vendor, on_time).

completed(site_prep).
completed(foundation).
completed(structural_frame).

milestone(regulatory_inspection).
milestone(occupancy_permit).
milestone(go_live).
```

### Step A2b: If Baseline Looks Empty

Paste this exact recovery prompt:

```text
Do diagnostics in order:
1) list_known_facts
2) show_system_info
3) query_rows task(Task).

If task(Task) returns 0 rows, call reset_kb and re-run Step A2 ingestion using bulk_assert_facts.
Then verify counts again before continuing.
```

### Step A3: Baseline Control-Room Questions

Paste:

```text
Run these raw queries in order and return markdown tables:
1) query_rows safe_to_start(Task).
2) query_rows waiting_on(Task, Prereq).
3) query_rows task_status(Task, Status).
4) query_rows delayed_milestone(Milestone, Supplier).

Then give a 5-bullet control-room summary:
- what can start now
- what is blocked
- what is waiting
- milestone risk status
- highest-leverage next completion
```

### Step A4: Supplier Shock (Glass Delay)

Paste:

```text
Apply this change set:
1) retract_fact supplier_status(glass_vendor, on_time).
2) assert_fact supplier_status(glass_vendor, delayed).

Then run:
- query_rows blocked_task(Task, Supplier).
- query_rows delayed_milestone(Milestone, Supplier).
- query_rows task_status(Task, Status).

Return:
1) impacted tasks table
2) impacted milestones table
3) one short narrative: "what changed and why it propagated"
```

### Step A5: Second Shock (Medical Gas Vendor Delay)

Paste:

```text
Apply:
1) retract_fact supplier_status(medgas_vendor, on_time).
2) assert_fact supplier_status(medgas_vendor, delayed).

Then run:
- query_rows blocked_task(Task, Supplier).
- query_rows delayed_milestone(Milestone, Supplier).

Return the top 3 interventions to protect go_live, based on deterministic dependencies.
```

### Step A6: Recovery Simulation

Paste:

```text
Apply recovery:
1) retract_fact supplier_status(glass_vendor, delayed).
2) assert_fact supplier_status(glass_vendor, on_time).
3) assert_fact completed(enclosure_glazing).
4) assert_fact completed(mep_rough_in).
5) assert_fact completed(fireproofing).

Then run:
- query_rows safe_to_start(Task).
- query_rows waiting_on(Task, Prereq).
- query_rows delayed_milestone(Milestone, Supplier).

Return an updated execution plan in three sections:
- Ready now
- Still waiting
- Remaining milestone risks
```

## Why This Works

You get a true split of responsibilities:

- chat model handles orchestration and reporting
- symbolic engine enforces dependency truth and propagation

The result is not just plausible planning language. It is reproducible logical
state with explicit update operations.

## Captured Example Session

A full captured run of this playbook is available:

- JSON transcript: `docs/examples/hospital-cpm-playbook-session.json`
- Markdown transcript: `docs/examples/hospital-cpm-playbook-session.md`
- Styled chat transcript (canonical): [examples/hospital-cpm-playbook-session.html](https://dr3d.github.io/prolog-reasoning/examples/hospital-cpm-playbook-session.html)
- Styled chat transcript (GitHub Pages): [dr3d.github.io/prolog-reasoning/examples/hospital-cpm-playbook-session.html](https://dr3d.github.io/prolog-reasoning/examples/hospital-cpm-playbook-session.html)

## Reusable Chat Transcript Template

Use this script for future demos to keep the same chat-bubble format:

- `scripts/capture_hospital_playbook_session.py`

It now supports:

- full capture from LM Studio API + MCP integration
- render-only mode from an existing transcript JSON
- optional transcript validation (`--validate`) for step structure + ingest counts
- user-bubble copy buttons (`[copy]` -> `[copied]`)

Render existing transcript artifacts without re-running the API session:

```bash
python scripts/capture_hospital_playbook_session.py --input-json docs/examples/hospital-cpm-playbook-session.json --out-dir docs/examples
```

## Playbook B: Fantasy Overlord Simulation

For a multi-character simulation with pause/resume edits, locality/inventory state,
and a visible "Prolog Console" side panel in the rendered HTML transcript, use:

- Walkthrough: [fantasy-overlord-mcp-walkthrough.md](fantasy-overlord-mcp-walkthrough.md)
- Captured transcript (HTML): [examples/fantasy-overlord-session.html](https://dr3d.github.io/prolog-reasoning/examples/fantasy-overlord-session.html)
- Captured transcript (GitHub Pages): [dr3d.github.io/prolog-reasoning/examples/fantasy-overlord-session.html](https://dr3d.github.io/prolog-reasoning/examples/fantasy-overlord-session.html)

Optional scripted gate:

```bash
python scripts/capture_fantasy_overlord_session.py --validate --out-dir docs/examples
```

## Playbook C: MCP Surface Sanity (Interactive)

Use this when onboarding someone new and you want a fast "most tools in one chat"
confidence pass without a long narrative scenario.

### Step C1: Preflight

Paste:

```text
Use show_system_info and list_known_facts first.
Then summarize the active KB profile in one paragraph and wait.
```

### Step C2: Clean Start

Paste:

```text
Use ONLY reset_kb. Confirm success in one sentence.
```

### Step C3: Seed Minimal Facts

Paste:

```text
Use bulk_assert_facts with:
task(alpha).
task(beta).
depends_on(beta, alpha).
supplier_status(alpha_vendor, on_time).

Then use assert_fact with:
completed(alpha).

Return asserted_count and a one-line sanity summary.
```

### Step C4: Table Query

Paste:

```text
Use ONLY query_rows with:
depends_on(Task, Prereq).

Return rows and count.
```

### Step C5: Boolean Logic Query

Paste:

```text
Use ONLY query_logic with:
depends_on(beta, alpha).

Return short answer and detailed answer.
```

### Step C6: Natural-Language Query

Paste:

```text
Use ONLY query_prolog on:
What task depends on alpha?
```

### Step C7: Statement Classification

Paste:

```text
Use ONLY classify_statement on:
Maybe my mother was Ann.

Return classification fields only.
```

### Step C8: Error Explainability

Paste:

```text
Use ONLY explain_error with:
Entity 'charlie' not in KB

Return explanation and suggested next actions.
```

### Step C9: Cleanup

Paste:

```text
Use ONLY these tools in order:
1) retract_fact completed(alpha).
2) reset_kb

Confirm cleanup complete.
```

Optional scripted gate for this same surface pass:

```bash
python scripts/capture_mcp_surface_playbook_session.py --validate --out-dir docs/examples
```

## Playbook D: Indie Game Launch War Room (Conversational)

Use this when you want a realistic, practical demo for newcomers that still feels like normal chat.

### Step D1: Preflight

Paste:

```text
Quick pulse check before we dive in.
Use show_system_info and list_known_facts first.
Then summarize in one paragraph what this MCP setup can and cannot do today.
```

### Step D2: Reset Runtime

Paste:

```text
Use ONLY reset_kb. Confirm success in one sentence.
```

### Step D3: Ingest War-Room Baseline

Paste:

```text
Use bulk_assert_facts with this full list, then verify counts with query_rows:
- task(Task).
- depends_on(Task, Prereq).
- task_supplier(Task, Supplier).
- supplier_status(Supplier, Status).
- completed(Task).
- milestone(M).

Expected:
- task: 15
- depends_on: 24
- task_supplier: 4
- supplier_status: 4
- completed: 4
- milestone: 3
- asserted_count: 62

task(vertical_slice_lock).
task(crash_triage_sweep).
task(final_build_candidate).
task(console_submission).
task(platform_release_slot).
task(launch_trailer_cut).
task(press_kit_final).
task(store_page_lock).
task(localization_pack).
task(streamer_preview_keys).
task(day_one_patch).
task(matchmaking_scale_test).
task(community_faq_publish).
task(embargo_briefing).
task(global_launch).
depends_on(crash_triage_sweep, vertical_slice_lock).
depends_on(final_build_candidate, vertical_slice_lock).
depends_on(final_build_candidate, crash_triage_sweep).
depends_on(console_submission, final_build_candidate).
depends_on(platform_release_slot, console_submission).
depends_on(launch_trailer_cut, vertical_slice_lock).
depends_on(press_kit_final, launch_trailer_cut).
depends_on(store_page_lock, launch_trailer_cut).
depends_on(store_page_lock, press_kit_final).
depends_on(localization_pack, final_build_candidate).
depends_on(streamer_preview_keys, platform_release_slot).
depends_on(streamer_preview_keys, store_page_lock).
depends_on(day_one_patch, final_build_candidate).
depends_on(matchmaking_scale_test, final_build_candidate).
depends_on(community_faq_publish, press_kit_final).
depends_on(community_faq_publish, day_one_patch).
depends_on(embargo_briefing, press_kit_final).
depends_on(embargo_briefing, streamer_preview_keys).
depends_on(global_launch, console_submission).
depends_on(global_launch, day_one_patch).
depends_on(global_launch, matchmaking_scale_test).
depends_on(global_launch, store_page_lock).
depends_on(global_launch, localization_pack).
depends_on(global_launch, embargo_briefing).
duration_days(crash_triage_sweep, 3).
duration_days(final_build_candidate, 2).
duration_days(console_submission, 4).
duration_days(platform_release_slot, 2).
duration_days(localization_pack, 5).
duration_days(day_one_patch, 4).
duration_days(matchmaking_scale_test, 3).
duration_days(global_launch, 1).
task_supplier(console_submission, console_cert_vendor).
task_supplier(platform_release_slot, platform_ops_vendor).
task_supplier(localization_pack, localization_vendor).
task_supplier(matchmaking_scale_test, cloud_vendor).
supplier_status(console_cert_vendor, on_time).
supplier_status(platform_ops_vendor, on_time).
supplier_status(localization_vendor, on_time).
supplier_status(cloud_vendor, on_time).
completed(vertical_slice_lock).
completed(crash_triage_sweep).
completed(launch_trailer_cut).
completed(press_kit_final).
milestone(platform_release_slot).
milestone(embargo_briefing).
milestone(global_launch).
```

### Step D4: Standup Snapshot

Paste:

```text
Use ONLY query_rows for:
- safe_to_start(Task).
- waiting_on(Task, Prereq).
- task_status(Task, Status).
- delayed_milestone(Milestone, Supplier).

Then use query_logic for:
depends_on(global_launch, console_submission).

Return: ready now, blockers, waiting chain, milestone risk.
```

### Step D5: Incident and Clarification

Paste:

```text
Apply this cloud vendor incident:
1) retract_fact supplier_status(cloud_vendor, on_time).
2) assert_fact supplier_status(cloud_vendor, delayed).
3) query_rows blocked_task(Task, Supplier).
4) query_rows delayed_milestone(Milestone, Supplier).
5) query_rows task_status(Task, Status).
```

Then paste:

```text
Incoming uncertain producer note:
"I think launch date might be June 3, but it is not locked yet"
Use classify_statement and return classification fields.
Then use explain_error on:
Entity 'mystery_vendor' not in KB
Do not write any facts in this step.
```

### Step D6: Recovery

Paste:

```text
Use only these tools in order:
1) retract_fact supplier_status(cloud_vendor, delayed).
2) assert_fact supplier_status(cloud_vendor, on_time).
3) assert_fact completed(final_build_candidate).
4) assert_fact completed(console_submission).
5) assert_fact completed(platform_release_slot).
6) query_rows safe_to_start(Task).
7) query_rows waiting_on(Task, Prereq).
8) query_rows delayed_milestone(Milestone, Supplier).
9) query_rows task_status(Task, Status).

Close with: ready now, still waiting, remaining launch risk.
```

Optional scripted gate:

```bash
python scripts/capture_indie_launch_warroom_session.py --validate --out-dir docs/examples
```

Captured artifacts:

- `docs/examples/indie-launch-warroom-session.json`
- `docs/examples/indie-launch-warroom-session.md`
- [indie-launch-warroom-session.html](https://dr3d.github.io/prolog-reasoning/examples/indie-launch-warroom-session.html)
- [indie-launch-warroom-session.html on GitHub Pages](https://dr3d.github.io/prolog-reasoning/examples/indie-launch-warroom-session.html)

