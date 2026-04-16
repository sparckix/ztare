# supervisor

Internal operator surfaces for ZTARE.

## GP-070 Goal Orchestrator Dashboard

`inbox_streamlit.py` is the principal dashboard for the ZTARE goal lifecycle.
Three views accessible from the sidebar:

### Goals

Live overview of all tracked goals. Each goal shows:
- Name, slug, type, current stage, status
- Stage map with `[x]` done / `[>]` current / `[ ]` future / `[GATE]` gate-pending
- Transition log (timestamped, with drift detection)
- Actions: Advance to next stage, Resume to clear a gate

### Create Goal

Natural language goal creation. Describe what you want to accomplish and the
system maps it to the right goal type (`science_sandbox`, `synthetic_test`, or
any YAML config in `research_areas/private/goal_types/`). Shows the matched
type's stage map before you commit.

### Inbox

Gate escalation queue. When a goal advances into a gate stage
(`PENDING_LEAK_AUDIT`, `PENDING_SEAL`, `PENDING_NEXT_QUESTION`), it writes a
JSON file to `ztare_workspace/gates/pending/` and appears here. The operator
reviews, writes a note, and clicks Approve / Reject / Defer.

After approving a gate in the Inbox, switch back to the Goals view and click
Resume on the goal to clear the gate and continue advancing.

## Workflow

1. Create a goal from **Create Goal** (or CLI: `python -m src.ztare.orchestration.cli create`)
2. Advance through stages from **Goals** view
3. When a gate fires, review it in **Inbox**, approve, then Resume from **Goals**
4. Repeat until terminal stage (CLOSED / CLOSED_NULL)

## Running

    streamlit run src/ztare/supervisor/inbox_streamlit.py

The dashboard requires the repo root on `sys.path` (handled automatically).

## CLI alternative

All dashboard actions are available via CLI:

    python -m src.ztare.orchestration.cli status                    # list all goals
    python -m src.ztare.orchestration.cli status <slug>             # goal detail
    python -m src.ztare.orchestration.cli create <name> --type <t>  # create goal
    python -m src.ztare.orchestration.cli advance <slug> --to <s>   # advance stage
    python -m src.ztare.orchestration.cli resume <slug>             # clear gate
    python -m src.ztare.orchestration.cli validate <config.yaml>    # validate config

## Architecture

- `inbox_state.py` — pure logic for gate resolution (no Streamlit dependency)
- `inbox_streamlit.py` — Streamlit wrapper, forensic visual register (D4 brief §7)
- GP-070 orchestration core lives in `src/ztare/orchestration/`
- Goal type configs live in `research_areas/private/goal_types/*.yaml`
- Goal state lives in `research_areas/private/goals/<slug>/`

## Fixture regression

    python -m src.ztare.supervisor.inbox_state_fixture_regression
    python -m src.ztare.orchestration.modules.test_module

## Known limitations

- Streamlit's widget system fights the forensic register (monospace, stroke-only
  buttons). CSS overrides get 70% there. A Flask + static HTML rewrite would
  match D4 brief §7 fully.
- Gate resolution in Inbox does not auto-resume the goal — operator must switch
  to Goals view and click Resume. Slice B will wire agent-driven gate resolution
  so the agent can run checklists and resume without operator context-switching.
