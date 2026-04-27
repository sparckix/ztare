# information_yield.py + Signal Flow — Agent Self-Model

READ THIS BEFORE EDITING information_yield.py OR changing IterationSignal construction
sites in autoresearch_loop.py. Line numbers drift; grep to confirm.
UPDATE THIS AFTER EDITING. A stale map causes the next agent to trust wrong invariants.

last_updated: 2026-04-20

## FILE LOCATION

`src/ztare/validator/core/information_yield.py`

## PURPOSE

Stateless yield evaluator: given a list of `IterationSignal` records (one per
completed iteration), returns an `InformationYieldDecision` with `action` and
`stagnant_window`. The main loop uses `stagnant_window` as `stagnation_count`
and `action` as `pending_loop_action`.

---

## IterationSignal — FIELD SEMANTICS

| Field | Source | Novelty? | Notes |
|-------|--------|----------|-------|
| `score_improved` | `new_eval["score"] > best_score` | Early return (stagnant=0) | Checked BEFORE `has_novelty()` |
| `novel_attack_ids` | Attack surface extraction | Yes | Populated by science/v4 paths only |
| `novel_hinge_ids` | Hinge extraction | Yes | Populated by science/v4 paths only |
| `novel_primitive_ids` | Primitive extraction | Yes | Populated by science/v4 paths only |
| `verified_axioms_added` | `len(new_eval["verified_axioms"])` | Yes | **Gated on `_candidate_improved`** — 0 for reverted iterations |
| `_is_reframing_with_new_committee()` | `claim_delta_type` + `committee_digest` | Throttled | Only fires with `--dynamic`; grace=1 between improvements |
| `catastrophic_failure` | `score <= 0` or `score < 0.5 * best` | Suppresses all novelty | Forces iteration into flat tail |
| `mutation_r1_mismatch` | R1 validation | Separate path | Treated like runtime_failure |
| `runtime_failure` | subprocess crash | N/A | Counted in flat tail |

## IterationSignal CONSTRUCTION SITES (in autoresearch_loop.py)

Five sites construct IterationSignal. Grep `IterationSignal(` to locate them.

| Site | Line (approx) | Trigger | `verified_axioms_added` | `novel_*_ids` | `committee_digest` |
|------|---------------|---------|------------------------|---------------|-------------------|
| R1 mismatch | ~3472 | R1 declaration validation failed | 0 (default) | empty (default) | current_committee_digest |
| R1 mismatch v2 | ~3390 | R1 rejection (earlier try/except) | 0 (default) | empty (default) | current_committee_digest |
| R3 rejection | ~3811 | Candidate not admissible | 0 (default) | empty (default) | current_committee_digest |
| Main eval | ~3860 | Normal evaluation completed | `len(axioms) if improved else 0` | empty (default) | current_committee_digest |
| Subprocess crash | ~4222 | CalledProcessError in eval | 0 (default) | empty (default) | current_committee_digest |

**Key invariant**: Only the Main eval site can set `verified_axioms_added > 0`, and
only when `_candidate_improved` is True. All other sites leave it at default 0.

---

## DECISION STATE MACHINE

```
evaluate_information_yield(history) → InformationYieldDecision

1. latest.is_r1_failure()?
   → YES: _collect_flat_tail; if 2+ consecutive R1/crash → PIVOT; else → REFRESH

2. latest.score_improved?
   → YES: return CONTINUE, stagnant=0

3. latest.has_novelty()?
   │
   ├─ Novel attacks/hinges/primitives/axioms? → CONTINUE, stagnant=0
   │
   └─ Committee-only (_is_reframing_with_new_committee)?
      ├─ First occurrence after improvement? → CONTINUE, stagnant=0 (grace)
      └─ Consecutive committee rotation?     → FALL THROUGH (don't credit)

4. _collect_flat_tail(history) → flat_tail
   stagnant_window = len(flat_tail)

5. UNDERIDENTIFIED check (bounded_discriminator + catastrophic streak)
6. Crash-only tail (2+ runtime failures) → PIVOT
7. Same weakest_point for pivot_after iters → PIVOT
8. stagnant_window >= refresh_after → REFRESH
9. Else → CONTINUE with stagnant_window
```

## _collect_flat_tail — ACCUMULATION RULES

Walks backward from latest, collecting iterations until a "novelty boundary":

| Boundary condition | Effect |
|-------------------|--------|
| `item.score_improved` | STOP — do not include |
| Hard novelty (attacks/hinges/primitives/axioms > 0) and not catastrophic | STOP — do not include |
| Committee-only reframing AND prior was improvement or non-committee | STOP (grace boundary) |
| Committee-only reframing AND prior was ALSO committee-only noise | INCLUDE (stagnation) |
| Everything else (no novelty, no improvement) | INCLUDE |

---

## VETO SUBSYSTEM (apply_latent_motion_veto)

Called by `_evaluate_post_eval_loop_control` in autoresearch_loop.py, ONLY for
`bounded_discriminator` falsification mode.

```
Input:  raw_decision from evaluate_information_yield
Output: final_decision (possibly with action changed, stagnant_window PRESERVED)

Fires when ALL of:
  1. raw_decision.action == REFRESH_SPECIALISTS
  2. records_considered >= min_records (3)
  3. mean_max_set_distance >= threshold (0.30)

Effect: action changed to CONTINUE, stagnant_window unchanged.
Does NOT affect: PIVOT, UNDERIDENTIFIED, CONTINUE decisions.
```

Source: `src/ztare/motion/latent_distance.py` → `summarize_recent_latent_motion()`
reads `workspace/latent_distance.jsonl`, filters for `status=="ok"`, computes mean
of max(jaccard_failure_families, jaccard_attack_surface, jaccard_named_primitives)
over last 5 records.

---

## STAGNATION_COUNT FLOW (autoresearch_loop.py)

```
stagnation_count = 0                              # init (line ~2782)
    │
    ├─ Each iteration:
    │   signal = IterationSignal(...)              # one of 5 construction sites
    │   iteration_history.append(signal)
    │   yield_decision = evaluate_information_yield(iteration_history)
    │   [optional: apply_latent_motion_veto for bounded_discriminator]
    │   stagnation_count = yield_decision.stagnant_window
    │
    └─ stagnation_count used by:
        _current_loop_control_action()             # determines pivot profile
        _append_iteration_telemetry()              # written to JSONL
        GP-103 stagnation threshold check          # additive composite injection
        GP-076 divergence sweep                    # passed as context
```

---

## BUG HISTORY

### 2026-04-20: Qualitative stagnation stuck at 0

**Root cause**: `verified_axioms_added=len(new_eval.get("verified_axioms", []))` counted
axioms from REJECTED (non-improving) iterations. For qualitative projects, the judge
always extracts empirical claims → `has_novelty()=True` every iteration → stagnation
never accumulated.

**Fix**: Gate `verified_axioms_added` on `_candidate_improved` at the Main eval
signal construction site. Reverted iterations set axioms=0.

**Secondary fix**: Committee-rotation throttle in `evaluate_information_yield` and
`_collect_flat_tail` — prevents `--dynamic` mode committee rotation from suppressing
stagnation. Grace period of 1 between score improvements.

---

## COMPRESSION PIPELINE (compress_champion.py + margin_of_safety.py)

### Stage 1: Additive Templates (26 forms, expanded 2026-04-21)
Enumerates low-k additive combinations of {sqrt, log, power, exp, 1/n, 1/n^2}.
Expanded from 22 to 26: added `loglog_affine`, `log_power_free`,
`loglog_reciprocal`, `log_power_reciprocal` (`compress_champion.py` lines 71-77).
Fits each to visible evidence via curve_fit. Tests against gate harness.
Selects best gate-passing form by BIC.

### Stage 2: Compositional Templates (13 forms, depth-1 nesting)
Only activates when Stage 1 returns 0 gate-passing forms (UNDERIDENTIFIED).
Enumerates depth-1 nested compositions: sqrt(n/log(n)), sqrt(n*log(n)),
exp(sqrt(n)), log(n)^b, and combinations with corrections.
Same tight gates as Stage 1. Munger constraint: never weakens Stage 1.
Popper constraint: same or tighter gates for bolder claims.

### Backtest results (9 substrates)
- GP-088: Stage 1 found sqrt(n)+log(n)+c (correct). Stage 2 never fired.
- KWW: Stage 1 found stretched_exp (correct). Stage 2 never fired.
- DFDO: Stage 1 AND Stage 2 both return 0 (correct refusal).
- A000607: Stage 2 found sqrt(n/log(n))+log(n)+c (Vaughan form, all gates pass).
- 5 additional backtests: 0 false positives across all.

### In-loop wiring (PHASE_F.7)
Fires after champion promotion when k>=3. Calls compress_champion with
k_max=champion_k-1. If simpler form passes gates, installs to test_model.py.
Dynamic threshold — BIC decides, no hardcoded minimum.

### Phase 2.5: GP-112 Margin of Safety (added 2026-04-21)
`src/ztare/fit/margin_of_safety.py` — wired into `make discover` between
compress_champion (Phase 2) and lean_compiler (Phase 3). Runs 5 margin tests
(split-half stability, coefficient drift, grammar completeness probe, residual
autocorrelation, extrapolation stress). Closed-loop remediation on flag detection.
Output: `workspace/margin_of_safety.json`.
Pipeline flow: Phase 1 -> Phase 2 -> Phase 2.5 -> Phase 3.

### Lean 4 compiler (lean_compiler.py)
Reads gate harness results. Emits:
- `#eval check_<gate>_pass` — sorry-free Float computation (Product A)
- `axiom pslq_<param>` — sorry-bearing PSLQ conjectures (Product B)
- Evidence grids as Lean definitions

### GP-110 Statistical Fingerprint (added 2026-04-21)
`src/ztare/fit/statistical_fingerprint.py` — fires after Stage 1+2+3 all fail.
Computes: spectral slope (Welch), Hurst exponent (DFA), dominant period
(Lomb-Scargle), phase linearity (Hilbert), amplitude envelope (power-law fit),
arithmetic energy fraction (Ramanujan residue-class test).
Output: `StatisticalFingerprint` dataclass → `workspace/statistical_fingerprint.json`.
Backtest: 5 substrates, fires ONLY on Ulam (0 false positives).
Hurst/slope consistency warning when |beta - (2H-1)| > 0.3.

### PSLQ bridge (mpmath.identify + curated constant library)
Maps fitted floats to exact constants within 5% tolerance.
Curated library: pi, sqrt(2), sqrt(3), pi*sqrt(2/3), ln(2), etc.
Falls back to mpmath.identify for uncurated constants.
GP-088: identified ch1_a ≈ pi*sqrt(2/3) (Hardy-Ramanujan leading coefficient).
