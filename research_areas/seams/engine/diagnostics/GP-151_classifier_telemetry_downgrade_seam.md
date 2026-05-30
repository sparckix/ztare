# GP-151 — Classifier Telemetry Downgrade & Super-Class Routing

> **Seam metadata** · `seam_id:` GP-151 · `track:` engine · `status:` draft / debate-mode (not yet resolved) · `last_updated:` 2026-05-09


**Status:** draft / debate-mode (not yet resolved)
**Date:** 2026-04-24
**Prompted by:** Gemini Pro message post 2026-04-24 cross-LLM classifier audit (48% three-way agreement, κ≈0.57); operator ask to seam + debate before implementing.

## 0. Problem statement — one sentence

The runtime classifier's 15-class taxonomy is the same taxonomy that three frontier LLMs agreed on only 48% of the time; any live routing built on the fine-grained labels inherits that disagreement as iatrogenic drag, so we must decide whether to (a) coarse-grain live routing to a binary super-class, (b) enforce quorum across lightweight classifiers, or (c) downgrade the classifier entirely to observability and disconnect it from branch conditions.

## 1. What is actually live today — audit

Four sites use `classify_weakest_point` in `autoresearch_loop.py`:

| Site | Line | Usage | Cross-LLM risk |
|---|---|---|---|
| **A. Task 12 class-novelty stagnation** | ~1469 (`_populate_weakest_class`) | Fine-grained class stored on `IterationSignal.weakest_class`; `evaluate_information_yield` treats "class not seen earlier in session" as novelty → resets stagnation. | **Low.** The regex classifier is DETERMINISTIC within a session (same text → same label). The 48% disagreement is cross-model; our runtime uses regex, not LLMs, so within-session consistency is near-100%. |
| **B. GP-149 I-2 observability** | ~3657 | Tracks cardinality of distinct classes seen → suppresses pivot if <N distinct classes. **Cardinality only**, not label identity. | **Low.** Counts are robust to label noise as long as labels are stable within a session (regex → yes). |
| **C. GP-149 I-3 pivot-ineffective routing** | ~3666 | Checks membership: `class ∈ {tail_generalization, unverified_bound}` → in `"suppress"` mode, skips topological pivot. | **HIGH.** The set membership {tail_gen, unverified_bound} was chosen from LLM-classified mining data (~GP-148 Stage 2). If three LLMs would disagree on which class a weakest-point belongs to, the set-membership gate is 52%-unreliable. Currently `"observe"` mode by default — not yet live. |
| **D. Inject anti-pattern catalog (I-1)** | ~1976 | Text injection into mutator prompt. Already split: `"hardkill"` injects Part 1 only (cross-judge-validated); `"ceilingbreaker"`/`"both"` emits warning. | **Addressed.** Split 2026-04-24; not further affected by GP-151. |

**Upshot:** The only currently-live fine-grained routing at risk is **Task 12 class-novelty**. The only *planned* live routing is **I-3 suppress mode**, which is not yet enabled.

The classifier itself is a 15-class regex — not an LLM. So within-session label disagreement is ~0% (deterministic on input text), not 48%. Gemini's "48% random walk" concern applies to a world where the runtime classifier was an LLM, which it isn't.

**What IS 48%-disputed:** the ORIGIN of the set `PIVOT_INEFFECTIVE_CLASSES = {tail_generalization, unverified_bound}`. This set came from GP-148 Stage 2 mining, which used LLM-reclassification of 842 unclustered records. If three LLMs disagreed on labels in that pool at 48%, then the empirical frequency lifts assigned to classes in that pool are 48%-noisy, and "tail_generalization has mean Δ −0.7" is decisive on disputed LLM labels.

## 2. Three candidate paths (Gemini's framing)

### Path A — Coarse-grain live routing to super-class

- Add to `weakest_link_classifier.py`: `classify_super_class(text)` returns one of `{"structural_blocker", "ceiling_breaker", "other"}`.
- Task 12 class-novelty: optional super-class mode — reset stagnation on super-class novelty instead of fine-grained.
- I-3 suppress mode: gate on super-class membership (never live on fine-grained).

**Pros:** Structurally insulates live routing from cross-LLM disagreement. Preserves the signal we actually believe (structural-blocker vs ceiling-breaker, per mining).
**Cons:** Weaker novelty signal for Task 12 (only 2-3 super-classes vs 15 fine → fewer "new class" events → stagnation triggers earlier). For I-3, super-class is less actionable than fine-grained.

### Path B — Quorum gate (3 lightweight LLM classifiers, ≥2 agreement)

- At iteration-close: fire three lightweight classifiers (gpt-4o-mini, claude-haiku, gemini-flash) on the weakest-point string.
- Fine-grained routing only engages if ≥2 agree. Otherwise fall back to super-class or generic.

**Pros:** Highest-fidelity fine-grained signal. Empirically validated (Gemini recommendation).
**Cons:** **Budget explosion.** Each iteration pays 3× classification cost. At ~1800 trajectory iterations, that's 5400 extra classifier calls per rerun. For mining, this is one-time. For live runs, this is per-iteration compounding. Also adds 3 network dependencies.

### Path C — Observability-only downgrade

- Continue computing fine-grained regex labels for LOGS, telemetry, and mining inputs.
- Disconnect from all live branch conditions. Task 12 reverts to score-only mode by default. I-3 stays "observe" indefinitely until quorum data is collected.

**Pros:** Zero iatrogenic drag risk. Maximally conservative.
**Cons:** Loses the mining-derived signal we already paid compute for. Leaves GP-149 interventions as purely observational — the champion-persistence-profile insight goes unused in live steering.

## 3. Debate — my read

The cleanest composition is **Path A + C** together:

1. **Path A structurally**: add `classify_super_class` helper. Make Task 12 support both modes (fine-grained = default, super-class = opt-in). Make I-3 only-ever operate on super-class when promoted from observe.
2. **Path C by default**: keep I-3 observe-only until we have within-session quorum evidence. Keep Task 12 at fine-grained only because regex is deterministic (no cross-LLM issue at runtime). Document that the 48% issue applies only to the origin of `PIVOT_INEFFECTIVE_CLASSES`, not to the regex classifier itself.
3. **Path B later**: only if within-session regex labels prove empirically misaligned with judge-validated failure modes — add quorum then. Not worth paying 3× today.

Specifically:

- **Task 12 (class-novelty stagnation)** is LOW risk as currently implemented. The rubric flag lets operators opt in per-project. If we add super-class mode as `stagnation_trigger_mode: "new_super_class"` alongside `"new_class"`, operators can choose the robustness level. **Keep current `"new_class"` mode available; add `"new_super_class"` as a more-conservative option.**
- **I-3 pivot-ineffective** should stay `"observe"` until we re-mine the frequency lifts under super-class grouping. That mining is cheap (re-run Stage 2 with super-class instead of fine-class). If super-class lifts are >90% agreement-stable, promote I-3 to "suppress" on super-class only.
- **GP-148 mining data itself** is NOT re-done; its role is historical. But future mining should bucket by super-class first, with fine-grained as secondary optional facet.

## 4. Open questions for multi-agent debate

1. **Is within-session regex determinism enough to justify keeping fine-grained for Task 12?** (Gemini's concern was about LLM classifiers; ours is regex. The disagreement question doesn't obviously apply to deterministic code. But: is the regex itself *well-aligned* with the judge's underlying failure-mode taxonomy? Separate question from the cross-LLM one.)

2. **Is the 15-class taxonomy too fine for MINING purposes too**, not just live routing? If LLM classifiers disagree 52% of the time on which fine class an example is, the mining frequency tables we already produced may be noisy and the GP-149 interventions derived from them may be pointing in the wrong direction.

3. **Quorum cost model**: 3 classifiers × N iters × $/classification. Is it cheaper than ONE wrong suppression decision? For I-3 suppress mode the downside is a skipped pivot; the value of a correct pivot skip is the topological-pivot token cost it would have incurred. Rough estimate: pivot fires ~5-10× per project; quorum would fire ~30-60× (6× more often due to being on every iteration). If quorum costs are 10-30% of a pivot's cost, quorum is net positive ONLY IF >3 of 10 pivots are genuinely mis-targeted. Mining estimate: tail_gen pivots have mean Δ −0.7 → 20% regress rate. That's not obviously >30% mis-targeted. Quorum might not pay back.

4. **Super-class definition stability**: does the binary blocker/breaker split hold under cross-LLM test? We have NOT directly mined for super-class agreement; we only mined the fine-grained 15-class agreement. **Candidate experiment: re-run `mine_cross_provider_classifier_agreement.py` with the two-class collapse and see if agreement jumps from 48% to 90%+.** If yes, Path A has empirical grounding. If not, Path A is also disputed.

## 5. Recommended immediate actions (if this seam resolves to Path A + C)

1. Extend `weakest_link_classifier.py`: add `SUPER_CLASS_MAP: dict[str, str]` mapping each fine class to one of `{structural_blocker, ceiling_breaker, other}`. Add helper `classify_super_class(text)`.
2. Add `stagnation_trigger_mode: "new_super_class"` option to Task 12. Default stays `"score"`.
3. Do NOT promote I-3 to suppress mode. Document in seam why.
4. **Pre-registered validation experiment**: `scripts/public/mine_cross_provider_classifier_agreement_super_class.py` — re-run the 100-record sample with 2-class collapse. If three-way agreement ≥ 90%, super-class routing is green. If 70-90%, treat as observability-only. If <70%, Path A is also broken and we fall to pure Path C.

## 6. What this seam does NOT change

- The existing cross-LLM warning on `ceilingbreaker`/`both` catalog modes stays.
- The `hardkill` catalog injection stays (Part 1 is regex-sourced, not LLM-classified).
- Existing mining output (GP-149 findings) stays as PROVISIONAL pending super-class re-mining.
- GP-146 gate-stack self-validation, G1 full implementation, GP-145b run-3 retry — all UNAFFECTED and should proceed in parallel.

## 7. Decision gate — operator sign-off

Before implementing Section 5, operator should confirm:
- [x] Read the audit table in §1 and agree that only Task 12 and I-3 are at risk.
- [x] Agree that Path A + C is the right composition (vs Gemini's preference for A + B).
- [x] Authorize the super-class-collapse experiment in §5.4 as the empirical gate.
- [x] Run the experiment and record the verdict.

## 8. Experiment result — 2026-04-24

Ran `scripts/public/mine_cross_provider_classifier_agreement_super_class.py` against the existing 100-record 3-provider dataset (no new API calls; purely offline collapse + recomputation).

| Metric | Fine-grained (15-class) | Super-class (3-class) |
|---|---:|---:|
| 3-way agreement rate | 48.0% | **75.0%** |
| κ(openai, claude) | 0.56 | 0.46 |
| κ(openai, gemini) | 0.58 | 0.48 |
| κ(claude, gemini) | 0.57 | **0.64** |

Per-super-class stability:
- `ceiling_breaker`: 72.2% (65 of 90) — solid
- `structural_blocker`: 28.6% (10 of 35) — **LLMs disagree even on fatal-vs-recoverable**
- `other`: 0.0% (1 of 1, degenerate)

**Verdict band:** 70-90% → `PATH_C_ONLY`.

**Decision:**
- Do NOT implement live super-class routing (`SUPER_CLASS_MAP` live branch conditions).
- Keep runtime regex classifier **observability-only**.
- Task 12 `stagnation_trigger_mode="new_class"` stays live (regex deterministic within-session; cross-LLM noise doesn't apply).
- I-3 `pivot_ineffective_class_mode` stays `"observe"` indefinitely.
- Anti-pattern catalog stays split: `hardkill` only is safe; `ceilingbreaker`/`both` still emits warning.

**Surprising sub-finding**: the `structural_blocker` super-class is the LESS stable of the two (28.6% vs 72.2%). Interpretation: LLMs agree on "this is a ceiling-breaker-shaped critique" but disagree on whether a critique is genuinely fatal or merely residual. This is a downstream concern worth a follow-up seam if we ever depend on the structural-blocker vs ceiling-breaker distinction for routing (we don't today — `hardkill` catalog is regex-sourced from Part 1 of `docs/concepts/anti_pattern_catalog.md`, which is deterministic).

**Artifact:** `analytics/public/queries/classification/cross_provider_classifier_agreement_super_class_2026-04-24.json`

**Seam status:** CLOSED. Path C adopted. No code changes to classifier live routing. GP-149 rubric defaults unchanged.
