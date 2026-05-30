# external_prover_responses/

Append-only record of dispatches to external proof tools (Codex, Claude,
Lean-side hammers). One `.md` file per dispatch, named by `dispatch_id`.

## File pattern

`<dispatch_id>.md` — the prompt that went out, the tool that received
it, the response that came back, the dispatch timestamp, and the
disposition the operator/daemon recorded.

Writer: `scripts/public/control/dispatch_external_prover.py`. No
in-place edits — every new dispatch is a new file. Stale files are
left for postmortem.

## What this is NOT

Not a proof-value ledger. Nothing in this directory earns governance
credit on its own; closure attribution happens through the Governance
Gate, not through dispatch responses.
