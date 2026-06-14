# action_intelligence/

Read-model surface for GP-243 action-impact diagnostics. Daemon-owned;
operators read, daemon writes.

## Files

- `state/source_health.json` — current source-lane health snapshot.
- `state/action_intelligence.json` — recommended next-operator actions
  + the structural rationale per action.
- `state/shadow_recommendations.json` — proposed actions held back
  for review before promotion to the live recommendation set.

Consumer: `src/ztare/reports/operations_intelligence.py` (the RD-side
intelligence reporter). The CLI surface is `ztare action-intel`.

## Agentic workbench rows

`ztare action-intel record-agentic-work ...` records RD/Codex/Claude or other
out-of-loop agent labor as `domain=agentic_workbench` action-impact evidence.
Use it when a task could plausibly have been sent through autoresearch. The row
must state the workbench-router decision: invoke autoresearch, prepare the
missing surface, stay out of loop, or not evaluated. If the selected action is
`run_out_of_loop_agent`, include `--why-not-autoresearch`.

These rows feed operations intelligence and reflexive mining. They do not
schedule workers, mutate autoresearch state, or replace source ledgers.

## Update cadence

Refreshed by the action-intelligence daemon at end of every RD tick.
Files are atomic-write (temp + rename), so readers always see a
consistent snapshot.
