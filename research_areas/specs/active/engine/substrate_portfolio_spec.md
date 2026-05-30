# `substrate_portfolio` — sequential portfolio runner — spec v0

**Parent seam:** `GP-213_operator_role_mechanization_seam.md` (director-mechanization).
**Companion seam:** `GP-228_substrate_portfolio_v05_v3_seam.md` (anti-anchoring composition).
**Status:** v0 spec written 2026-05-07; module shipped at `src/ztare/research_director/substrate_portfolio.py`.

## 1. What this builds

A kernel module + Make targets that turn the substrate portfolio (the set of meta-apparatus / ZTARE-on-ZTARE substrates running in rotation) from a hand-managed convention into a YAML-registered, sequentially-dispatched mechanism.

- **Module:** `src/ztare/research_director/substrate_portfolio.py`
- **Registry:** `org/runtime/substrate_portfolio.yaml`
- **Make targets:** `make portfolio-list`, `make portfolio-scaffold`, `make portfolio-run [ITERS=N] [ONLY=<slug-substring>]`
- **Work-discovery hook:** `discover_substrate_portfolio_opportunities()` in `src/ztare/orchestration/work_discovery.py` — proposes `scaffold` and `rotate-eigenquestion` candidates for the research_director role

## 2. Why now

Run-5 of `ztare_on_ztare_v2_expanded_scope` produced the same primitive family for the 5th time despite v0.3 lane-ceiling-asymmetry + v0.4 class-rotation. The post-mortem identified the root cause as eigenquestion monoculture: ONE substrate × K iters keeps producing K iters of one family; what's needed is K substrates × 1 iter each, with deliberately-distinct eigenquestions.

Pre-spec, this was implemented as a one-shot script under `scripts/public/`. That violates the "scripts are operator one-shots, kernel features go in `src/ztare/`" rule. This spec moves the capability into the kernel proper and wires it into the GP-128 daemon's work-discovery surface.

## 3. Inputs

The runner reads (and only reads):
- `org/runtime/substrate_portfolio.yaml` — the registry (members + eigenquestion summaries + scaffolded flags)
- `rubrics/<slug>.json` — per-member rubric (existence-checked before run)
- For work-discovery: `analytics/public/queries/rd/cross_substrate_explored_classes.jsonl` — the cross-substrate exclusion ledger

No write access to apparatus state. Only `make loop` subprocess invocations + (in `scaffold` mode) charter-stub writes under `projects/<slug>/`.

## 4. Output

- **`list` mode:** stdout enumeration of registry members with eigenquestion + scaffolded status
- **`scaffold` mode:** for each non-scaffolded registry member, creates `projects/<slug>/project_charter.md` + `projects/<slug>/raw/`. Operator authors the rubric.
- **`run` mode:** invokes `make loop` for each member sequentially; emits a per-substrate result table at the end. Cross-substrate exclusion ledger §25 in `rubric_specification.md` is updated by the loop itself (this runner just sequences invocations).

## 5. Operator-confirmed only in v0

This module does NOT auto-launch substrates from the registry. Operator (or the GP-128 daemon under `--unattended` with role-authorized mandate) invokes `make portfolio-run`. Future v1 may wire auto-rotation into the daemon when a substrate's cross-substrate ledger shows family-attractor behavior; v0 surfaces this as an advisory work candidate via `discover_substrate_portfolio_opportunities()`.

## 6. Promotion criteria for adding a portfolio member

Documented in `org/runtime/substrate_portfolio.yaml` itself:
1. Eigenquestion structurally orthogonal to existing members
2. Project + rubric authored to spec (rubric_specification.md §§22-27)
3. Operator or research_director signoff in `opened_by`

## 7. Code references

| File | Function |
|---|---|
| `src/ztare/research_director/substrate_portfolio.py` | `load_registry`, `cmd_list`, `cmd_scaffold`, `cmd_run` |
| `src/ztare/orchestration/work_discovery.py` | `discover_substrate_portfolio_opportunities` |
| `org/runtime/substrate_portfolio.yaml` | registry |
| `Makefile` | `portfolio-list` / `portfolio-scaffold` / `portfolio-run` |

## 8. Dependencies

- GP-213 (director mechanization) — parent seam, established the kernel-module + operator-confirmed pattern
- GP-228 (substrate-portfolio + anti-anchoring composition seam) — the WHY for the registry
- GP-128 (persistent-agent daemon) — consumes work-discovery output
- rubric_specification.md §§22-27 — the discipline stack each portfolio member must compose
