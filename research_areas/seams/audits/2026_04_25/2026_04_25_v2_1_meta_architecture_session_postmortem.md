# 2026-04-25 v2.1 Meta-Architecture Session Postmortem

> **Seam metadata** · `seam_id:` 2026_04_25_v2_1_meta_architecture_session_postmortem · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

A long session that started as a single ANALOGY audit and ended as the v2.1 meta-architecture. This document is the operator-facing record of what happened, what shipped, and what the runs actually showed. It is meant to be read in one sitting; the architectural-map and arch-map updates carry the same content in reference form.

## What started the session

The day opened with three parallel intentions: run gp165 to audit the L1 ANALOGY primitive before live activation, run gp163d to test the v2.0 weighted-χ² fit primitive on real heteroscedastic astrophysics data, and prepare the gp-164 architecture seam for closure. The gp163d substrate was the unified disk-cluster-binary acceleration dataset built earlier — 3,180 SPARC galaxy rows, 84 CLASH cluster rows, 12 Chae wide-binary bins — with per-row σ propagated from the actual instrument errors. The Newton-step claim was straightforward: pre-commit a constant on visible class A (disks), run the prediction on withheld classes B (clusters) and C (binaries) without re-fitting, and let the farther-tail gate adjudicate whether universality holds.

The session did not stay with that plan.

## The first six hours

The first run of gp163d under v2.0 failed for reasons that had nothing to do with the science. The mutator (o3) recovered the McGaugh interpolation function `(x + sqrt(x² + 4·c·x))/2` cleanly and fitted c ≈ 9×10⁻¹¹ — within the literature a₀ range — but the iter scored zero. The thesis prose was empty. The mutator had spent its entire token budget bouncing between two contradictory contracts: the R1 stdlib-only rule that forbade `from features import …`, and the apparatus rule against module-level `I_model` calls. Inlining the data to satisfy R1 looked indistinguishable from import-time evaluation, which triggered the second rule. The mutator never wrote a thesis.

The fit primitive was working. The mutator was working. The judge was working. The contracts disagreed.

Allowing `from features import …` whenever the project directory contains a `features.py` closed the collision. The R1 rule was originally designed against apparatus-import bypass, not against project-local substrate adapters; the fix recognized the difference. With the contract collision gone, gp163d's iter-1 produced a clean Hypothesis-U pre-commit and a clean fit. The score moved off zero.

The next failure was the framer. Under cage_meta.class="nd_features" the substrate had `enable_fit_primitive=False` (correctly, since the 1D solver does not apply) and `enable_fit_primitive_features=True`. The framer's scope check was gated on the 1D flag alone; every N-D substrate that set `enable_framer=True` saw the framer silently disable with reason `fit_primitive_disabled`. The fix was a one-line OR: accept either flag.

The third failure was at the fit primitive itself. With three free parameters (c0, k_r, k_m) and only Class A visible, scipy moved slack into k_m — a parameter that the data could not constrain because Class A's mass_log10 spans only ±0.5 around 10.5 — and reached -1,205,170. The fit's pathology detector flagged this correctly. The detector then did nothing else. The catastrophic value propagated into `MODEL_PARAMS`, the gate harness ran the form on cluster data with mass_log10 ≈ 14, computed `10^(-1.2M × 3.5)`, underflowed to zero, and reported farther-tail MRE of 143. The detector caught the symptom; enforcement was missing.

Pathology enforcement now replaces extreme-flagged parameters with the midpoint of their declared init-range before substitution. The form remains evaluable. The mutator's briefing surfaces both the original fitted values and the substituted ones, with a structural note: *your form has unconstrainable parameters given visible-class data; restructure so each free parameter is bounded by the visible classes alone.*

## The harness defect that wasn't a harness defect

A subtler failure lived in the score-cap path. When the mutator's own falsification suite ran a discriminator assertion that failed on the fitted form — for instance, `assert ratio_S > 10.0` on a form whose fitted k_r = 0.061 produced only 1.15× variation — the truncated stderr did not always contain a parseable Python exception name. The classifier returned `fail_other`, the apparatus labeled it "harness defect," and the score capped at 50 as a tooling failure. The judge dutifully wrote *"the test suite did not run to completion; cannot score Newton step,"* even though what had actually happened was a real, scientifically meaningful self-falsification: the mutator's pre-commit was over-aspirational, the form did not deliver the asserted variation, and the discriminator fired correctly.

The fallback now matches `AssertionError` substrings and bare `assert` traceback frames, returning `fail_assert` in those cases. The judge sees "the thesis was disproven by its own discriminator" and scores accordingly. A real falsification is now a finding, not a tooling failure.

## What the briefing was missing

By the third iter, the mutator was looping. Same form. Same constants. Same farther-tail failure. Aggregate MRE 0.85, threshold 0.5, score zero. The judge's notes pointed at the universality assumption, but the mutator had no operational signal about WHICH class drove the failure. The fit primitive's output exposed only aggregate stats. The harness output had per-class MRE breakdown, but it printed to stdout and disappeared.

A new briefing provider, `PerClassBreakdownProvider`, reads `workspace/gate_harness_result.json` (now persisted by the harness on every run) and surfaces the decomposition: holdout MRE 0.058 on Class A, farther-tail MRE 0.92 on Class B, 0.43 on Class C. When farther-tail fails on out-of-class systems while holdout passes on the visible class, the provider also surfaces an explicit U-vs-S diagnosis: *Class-B MRE is 16× larger than visible-class MRE. Hypothesis U is rejected by the data. Pivot to Hypothesis S OR commit to a publishable null.*

On the next iter the mutator dropped Hypothesis U and proposed `c = c₀ · 10^(0.30 · radius_log10)`. A scale-dependent form. The score moved to 50 — exactly the harness-defect cap floor, indicating the structural pre-commit was earning credit even though the discriminator path was still mis-classified.

## The contamination problem

Iter-1 of the same chain hard-failed on `global_named_import_check`. The mutator had written `MOND-like law` and `baryonic surface-density` in the thesis prose. The denylist gate fired correctly: those terms were on the list. The contamination defense had detected canonical theory leaking from training data.

The right response to this was not obvious. The denylist was set up to enforce a cold-LLM-null framing: *can the apparatus produce a finding without the LLM reciting its training?* But gp163d's actual scientific role is not blind discovery. The contribution is the unified disk-cluster-binary analysis under principled weighting — a combination not done in published literature. The mutator naming MOND or baryonic does not undermine that contribution; those are simply the field's vocabulary for what the data describes.

The denylist was enforcing the wrong epistemic stance for the substrate. Different substrates need different stances. A cold-LLM-null test on OEIS dark sequences (gp077) needs a strict denylist; the test there IS whether the apparatus can find structure blind. A synthesis-from-known substrate like gp163d needs only a recital-prevention denylist: terms that name the *answer* (specific paper authors, specific catalog identifiers, the canonical constant value) but not terms that name the *question* (gravitational acceleration, system-size dependence, universality vs scale-dependence, the field's basic vocabulary).

gp163d's denylist now enforces only recital prevention. The Compress leg's Newton-step claim still has to survive farther-tail; the denylist no longer also requires the mutator to invent a vocabulary the field already has.

A general infrastructure piece shipped alongside this. Pre-submission denylist scanning now runs as an R1 retry: when the candidate's prose contains a denylist term, the mutator gets a free retry to rewrite without it, instead of having the iter zeroed post-judge with no chance to recover. Substrates that genuinely need cold-LLM-null discipline (gp077, gp145) keep the same denylist content; what changed is that contamination is now a redo, not an iteration burned.

## The audit's own ceiling

While the gp163d work was running, gp165 — the architecture audit that started the session — kept hitting 100. Same-family gemini-on-gemini in the first runs, then once o3-on-gpt-4.1 with broadened scope, still 100.

The structural cause of the ceiling was visible from the rubric. Audit-class substrates (cage_meta.class="audit") have all numerical-validation gates disabled by design: no holdout, no fit, no uniqueness gap, no parsimony violation, no cage authoritative dispatch. The score is determined entirely by the LLM judge grading the thesis prose against the rubric. With nothing to fail, any rubric-aligned prose ceilings out.

The diagnostic mechanism the rubric was supposed to provide — "concrete bypass exploit demonstrated against the actual codebase" — could be satisfied by submitting Python that built `MockFramerND` and `MockAnalogy` classes in-script and asserted behavior against the Mocks. The exploit was technically runnable. It demonstrated nothing about the real codebase. The judge, working from the rubric prose, awarded full points for the bypass dimension because the rubric did not specify "real imports only."

A new gate, `global_audit_mock_bypass`, scans the latest Python submission for `unittest.mock` imports, `MagicMock` references, and class definitions matching `^class\s+Mock[A-Z]\w*`. When the substrate is audit-class and any of those patterns appears, the gate caps the score at 50 with a structural note: *to unlock full credit, rewrite the exploit to import the actual components and run the bypass against their real signatures.* The gate skips entirely on non-audit substrates, so the existing science-substrate path is unchanged.

The gp165 audit's iter-1 used Mocks and would now cap at 50. The current iter-3 uses real imports of `src.ztare.fit.analogy` and passes the gate cleanly. The substrate's score will reflect what the apparatus actually demonstrated against the actual codebase, not what the LLM prose claimed.

## What v2.1 is, and where the score comes from

v2.1 is the apparatus that emerged from this session. It is the v2.0 stack (REFRAME + ANALOGY + weighted-χ²) plus seven discipline mechanisms that close the silent-failure modes the v2.0 stack revealed under live data:

The noise-profile diagnostic measures the data's actual error structure (heteroscedasticity, normality, autocorrelation, errors-in-X) and routes the solver before iter one begins. The same four tests run again per iteration on the fitted model's residuals to distinguish a clean fit from a misspecified form. Pathology enforcement refuses to substitute catastrophic fitted parameters into the harness. The self-falsification reclassifier returns the right verdict when the mutator's own discriminator fires. The contamination-defense briefing surfaces denylist hits to the mutator with line numbers and explicit re-derivation guidance, closing a feedback loop that was previously silent. The R1 contract-collision fix admits substrate-local imports while keeping arbitrary third-party imports blocked. The framer N-D scope fix lets REFRAME run on the path it was always meant to run on.

Two new gates close the audit-class friction gap (mock-vs-real-imports) and the contamination-recovery gap (pre-submission denylist scan as R1 retry). Two new briefing providers (per-class breakdown, contamination defense) close feedback loops the mutator could not act on without explicit signal.

The score gp163d will produce under v2.1 depends on what the form actually is. A pre-commit to Hypothesis U with the McGaugh interpolation form will score the Newton-Step Pre-commit dimension cleanly, run the farther-tail gate, fail it (universality is empirically rejected on this combined dataset under proper weighting), and either land in the publishable-null band (70 if interpreted in U-vs-S terms) or the form-too-narrow band (40 if the mutator tries to defend U despite the failure). A pivot to Hypothesis S with a properly bounded c(features) form might land higher if it passes farther-tail. The apparatus is not designed to produce 100; it is designed to produce the score the form earns, and the band 60-80 is the calibration target for a substrate whose canonical answer is in the mutator's training data.

The score gp165 will produce under v2.1 caps at 50 unless the bypass exploit imports the real components. With real imports, the audit can reach the high band, but only by demonstrating a vulnerability against the actual codebase. The Mocks-pass-prose ceiling is closed.

## What this session did not produce

It did not produce a publishable physics finding. The U-failure on combined disk-cluster-binary data under weighted χ² reproduces what the field already knows piece by piece: MOND fits SPARC disks, MOND has trouble with clusters, Chae's wide-binary results are recent and contested. The unified analysis under principled weighting is methodologically novel; the verdict is not.

It did not produce a closed gp165 audit. The audit was broadened mid-session from "ANALOGY only" to "v2.1 meta-architecture" because each fix added a component the audit needed to cover, and the substrate is now under fresh review against the broader scope.

It did produce a v2.1 apparatus that knows what test it is running. That is the contribution worth recording. The next discovery substrate runs against this apparatus, not against the v2.0 one.

## Files touched this session

Apparatus changes:

- `src/ztare/fit/fit_primitive_features.py` — weighted χ² objective, χ² + K·log(N) BIC switch, σ_list extraction with σ=1 fallback
- `src/ztare/diagnostics/__init__.py` and `src/ztare/diagnostics/noise_profile.py` — new module with four detectors and auto-routing
- `src/ztare/framer/active_framer.py` — σ-aware bypass on heteroscedasticity guard, N-D scope check fix
- `src/ztare/framer/framer_nd.py` — N-D framer adapter (already existed; verified clean)
- `src/ztare/validator/autoresearch_loop.py` — fit dispatch wMDL flags, pre-flight noise-profile hook, per-iter noise-profile hook, pathology enforcement, R1 contract-collision allowlist, pre-submission denylist scan as R1 retry, framer N-D dispatch fix
- `src/ztare/validator/utilities/harness_failure_mode.py` — AssertionError fallback in classify_harness_failure
- `src/ztare/gates/global_gates.py` — extrapolation-gap audit-class bypass, audit-mock-bypass gate
- `src/ztare/orchestrator/briefing_providers/per_class_breakdown.py` — new briefing provider (per-class MRE + U-vs-S diagnosis)
- `src/ztare/orchestrator/briefing_providers/contamination_defense.py` — new briefing provider (denylist hit surfacing)
- `src/ztare/orchestrator/briefing_providers/noise_profile_brief.py` — new briefing provider (noise-profile verdict)
- `src/ztare/orchestrator/briefing_providers/fit_telemetry.py` — pathology-substituted-params surface

Substrate changes:

- `projects/gp163d_unified_accel/raw/unified_rar_with_sigma.csv` — σ-enriched dataset (3,276 rows, 10 cols)
- `projects/gp163d_unified_accel/features.py` — exposes per-row sigma + sigma_source
- `projects/gp163d_unified_accel/gate_harness.py` — persists full per-class breakdown to workspace JSON
- `projects/gp163d_unified_accel/.denylist` — relaxed to recital-prevention only
- `rubrics/gp163d_unified_accel.json` — fit_weighted_residuals=true, fit_sigma_key="sigma", enable_noise_profile=true

Audit substrate changes:

- `projects/gp165_analogy_architecture_review/project_charter.md` — rewritten as cohesive v2.1 charter
- `projects/gp165_analogy_architecture_review/evidence.txt` — v2.1 component list + ANALOGY-degeneracy observation
- `projects/gp165_analogy_architecture_review/raw/` — extended from 5 to 16 files covering all v2.1 components
- `rubrics/gp165_analogy_architecture_review.json` — v2.1 description, audit-class cage_meta, farther-tail-region opt-out

Documentation:

- `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md` — GP-166 section
- `docs/concepts/architecture.md` — §15 "The v2.1 Meta-Architecture: Measuring the Data's Epistemology"
- `research_areas/private/philosophy/cognitive_gym.md` — Part 6 "Calibration vs Discovery, and What 'Science' Means Here"
- `research_areas/private/philosophy/three_legs_of_ztare.md` — "Measuring Before Killing" addendum
- `research_areas/private/seams/audits/2026_04_25/2026_04_25_v2_1_meta_architecture_session_postmortem.md` — this document

## Final note on framing

The framing question that took the longest to settle was the one the operator pushed back on twice: is gp163d real science? The answer, which I got wrong twice before getting right, is calibration. gp163d is a calibration substrate, not a discovery substrate, and conflating the two produces both false confidence ("we did science!" when the LLM recited from training) and false despair ("the LLM had priors, so nothing here is real"). What the apparatus did on gp163d is the calibration the apparatus needed before it can be trusted on the next discovery substrate. The 60-80 band is the target. The 100 ceiling on gp165 was the apparatus failing silently. The 0 floor with the contamination defense firing was the apparatus over-disciplining a synthesis substrate. The fixes shipped this session are the apparatus learning the difference.
