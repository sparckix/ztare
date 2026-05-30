# GP-217 — Daemon continuity + empirical mandate broadening

> **Seam metadata** · `seam_id:` GP-217 · `track:` engine · `status:` shipped (mechanisms), proposed (mandate edits) · `last_updated:` 2026-05-09


**Status:** shipped (mechanisms), proposed (mandate edits)
**Date:** 2026-05-05
**Audience:** internal engineering + governance
**Sister docs:** GP-148 (Mining the Void), GP-216f (Cross-scale fractal map), `org/bootstrap_manifest.yaml`, `analytics/public/queries/rd/decision_history_calibration.md`

---

## Eigenquestion

> Why do dockerized agents feel checkpoint-anxious, and what would actually fix it?

## Two-line answer

Two compounding problems: (1) mandate scope is calibrated by intuition, not evidence — agents escalate on classes of decisions that historically didn't require principal in the loop; (2) every tick spawns a fresh subprocess with no memory of prior ticks, so even when scope is broad enough, the daemon rebuilds context every 5–20 minutes. The fix is two-pronged: mine the empirical decision history to defend mandate broadening, and wire `claude --resume` + a per-task checkpoint so context persists across ticks.

---

## Problem framing

**Symptom:** principal observes that dockerized daemons (`scripts/public/control/agent_daemon.py`) feel low-throughput compared with foreground sessions. Suspicion: too many escalations + no continuity = small effective unit of autonomous work per tick.

**Decomposition:**

1. **Scope calibration gap.** Role mandates currently lean "escalate on ambiguity." Empirically, that's a bigger surface than reality: ~85% of `research_director`-affinity F-rows in our 262-row corpus closed without principal-explicit signal. Mandates over-index on caution.

2. **Cross-tick amnesia.** Daemon spawns `claude --print -p <prompt>` fresh every tick. No memory of what last tick concluded. Every tick rebuilds context from disk (AGENTS.md + role yaml + mandate + bootstrap chain), then exits. A multi-step task either fits in one tick or fragments across ticks with each re-paying the bootstrap cost.

3. **Cadence mismatch.** Default 600s tick interval. Claude prompt cache TTL is 300s. So even with `--resume` the cache is cold every tick at default cadence — the cache penalty is paid 12× per hour for nothing when idle, and is unnecessarily missed when active.

These compose: narrow scope causes more escalations, amnesia means each escalation is informationally expensive, fixed cadence wastes both cache and tokens.

---

## Mechanism 1 — empirical mandate broadening (GP-148 self-applied)

**Apparatus:** `scripts/public/mining/mine_decision_history.py`. Walks F-rows in `research_areas/EXPERIMENT_TRACK_RECORD.md`, classifies each closed decision by signal:

- **principal-driven**: paths under `papers/`, `org/mandates/`, `org/preferences/`, `org/directives/`, `AGENTS.md`, OR keywords matching SSRN / promotion / paper-grade / naming / INS- references
- **agent-driven**: paths under `src/`, `scripts/public/`, `tests/`, `docs/internal/`, `analytics/public/`, `research_areas/private/seams|specs/`, OR keywords matching shipped/refactor/audit/mechanized/falsifier/lean-proof
- **mixed**: both signal classes fire
- **unknown**: no signals

Outputs `analytics/public/queries/decision_history_calibration.{json,md}`. Re-runnable monthly.

**Empirical findings (2026-05-05 run):**

| Class | Count | Share |
|---|---|---|
| Principal-driven | 23 | 9% |
| Agent-driven | 157 | 60% |
| Mixed | 27 | 10% |
| Unknown | 55 | 21% |

Plus: 8 principal directives filed total in corpus; 9 resolved gates total. The principal-load is small and concentrated.

**Role-affinity table:**

| Role | Total | Agent-share |
|---|---|---|
| engineer | 7 | 71% |
| research_director | 120 | 85% |
| principal | 1 | 0% |
| unknown affinity | 134 | 37% |

**Top directories agent drove closure on (no principal signal):**

| Directory | Agent-driven F-rows |
|---|---|
| `projects/ns_millennium_hunt/` | 62 |
| `research_areas/private/` | 35 |
| `projects/gp163d_unified_accel/` | 16 |
| `ztare_proofs/ZtareProofs/` | 7 (research_director) + 4 (engineer) |

Currently `research_areas/private/` is NOT in research_director's `authorized_paths` (only public `research_areas/` is), and `ztare_proofs/` is in nobody's. Empirically, these are exactly where the autonomous research is happening.

**Proposed broadening (filed as `org/directives/20260505-empirical-mandate-broadening-v1.json`):**

- `research_director.yaml` `authorized_paths`: add `research_areas/private/` and `ztare_proofs/`
- `engineer.yaml` `authorized_paths`: add `ztare_proofs/`
- `research_director_mandate.md`: add explicit "act-and-flag scope" section listing categories that close autonomously vs categories that escalate

Each broadening cites 3+ historical F-rows. Status: proposed, awaiting principal approval.

**Calibration discipline:** re-run miner monthly. Intended signal: agent-share trends up after broadening (intended); principal-driven counts in `papers/` + `org/` stay stable (failure mode would be principal-driven decisions getting silenced).

---

## Mechanism 2 — daemon continuity (cross-tick `--resume` + per-task checkpoint)

**Apparatus:** `src/ztare/orchestration/daemon_continuity.py`. Two related primitives:

### 2a. Cross-tick session resume

- Per-role persistent Claude session id stored at `org/sessions/daemon/<role_id>.json`
- `get_or_create_claude_session_id(role_id)` returns the active id with `is_new=True` on first creation/rotation, `is_new=False` on subsequent ticks
- Daemon passes `--session-id <uuid>` (first use) or `--resume <uuid>` (subsequent) to `claude --print`
- Auto-rotates when stale: `tick_count >= 100` OR `age >= 24h`. Prevents unbounded conversation growth.
- `note_tick(role_id, success=, summary=)` increments tick_count + appends bounded tick log
- Codex's `codex exec` does not support resume — codex_exec adapter is unaffected

### 2b. Per-task checkpoint

- `org/sessions/<org_session_id>/state.json` — flat JSON with prior tick's claimed_id, task_intent, status, last_summary
- `write_task_checkpoint(...)` called at end of every tick (success path) AND on no-work tick (with status="no_work")
- `read_task_checkpoint(...)` called at start of execute_task; prior tick conclusion is appended to the next tick's prompt as a "PRIOR TICK CHECKPOINT" hint
- Composes with --resume: resume gives in-conversation memory; checkpoint gives crash-resilience and is the canonical "where was I" surface

### 2c. Variable tick cadence

- New `--variable-interval` flag in `agent_daemon.py`
- After a tick that dispatched real work: sleep `ACTIVE_TICK_INTERVAL = 270s` (under Claude's 5-min cache TTL)
- After an idle tick: sleep `IDLE_TICK_INTERVAL = 1200s` (20 min; saves cost when nothing to do)
- Old fixed-`--interval` semantics preserved for back-compat; opt-in to variable mode

`tick()` now returns `bool` (did_work). All early-return paths return `False`; success path returns `True`.

---

## Files

**New:**
- `scripts/public/mining/mine_decision_history.py` — miner + reporter
- `src/ztare/orchestration/daemon_continuity.py` — resume + checkpoint primitives
- `analytics/public/queries/decision_history_calibration.{json,md}` — calibration output
- `org/directives/20260505-empirical-mandate-broadening-v1.json` — broadening proposal

**Edited:**
- `scripts/public/control/agent_daemon.py` — wires resume + checkpoint + variable interval; `tick()` returns bool
- `org/bootstrap_manifest.yaml` — earlier turn (knowledge graph + query helper as conditional reads)
- `AGENTS.md` — earlier turn (§6i.6 knowledge graph pointer)
- `scripts/public/control/org_role_preflight.py` — earlier turn (graph + helper hard-fail checks)

---

## Lakatosian pass/fail

**Pass criteria:**
1. `python scripts/public/mining/mine_decision_history.py` exits 0 and produces a calibration markdown with per-role agent-share numbers.
2. `python scripts/public/control/agent_daemon.py --tick-once --dry-run --role manager` runs without error.
3. Continuity smoke test: `get_or_create_claude_session_id` returns same uuid on second call (resume), `is_new=True` on first; checkpoint round-trips through write+read.
4. After mandate broadening is applied, monthly re-run of miner shows agent-share for `research_director` ≥ baseline (failure mode: drops, meaning broadening was too narrow).
5. Daemon running with `--variable-interval` for 24h: principal-driven decision count in `papers/` does not drop below baseline (failure mode: continuity made the agent slip into principal-domain work without flagging).

**Fail criteria (would retract):**
- Miner classifier proves systematically biased — independent eyeball of 30 random F-rows disagrees with the classifier on >25% of them.
- `--resume` causes context-collapse failures (the agent confuses prior-tick state with current work) more than once a week.
- After broadening, principal observes work happening in newly-authorized paths that should have escalated.

---

## What this is NOT

- **Not a paper.** This is operational mechanism + apparatus. The methodology (mining your own decision history to calibrate your own scope) is closer to a Pattern 11 self-application than a research finding.
- **Not a substitute for telemetry.** The miner classifies historical F-rows; it doesn't tell you what daemon throughput will look like after broadening. That requires live operation. The calibration_followup section in the directive proposes monthly re-runs as the regression test.
- **Not a unification of resume + scope.** They're independent levers. Broadening alone increases throughput at fixed cadence. Resume alone preserves memory but does nothing about scope. Variable cadence alone reduces cost. The combination is what makes dockerized agents productive; each is independently shippable.

---

## Connection to existing primitives

- **GP-148 (Mining the Void)** — this seam is GP-148 self-applied. We mined the autoresearch corpus for blindspots; here we mine the org-decision corpus for scope-calibration evidence.
- **GP-216f (Cross-scale fractal map)** — cross-scale aliases include "decision-history mining" at the org-scale (this seam) ↔ "F-row recordkeeping" at the experiment-scale ↔ "transition logging" at the daemon-scale. Same pattern: bounded vocabulary + apparatus enforcement.
- **GP-128 Level 2 (persistent autonomous agent daemon)** — this is the operational layer GP-128 was built for; continuity primitives close the cross-tick gap that GP-128 left open.

---

## Open questions

1. **Session-rotation cadence.** 100 ticks / 24h are educated guesses. If conversations grow faster than expected, may need tighter rotation; if cache stays warm longer than 5 min in practice, may need looser. Monitor `org/sessions/daemon/<role>.json` tick_count + actual cost-per-tick.
2. **Per-task vs per-role session.** Currently one session per role. Alternative: one session per (role, claimed_task) tuple. Tradeoff: per-task = cleaner context isolation, more uuids; per-role = role-level memory across many tasks, larger conversation. Empirical call once we have ≥48h of data.
3. **Codex parity.** `codex exec` doesn't support resume. If codex_exec becomes a primary adapter, we need either (a) Codex feature request to upstream, or (b) a different continuity mechanism for codex (e.g., manually injecting prior-tick conversation as part of the prompt). Out-of-scope for now.
