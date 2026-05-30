# GP-071 Executive Inbox Seam

> **Seam metadata** · `seam_id:` GP-071 · `track:` apparatus · `status:` `debate` (spec drafted 2026-04-15, debate pending) · `last_updated:` 2026-05-08


**Track:** supervisor / operator surface
**Status:** `debate` (spec drafted 2026-04-15, debate pending)
**Authorizing turn:** `D4_distribution_form_factor_seam.md` Turn 4 (Operator, 2026-04-15) — carve-out from the v1 external product brief
**Spec under debate:** research_areas/private/specs/active/GP-071_executive_inbox_spec.md
**Depends on:** GP-036 (runner writes `ztare_workspace/gates/pending/` with `advisory: true`), GP-070 (hybrid architecture declares gates as the core↔operator transition boundary)
**Related:** research_areas/private/seams/D4_distribution_form_factor_seam.md, research_areas/private/seams/GP-070_meta_supervisor_goal_orchestrator_seam.md

---

## Problem Snapshot

GP-036 ships a findings runner that emits gate escalation records to `ztare_workspace/gates/pending/*.json` with `advisory: true` and then exits fire-and-forget. Today there is no reader for that directory; the operator opens JSON files in an IDE. This is the operational bottleneck blocking unattended runs of the hybrid supervisor architecture GP-070 just reopened.

D4 Turn 4 authorized a carve-out: a narrowly scoped internal tool for the operator to clear the gate queue, strictly separated from the v1 external product brief (Workbench + Judgment Coach). GP-071 is that tool's spec.

## What this seam debates

The spec at `research_areas/private/specs/active/GP-071_executive_inbox_spec.md` is the concrete draft. This seam's job is to stress-test it before any code lands. The spec is auto-injected into the debate prompt via the `SPEC_EXCERPT` context tier (GP-036 `findings_context.py`), so the agents see its current contents directly.

**Decisive claims from the draft to debate:**

1. **Advisory-only, not blocking HITL.** The runner stays fire-and-forget. Approve / Reject / Defer are audit writes, not resume signals. Revisit only after 30 days of operational data shows "approved but forgot to re-run" as a repeating failure mode. Is this the right default, or is it premature optimization for a gap that will bite immediately?
2. **File-system-as-API with atomic resolve.** Two-phase write (tempfile + rename, then delete pending); startup reconciliation when both files exist. Is this atomicity story complete, or are there failure modes (process kill between fsync and rename; concurrent Streamlit instances; NFS) the spec misses?
3. **Payload schema mismatch risk.** The spec codes against the verified GP-036 payload (`seam_path`, `escalation_reason`, `equivalent_gate_reason`, `cycle_count`, `total_cost_usd`, `notes[]`, `timestamp_utc`, `advisory`). It explicitly rejects a `findings_context` field that does not exist. Is the fallback render branch (degraded-but-safe) sufficient for GP-039's future generalized gate library, or will it force a schema migration?
4. **Factored architecture: `inbox_state.py` pure + `inbox_streamlit.py` thin wrapper.** 10 fixture tests mandated on `inbox_state`. Streamlit is out of the regression suite. Is this split clean enough that a future replacement of Streamlit (stdlib http.server, or a D4 shared design system) is a file swap, or does the spec leak framework assumptions into the state module?
5. **Visual register = forensic-adjacent.** Monospace, minimal chrome, status color on stroke only, permanent top-of-page banner as the visual firebreak against becoming the Workbench. Is this enough to prevent scope creep into an authoring surface, given Streamlit's defaults push in the opposite direction?
6. **UX/UI spec required before implementation.** §10b mandates a one-page visual spec (two hand-drawn wireframes, state transition table, type/color tokens) as the prerequisite before any Streamlit code. Is this the right gate, or is it over-process for a 50-line wrapper?
7. **Queue ordering by `total_cost_usd` descending.** Rationale: "CEO reads the thing burning the most budget first." Is this the right default, or is it biased by the current small-queue assumption that will invert when the queue has both cost-budget and escalated-cap items competing?

## Non-goals this seam must not re-open

- The runner's fire-and-forget contract with GP-036 is NOT up for revision here. If the debate concludes advisory-mode is insufficient, the correct move is a separate seam requesting a runner contract change — not patching it in this seam.
- GP-039 gate library formalization is out of scope. This seam codes against GP-036's current payload only.
- Authentication, multi-user, cloud hosting — all deferred per D4 brief §11. Do not re-litigate.

## Convergence criteria for this seam

Both agents (Author + Skeptic under `single_claude` mode) produce at least two turns, and each agent's most recent turn carries the `no_new_load_bearing` sentinel per GP-031. If the debate raises a decisive change to the spec, the operator edits the spec between turns (the spec is re-injected on the next turn via the `SPEC_EXCERPT` tier, so the debate sees the updated version). When convergence fires, the operator either (a) seals the spec draft status → `ready` and begins implementation of `inbox_state.py`, or (b) opens a GP-071 visual spec stub and blocks implementation on it per §10b.

## Debate Log

<!-- Turns are appended by src/ztare/validator/supervisor_findings_runner.py.
     Do not hand-edit; use the runner in execute mode. -->
