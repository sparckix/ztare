# GP-228 — Substrate-portfolio v0.5 stack + v3 strange-loop variant + agent-agnostic Director role

> **Seam metadata** · `seam_id:` GP-228 · `track:` reflexive · `status:` active - kernel modules + Make targets + work-discovery wiri · `last_updated:` 2026-05-09


**Status:** active — kernel modules + Make targets + work-discovery wiring shipped 2026-05-07
**Parents:** GP-128 (persistent-agent daemon), GP-167 (multi-agent interface form factor), GP-213 (operator-role mechanization), GP-226 (charter-critic role)
**Children:** TBD — first portfolio-rotation cycle pending; v3 strange-loop test pending

## Eigenquestion

How should the apparatus break the family-attractor failure mode (one substrate × K iters → K iters of one primitive family) without reverting to operator-curated substrate launches?

## Triggering incident (2026-05-07)

`ztare_on_ztare_v2_expanded_scope` ran 5 times (run IDs 1778108910, 1778109..., 1778110098):
- All 5 produced a single primitive family (ACRR in run 4 → PECVP in run 5 — same mechanism, new label)
- v0.3 lane-ceiling-asymmetry caught lane anchoring (good)
- v0.4 class-rotation caught name-level repetition (good)
- Neither caught **mechanism-level** rebadging or **eigenquestion monoculture**

Operator surfaced the diagnosis: "the FRAME is the suspect, not the code" (the de-anchoring fractal pattern from `feedback_fractal_deanchoring.md`). Fixed eigenquestion = fixed basin.

## The 4-layer composition (rubric_specification.md §§22-25)

Each layer attacks a different anchoring mode; ALL FOUR needed for meta-apparatus substrates. Single layers were tried in isolation and failed:

| Layer | Flag | Anchoring mode it catches |
|---|---|---|
| §22 class-rotation | `enable_primitive_class_rotation: true` | name-level repetition within a run |
| §23 lane ceiling-asymmetry | `_lane_ceiling_asymmetry: {...}` | settling in the easy lane (tactical patches over primitive classes) |
| §24 adversarial judge | `enable_adversarial_judge_mode: true` | mechanism-level rebadging (PECVP=ACRR) within run + cross-run |
| §25 cross-substrate exclusion | `enable_cross_substrate_exclusion: true` | rediscovery across substrates that share an eigenquestion neighborhood |

These are persona-enforced (not separate gate modules); the rubric persona reads each flag's block and refuses to score above the relevant ceiling.

## The architectural extension — GP-228 (this seam)

Rotation + ceiling + adversarial + cross-substrate exclusion attack the symptom (the mutator picking the same family). They don't address the **eigenquestion-fixedness root cause**. Two new mechanisms address the root:

### 1. Substrate portfolio (rubric_specification.md §27)

Instead of ONE substrate × K iters, run K substrates × 1 iter each, with deliberately-distinct eigenquestions. Mechanized as:
- **Registry:** `org/runtime/substrate_portfolio.yaml` — adding a member is a YAML edit
- **Runner:** `src/ztare/research_director/substrate_portfolio.py` — sequential dispatch (cross-substrate ledger §25 depends on order)
- **Make targets:** `make portfolio-list / portfolio-scaffold / portfolio-run`
- **Work-discovery hook:** `discover_substrate_portfolio_opportunities()` proposes scaffold + rotate-eigenquestion candidates to the research_director role

Five members at v0:
1. `ztare_on_ztare_v2_expanded_scope` (apparatus-additive baseline)
2. `ztare_on_ztare_v3_meta_recursive` (substrate-architecture proposals)
3. `ztare_on_ztare_subtractive` (retire-existing-primitive proposals)
4. `ztare_on_ztare_red_team` (apparatus-fragility proposals)
5. `ztare_on_ztare_evaluation_surface` (Newton-mode surface-opening proposals)

### 2. v3 meta-recursive strange-loop variant

A substrate explicitly allowed to propose its own architectural evolution. v2's charter forbade meta-level proposals (anti-contamination); v3 relaxes this under three safeguards:
- **Recursion budget = 1**: proposed variants cannot themselves be v3-meta-recursive
- **Min 1 object-level per 3 meta-level proposals** (judge-persona enforced)
- **Mandatory `meta_recursion_guard` field** on every meta-level proposal

The strange-loop hypothesis (open question, untested at seam date): does a substrate that's allowed to propose its own architectural evolution actually produce architectural evolution, or does it family-attractor at the meta level?

### 3. Frontier-eigenquestion advisor (rubric_specification.md §27)

LLM-drafted advisory eigenquestion when a substrate's cross-substrate ledger shows ≥3 runs in one class. Module: `src/ztare/research_director/eigenquestion_generator.py`. Make target: `make eigenquestion-propose PROJECT=<slug>`. Operator-confirmed only — never auto-modifies the charter.

## Composition with existing org primitives

This is where the user's correction landed (2026-05-07): the original implementation was standalone scripts under `scripts/public/`, duplicating governance machinery already in the org runtime. The integration:

| Existing primitive | What it provides | How GP-228 uses it |
|---|---|---|
| `org/roles/research_director.yaml` | Persistent role contract — authorized paths, delegation, budget, agent-utilization caps | The Director role dispatches portfolio runs + reviews advisory eigenquestion drafts. Authorized paths already include `projects/*/workspace/`, `research_areas/`, `org/sessions/`. |
| `scripts/public/control/agent_daemon.py` (GP-128 L2) | Long-running governance loop (discover work → propose → approve via Telegram → execute via configured agent CLI → record) | Daemon's tick loop discovers GP-228 portfolio opportunities via `work_discovery.discover_substrate_portfolio_opportunities()`, surfaces them as approve-able candidates. |
| `src/ztare/orchestration/work_discovery.py` | Candidate-source registry (TODO scan, damage signals, principal goals, agent-channel messages) | New source: `discover_substrate_portfolio_opportunities` (scaffold + rotate-eigenquestion candidates). Filtered to research_director / principal roles. |
| `src/ztare/research_director/` (GP-213) | Director-side kernel module home — already has `substrate_recommender`, `retirement_detector`, `phase_runner` | New modules: `substrate_portfolio.py` + `eigenquestion_generator.py`. Same operator-confirmed-only-in-v0 pattern. |
| `ZTARE_AGENT_CLI` env var (GP-128) | Agent-CLI selection (default claude; codex/gemini pluggable) | The Director role is **agent-agnostic** by construction — Claude, Codex, or open-source agents can fill the role; the daemon dispatches whichever is configured. |

## Agent-agnostic Director-role doctrine (per GP-167 architecture invariant)

> "`org/` files are the system of record. Any interface is a projection. Git history is the audit trail. The interface can be replaced without losing governance state."

Applied to the autonomous-Director question:
- **The role is a file** (`org/roles/research_director.yaml`) — agent-agnostic
- **The mandate is a file** (`org/mandates/research_director_mandate.md`) — agent-agnostic
- **Work candidates are files** (deposited into `ztare_workspace/inbox/...`) — agent-agnostic
- **Decisions are files** (deposited into `org/directives/`, `org/sessions/<role_id>/<ts>/`) — agent-agnostic
- **The daemon dispatches to a configured agent CLI** (`ZTARE_AGENT_CLI=claude|codex|...`) — agent-agnostic
- **The orchestrator (substrate_portfolio.py) is pure Python** — no agent at all in the run-mine-run loop; agent enters only at the judgment layer (review work candidates, decide which to approve)

This decomposition means: a Claude session, a Codex session, an open-source-agent session, OR a human can fill the Director role. The org/ files persist across all of them. The daemon ticks regardless of which agent is configured. Replacing the agent runtime does not lose governance state.

## What's still missing (post-2026-05-07 backlog)

1. **First portfolio-rotation cycle** — run all 5 members through `make portfolio-run --iters 5` to validate sequential dispatch + cross-substrate ledger behavior under load
2. **v3 strange-loop test** — first run of `ztare_on_ztare_v3_meta_recursive` to test the strange-loop hypothesis
3. **Daemon `--unattended` policy for portfolio dispatch** — currently the Director role has the mandate; what conditions auto-approve a `make portfolio-run` proposal vs require Telegram approval? Defer to GP-128 mandate-tuning seam.
4. **`charter_patches_preflight_mode: "auto_confirm"` rollout** — flip portfolio members from interactive to auto_confirm once cross-family reviewer LLM has 10+ approved patches calibrating its policy
5. **Eigenquestion-rotation auto-fire** — currently `discover_substrate_portfolio_opportunities` proposes when ledger shows ≥3 runs in one class. v1 may chain to auto-invoke `make eigenquestion-propose` and surface the advisory file as the work candidate (not the rotation invocation).

## Cross-references

- `docs/concepts/rubric_specification.md` §§22-27 — the discipline stack (authoritative)
- `docs/internal/agent_workflow/rubric_authoring_map.md` §5b — anti-anchoring decision matrix for rubric authors
- `docs/guides/experiment_cookbook.md` §0B — operator-facing recipe
- `org/runtime/substrate_portfolio.yaml` — registry
- `src/ztare/research_director/substrate_portfolio.py` — runner
- `src/ztare/research_director/eigenquestion_generator.py` — advisor
- `research_areas/private/specs/active/engine/substrate_portfolio_spec.md` — spec
- `research_areas/private/specs/active/engine/eigenquestion_generator_spec.md` — spec

## Sentinel

`SENTINEL_DECISION: open` — first portfolio-rotation cycle and v3 first-run pending; promotion to `closed` requires:
  (a) ≥1 full portfolio cycle completed
  (b) v3 first run with reported strange-loop hypothesis verdict (object-only retreat / meta family-attractor / successful strange loop)
  (c) Daemon `--unattended` policy for portfolio dispatch decided
