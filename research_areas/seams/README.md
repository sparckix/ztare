# Seams — Findings Track

This folder is the **findings ledger**. It is a distinct track from V4 kernel hardening, and the distinction is decisive.

## Two tracks, one repo

ZTARE work splits into two tracks with different origins, tempos, and closure rules:

| Aspect | Kernel track | Findings track (this folder) |
|---|---|---|
| Origin | Planned gap in the core | Runtime-discovered gap |
| Primary activity | Implement | Observe, debate, then maybe implement |
| Tempo | Sprint-driven | Run-driven |
| Evidence to open | A design gap | A single runtime observation |
| Evidence to implement | Design gap is closed | Pattern observed ≥ 2× OR a verifier experiment that would produce n=2 |
| Closure | Implemented + verified | Implemented, subsumed, promoted, or dormant |
| Relationship to core | Modifies core | Strictly downstream of core |
| Artifact home | `debates/kernel/`, `specs/active/`, supervisor programs | `research_areas/seams/*.md` |

Kernel-track items (wrappers, write-scope guard, backlog, manifest, usage ledger, bridge freeze, stage2 derivation seam) are construction projects with external closure conditions. Findings-track items (GP-023, GP-028, GP-029, GP-030, etc.) are the trace of a moment where the loop did something the operator did not expect.

**The findings track is a ledger, not a construction backlog.**

## Five invariants

These rules exist because a findings seam opened on n=1 evidence and promoted too eagerly is how the ledger metastasizes into overengineered kernel changes. Every frontier seam in this folder is expected to conform.

1. **Origin invariant.** A findings seam is opened only in response to a runtime-discovered pattern. No speculative seams. If you do not have a concrete observation from a real run, you do not have a findings seam — you have a wishlist item, which belongs elsewhere.

2. **n=1 invariant.** A findings seam at n=1 is a **note**. It captures the pattern, names the conjectured fix, and sits dormant. It does not commission implementation work. Its board status is `note` or `dormant`, not `active`.

3. **Promotion invariant.** A findings seam becomes implementable only on n ≥ 2, OR on approval of a concrete verifier experiment that would produce n=2 if the pattern is real. Codex agreement that the fix is directionally correct is **not** the same as n=2; it is agreement that if n=2 is observed the seam is ready to build.

4. **Downstream invariant.** A findings seam cannot modify the kernel directly. If a finding requires a kernel modification, it is promoted to a kernel-track item via a separate rebase decision. Kernel changes have a higher evidentiary bar than findings changes.

5. **Debate symmetry invariant.** Each findings seam has a debate log with Claude + Codex turns and an explicit **"next action"** field. Either agent can write the next turn. The operator escalates only on (a) novel framings, (b) disagreement that does not converge in N turns, or (c) domain-knowledge gaps that only the operator holds.

## Status vocabulary

For findings-track items on `ZTARE_BOARD.md`:

- `note` — n=1 observation, conjectured fix captured, not implementable, not scheduled. This is the default landing zone for a new findings seam.
- `dormant` — evidence has been captured but no further turns are expected until a triggering condition fires (e.g., "wait for Phase 2 run").
- `active` — n ≥ 2 OR a verifier experiment is approved and scheduled. Implementation work may begin when the evidence threshold is crossed.
- `verify` — implementation shipped, awaiting live confirmation.
- `closed` — verified and retired.
- `subsumed` — absorbed into another seam or into a kernel-track item; kept in history but no longer listed as live.

A findings item at `active` with n=1 is a **visible anomaly** and should be audited.

## Naming rule

- `<ID>_<slug>_seam.md`

Examples:
- `GP-021_topological_pivot_heuristics_seam.md`
- `GP-030_deterministic_charter_gate_seam.md`

## Visibility rule (public vs private)

A seam can live in this folder (`research_areas/seams/`, public, tracked in git) **or** in `[internal-ref]` (gitignored). The choice is mechanical:

A seam stays public only if **all three** hold:

1. **Shipped or closed.** Status is `verify`, `closed`, or `subsumed`. Anything `active`, `note`, `dormant`, or `blocked` that implies unimplemented work goes private by default.
2. **No exploit content.** The seam does not name a concrete attack pattern, laundering exploit, judge-softening recipe, or reframing trick that an LLM could learn to execute by reading it.
3. **No first-mover IP.** The seam does not describe a product surface, methodology primitive, observability metric, or detection technique whose value depends on being first to implement it. (Pure ergonomics with no IP value — e.g. a compile-cache lane — are public.)

Failing **any one** of the three → the seam belongs in `[internal-ref]`. The move is the visibility event: there is no frontmatter toggle, no symlink, no dual-location file. One seam, one place.

When a private seam ships and crosses into `verify`/`closed`, do **two things at the same moment**:

1. Move the seam file from `[internal-ref]` to `research_areas/seams/`.
2. Promote its row from the private board mirror (`research_areas/ZTARE_BOARD.md`) to the public board (`research_areas/ZTARE_BOARD.md`).

The two boards are paired: the private mirror is the canonical full-detail view, the public board is a sanitized subset. New seams open in whichever location their visibility classification puts them, and their row goes on whichever board matches.

When in doubt, default private. The cost of an over-classified private seam is one extra move at promotion time. The cost of an under-classified public seam is permanent.

## Canonical index

- `research_areas/ZTARE_BOARD.md` — the canonical full-detail board (gitignored). Lists every seam, public and private.
- `research_areas/ZTARE_BOARD.md` — the public board. Lists only public seams; carries a structural note that further items exist in the private mirror.
