# GP-061 Component B — Generalization Target Spec

## Status

Active — **v4 (2026-04-15 late, protocol switch merged). v3 body retained below for diff-legibility; v4 amendments live in §v4 Amendment.** Open questions and content-review fixes from v3 still stand except where v4 explicitly supersedes them.

Spec'd 2026-04-15 after the sandbox_09 pause (see `GP-023_sandbox_09_pre_registration.md` — v2 RE-SEALED 2026-04-15, §A1 amendment).

---

## v4 Amendment — Nesting-collapse + R3b/R4 protocol switch (2026-04-15 late)

### What changed and why

Sandbox_09 v2 closed Outcome D (apparatus — harvest under-convergence) because iteration 1 of the live-mutator harvest fit-collapsed to the sealed GT via a nested-generalization wrapper, leaving the failed-family corpus empty. The sandbox_10 nesting-collapse audit (`GP-023_sandbox_10_nesting_collapse_audit.md`) then enumerated six wrapper classes W1–W6 under `math_power_only` and showed that **every** wrapper collapses to Kepler vis-viva at null extra-parameter values. This is not a sandbox-specific misfortune; it is a structural property of the interaction between (a) grids on which the sealed GT is identifiable and (b) grammar closures that contain the sealed GT as a limit point.

Consequence: the GP-061 spec v3 mode (c) live-mutator harvest protocol cannot execute on either sandbox_09 or sandbox_10 as specified. Any grid on which `fit_contract` discriminates the sealed family lets a nested wrapper fit-collapse to it; §A1.5 passing and harvest under-convergence are the same property.

### v4 protocol replacement

The v3 mode (c) protocol is **retired** for sandbox_10 and all future GP-061 cold tests over grammars known to exhibit nesting closures over their sealed GT. Replacement protocols:

- **R3b — curated-harvest cold test.** The failed-family corpus is a pre-registered, hand-curated set of grammar-valid wrong candidates, frozen at pre-reg seal time. Component B is cold-run against this curated corpus. The decisive claim is narrower than v3 mode (c): instead of "the mutator produces a harvest from which Component B surfaces the expected void," R3b tests "given a curated harvest of deliberately wrong candidates in a new grammar, does Component B's feature vocabulary fire correctly without Planck-residue leakage?" Curated-harvest discipline is now the decisive operator move and must be pre-registered per §6 of each target's pre-reg.

- **R4 — retrospective consistency check.** Component B is cold-run against the closed sandbox_07 and sandbox_08 Planck harvests (under their pinned `workspace/structural_memory.json` files) and must surface `fn:exp|arg0|has_op:Div` with no spurious voids. R4 is the control for "did we redesign the detector in a way that broke its original behavior?" A passing R4 is the retrospective leg of the new two-run promotion gate.

### v4 two-run promotion gate (supersedes v3 §Scope "Promotion gate (hard)")

Component B is NOT live-wired onto any non-Planck project until **both** of the following hold:

1. **Sandbox_10 R3b passes Outcome A or B** (prospective cross-grammar check under `math_power_only`). **STATUS: PASS (Outcome A, 2026-04-15).** See `GP-023_sandbox_10_post_run_audit.md`. Detector surfaced `fn:sqrt|arg0|has_op:Sub` (decisive) plus pre-registered ancillaries `{Div, USub, Call}` at the same key, no Planck residue, all voids grep-verifiable against `curated_harvest.json`.

2. **R4 retrospective consistency check passes on sandbox_07 and sandbox_08** closed harvests. **STATUS: PASS (both, 2026-04-15).** See `GP-061_R4_retrospective_audit.md`. Detector fired on both corpora with family counts (12 and 8) and void counts (7 and 7) matching the spec body's recorded description at lines 351–352, with the `Pow` filled/void polarity at `fn:EMLCALL|arg0` matching exactly (filled on 07, void on 08). All 14 surfaced voids manually grep-verified against the family labels. Detector behavior is stable against the historical written record under the current code version.

**Correction to earlier v4 amendment text.** An earlier draft of this amendment stated the R4 pass criterion as "must surface `fn:exp|arg0|has_op:Div`." That was wrong on two counts: (a) the detector surfaces `fn:EMLCALL|*` after `_normalize_family_label` rewrites `N(...)` to `EMLCALL(...)`, and (b) `has_op:Div` is a **filled** slot in both sandboxes (every family has `X0/X1` inside the eml first argument), not a void. The correct pass criterion, matching the historical description in §Cross-references lines 351–352, is: fired=True on both sandboxes, family_count ∈ {12, 8}, void_count 7 per sandbox, and `fn:EMLCALL|arg0|has_op:Pow` filled on sandbox_07 (because sandbox_07 uses `X0**P1` inside eml arg0) and void on sandbox_08 (because sandbox_08 uses plain `X0/X1` inside eml arg0). R4 passes under this corrected criterion.

Sandbox_09 v2 **no longer contributes** to the promotion gate under v4. Its closure is recorded as Outcome D (apparatus) in the experiment ledger and a separate narrow capability datapoint (F-CAP-FLASH-RC-01) covers the flash-recovered-RC observation. Sandbox_09 was the original second leg of the gate under v3 but the nesting-collapse pathology rules out its mode (c) path.

### Why R3b is weaker than v3 mode (c), and why this is the honest call

R3b is a strictly weaker test than v3 mode (c). It does NOT adjudicate whether a live mutator would produce the expected voids under real autoresearch conditions. It only adjudicates whether Component B's detector vocabulary generalizes across grammar boundaries without silent template leakage. The failure mode it does rule out — "Component B's feature vocabulary is secretly specific to `exp`-grammar harvests and either fires noise on `sqrt`-grammar harvests or fails to engage the density guard at all" — is the generalization failure the two-run promotion gate was originally designed to catch.

The stronger mode (c) claim is not ruled out; it is **not testable** on any sandbox where the identifiability/nesting interaction locks harvest convergence. This is a permanent architectural constraint of the curated-sandbox approach, not a sandbox_09/10 accident. Future GP-061 targets that can clear both identifiability AND generate non-trivial failed-family harvests require a grammar axis whose nesting closure does NOT contain the sealed GT as a fit-collapse limit — an open research question tracked as GP-069 (champion nesting-audit gate) and as a future grammar-axis design seam.

### What v4 does NOT authorize

- Live wiring of Component B until R4 passes. Solo R3b is insufficient.
- Rewriting v3 §Implementation Sketch mode (a)/(b)/(c) subsections — they are retained for diff-legibility but are not executable under v4 for targets exhibiting nesting closures.
- Re-running sandbox_09 v2 under any protocol. Closed.

### v4 action items

- [x] sandbox_10 R3b executed and verdicted (Outcome A)
- [ ] R4 retrospective against sandbox_07 closed harvest
- [ ] R4 retrospective against sandbox_08 closed harvest
- [ ] On dual R4 pass: promote Component B to `confirmed` and enable live wiring on non-Planck projects under the Component-B live-emission discipline seam
- [ ] GP-069 nesting-audit seam (task #47) — generalizes the sandbox_09/10 lesson into a pre-seal gate for future targets

### v4 cross-references

- `GP-023_sandbox_09_post_run_audit.md` — closure triggering the protocol switch
- `GP-023_sandbox_10_nesting_collapse_audit.md` — structural audit of mode (c) infeasibility
- `GP-023_sandbox_10_pre_registration.md` — v1 sealed, R3b protocol, §v4-aware §2 rationale
- `GP-023_sandbox_10_post_run_audit.md` — Outcome A R3b pass

---

**2026-04-15 late — sandbox_09 v2 CLOSED Outcome D (apparatus — harvest under-convergence).** Iter 1 scored 100 via a nested-generalization collapse: mutator (gemini-2.5-flash) proposed 5-param `R`-dependent wrapper, fitter drove extra exponents to null, fitted form equals sealed RC to 4 sig figs, no failed-family harvest accumulated. §7 Outcome A unreachable because its second conjunct (cold-run void surfacing) requires a non-empty harvest. §5 harvest-stress trajectory prescribes D. Unrelated capability observation worth recording separately: flash recovered first-order RC from a blinded transient-only grid (`t_max < τ_min`, plateau invisible) in a single iteration. Design-level finding: **grid identifiability and failed-family harvest are in tension** — any grid on which `fit_contract` discriminates the sealed 3-param RC family lets a nested wrapper fit-collapse to it. §A1.5 passing and harvest under-convergence are the same property. Component B cross-grammar claim returns to **open**. Two-run promotion gate unmet. Sandbox_10 (Kepler) must pass an explicit **nesting-collapse audit** (enumerate 5-param wrappers the mutator might propose under `math_power_only`; check whether any collapse to Kepler at null extra-param values; if yes, re-amend before sealing) before live run. See `research_areas/private/seams/GP-023_sandbox_09_post_run_audit.md`.

Blocks: any live wiring of `negative_space_extractor` onto a non-Planck project.
Related seams: `GP-061_constraint_accumulation_as_output_seam.md` (Component B live-emission discipline).

## Scope

Covers:

- selection of a domain target whose generator is physically and structurally disjoint from the Planck `I(phi, psi)` family used by sandbox_06/07/08/gp045
- a three-mode cold-test protocol (plumbing + live-mutator harvest) that gates whether Component B's feature vocabulary (`fn:{fname}|arg{i}|has_op:{OP}`) is domain-agnostic
- a pre-test identifiability discipline for the chosen generator
- detector-fingerprint pinning preconditions

Does not cover:

- live wiring of Component B into any production autoresearch run
- changes to `autoresearch_loop.py`, `structural_constraint_extractor.py`, `negative_space_extractor.py`, or `derived_constraints.py` (the detector under test is pinned by fingerprint)
- re-sealing or unpausing `GP-023_planck_sandbox_09`
- Component A or GP-062 re-qualification — they are covered under their own seams and are only touched here for co-firing discipline

- **Primary target (sandbox_09):** RC step-response generator `V(t, R) = V_inf * (1 - math.exp(-t / (R*C))) + V_offset`, with `t, R` as observables and `V_inf, C, V_offset` as identifiable parameters. Sandbox_09 slot is reused (old Planck pre-reg retired as `GP-023_planck_sandbox_09_pre_registration_RETIRED_2026-04-15.md`; live pre-reg is `GP-023_sandbox_09_pre_registration.md` v2).
- **Queued stronger target (sandbox_10, pre-committed before sandbox_09 runs):** Kepler distance-velocity `v(r, a) = math.sqrt(GM * (2/r - 1/a))`. Sandbox_10 uses a different primitive (`math.sqrt`, no `exp` anywhere), so Component B's vocabulary must fire correctly on a primitive family it has never touched.
- **Promotion gate (hard):** Component B is not live-wired onto any non-Planck project until **both** sandbox_09 RC and sandbox_10 Kepler pass their mode (c) verdicts. One pass is not sufficient. Running them sequentially (RC first to de-risk the protocol, Kepler second to close the disjointness claim) trades roughly 5 days of engineering for a much stronger generalization claim than either alone.
- **Cold-test protocol:** three modes per target — (a) plumbing check on a failed corpus, (b) plumbing check on a healthy corpus, (c) decisive live-mutator harvest. (a)+(b) pass is a precondition for running (c); only (c) passing contributes to the promotion gate. The expected-void analysis for mode (c) is sealed in the pre-reg (not this spec) to prevent the operator from anchoring on the void label before seeing the output.
- **Mutator backend:** same as sandbox_07/08 (apples-to-apples). Isolates the domain axis from the mutator-implementation axis.
- **Authorship of corpora:** Claude Opus 4.6 (this spec's author) is contaminated and cannot draft. A fresh LLM agent with read access only to this spec, the pre-reg public half, and Component B's source — and zero exposure to Planck sandbox_07/08 void sets, structural_memory.json, or seam files — is acceptable. The operator audits the agent's tool-call log to confirm no `planck` / `sandbox_07` / `sandbox_08` grep activity. Operator hand-drafting is the slower fallback.
- **Fingerprint precondition:** the detector under test is pinned by git commit hash + file sha256 before any cold-test mode runs.

## Problem

Component B (`negative_space_extractor`, GP-061.B) has been cold-tested on three projects to date: `gp023_planck_sandbox_07`, `gp023_planck_sandbox_08`, `gp045_cold_residual_01`. All three are Planck-family — `gp045_cold_residual_01`'s own charter describes it as a cold successor on the "frozen GP-037 / GP-042 / GP-043 substrate" and its thesis reasons about `I(phi, psi)`. The `gp045` cold test was previously mis-framed as a non-Planck generalization datapoint; it is not.

There is therefore no evidence that the detector's feature vocabulary, density guard, or dense-void logic generalize off the Planck family. Without a target whose generator is physically disjoint, sandbox_09's planned live run would promote Component B to `confirmed` after its second Planck-family datapoint — satisfying the two-run promotion gate procedurally while never having exercised the detector against structurally unfamiliar mutator output.

## Why It Matters

Component B is the first detector on the negative-space axis. If it promotes on single-domain evidence it becomes an unfalsifiable fixture: every subsequent run that fires it confirms the detector, and every run that does not is explained away as "healthy coverage." The sandbox_06 `(α, β)` identifiability incident is the cautionary analogue — a detector/check that appears to work on one family and quietly fails a degeneracy probe the family never stressed. The cheap move (a real non-Planck cold test) is the only move that keeps the two-run promotion gate honest.

The dollar value of being wrong here is also high: Component B is designed to write into the same `derived_constraints.json` channel that feeds the mutator prompt post-promotion. A confirmed-but-domain-overfit Component B would inject spurious "voids" into the prompt on every non-Planck run from then on, in exactly the place the operator is least likely to audit by default.

## Constraints

- **Physical/structural disjointness.** The chosen generator must share no identifiable primitive pattern with `I(phi, psi)` — no `phi^n * psi^m` coupling, no `1/(exp(x)-1)` denominator, no peaked-then-decaying surface shape. Variable names must differ to preempt accidental re-use of Planck feature-bags.
- **Grammar axis must be new.** The grammar slot must not be `eml_only` (already exercised by sandbox_07/08). Prefer a grammar that makes a small number of structurally-specific slots (e.g. `Div` inside `exp`'s first argument) meaningful.
- **Three parameters or fewer, all identifiable.** Inherits the sandbox_06 hardening-seam discipline. Non-identifiable GTs floor-limit the residual corpus and break the Component B cold test by construction.
- **Operator-drafted cold-test corpora.** No Claude-drafted example families in §5 of the implementation sketch. The spec author has been peeking at Planck voids for three sessions and cannot be trusted to draft blind.
- **Detector fingerprint pinned.** Cold-test execution is unauthorized until a git commit hash + file sha256 for `negative_space_extractor.py`, `structural_constraint_extractor.py`, and `derived_constraints.py` are captured and pasted into the Implementation Sketch's fingerprint block.
- **Inherits from sandbox_06/07/08 apparatus:** 9-ish gate battery shape, deterministic evidence discipline, no noise, `fit_primitive.py` grammar enforcement, harness smoke gate. New surfaces authored only where they are structurally required by the target.
- **Does not contaminate sandbox_09.** sandbox_09 remains paused under its Correction Block; this spec does not re-seal or modify it.

## Options

### Option A — RC step response

**Description.**
`V(t, R) = V_inf * (1 - math.exp(-t / (R * C))) + V_offset`. Observables `t` (time), `R` (resistance); parameters `V_inf`, `C`, `V_offset`. Grammar `math_exp_only` (not `eml_only`). Three-parameter identifiable GT. Sweeps over 5 log-spaced `R` values.

**Pros.**

- Makes `exp(arg0|has_op:Div)` the structurally-meaningful slot — a slot that is *void* in both sandbox_07 and sandbox_08's Planck corpora. If Component B's vocabulary is honest, it should discover this as a real coverage gap when the mutator proposes the wrong transient shape.
- Harness inheritance is cheap: the 9-gate Planck battery shape ports directly, re-expressed over `t, R` instead of `phi, psi`.
- Physical interpretation gives the operator a second, manual channel for sanity-checking detector output (operator can grep family labels and confirm "none of these families nest Div inside exp").
- Variable names `t, R` share no letters with `phi, psi`.
- Identifiability margin is comfortable: 3 parameters, `C` is separated from `V_inf` by cross-sweep `R` leverage (see §Constraints below).

**Cons.**

- Grammar still uses `math.exp`, the same primitive as several earlier Planck corpora. The primitive axis is therefore not *fully* disjoint — only the nesting structure and the domain are.
- The 63% rise-time gate requires a new metric in the harness library (`rise_time_63pct_relative_error_R_<value>`), not a straight port.
- Mutator may converge instantly on this target if the RC shape is too easy to guess, leaving the live-mutator harvest with too few failed families for Component B to read.

**Verdict.** Recommended as the primary target.

### Option B — Logistic / SIR sigmoid

**Description.**
`I(t, beta) = K / (1 + math.exp(-beta * (t - t0)))`. Observables `t, beta`; parameters `K, t0` (plus the sealed `beta`-scaling convention).

**Pros.**

- Stronger structural disjointness than RC: the sigmoid shape is neither peaked-and-decaying (Planck) nor monotone-approaching-asymptote (RC) — it's bounded monotone.
- Exercises `USub` and `Mult` inside `exp`'s arg0, plus outer `Div` by `(1 + ...)`.

**Cons.**

- Two of the three parameters collapse onto shift/scale of a sigmoid — identifiability is known-tight and requires denser `t` grids than RC.
- Mutator blind spots on sigmoids are less well-characterized across the existing ZTARE runs; harder to pre-state what Component B *should* surface as a void.
- Harness battery needs a "midpoint location" gate instead of a "rise time" gate — more bespoke than RC.

**Verdict.** Acceptable fallback if RC's live-mutator harvest (Option A's main risk) over-converges.

### Option C — Kepler distance-velocity (sqrt primitive)

**Description.**
`v(r, a) = math.sqrt(GM * (2/r - 1/a))`. Observables `r, a`; parameters `GM` (plus the sealed orbital convention).

**Pros.**

- Strongest disjointness: no `exp` anywhere. Exercises a primitive (`math.sqrt`) Component B has never been cold-tested against. This is the hardest test of "is the vocabulary really domain-agnostic, or just exp-agnostic?"
- Clear physical asymptotics at `r → a` (circular orbit) and `r → infinity` (escape), both usable as gates.

**Cons.**

- Requires new gate-threshold calibration; the Planck residual-threshold defaults are not portable.
- Only one free parameter (`GM`) unless the spec is expanded to include eccentricity, which adds identifiability work.
- Furthest from existing harness machinery — largest engineering surface.

**Verdict.** Acceptable as the stretch target if Option A passes and the operator wants a second disjoint datapoint before Component B is allowed on anything like the Planck family ever again.

### Option D — Black-Scholes intrinsic call value

**Description.**
`C(S, t) = max(S - K * math.exp(-r * t), 0)`. Financial domain.

**Pros.**

- Different domain entirely (financial vs physical). Cheapest proof of "not just physics."
- Exercises `max` + `exp` + subtraction — a new structural combination.

**Cons.**

- Piecewise function — the `max` kink breaks smoothness assumptions in the fit library. ZTARE's fit routines are not known to handle discontinuous gradients gracefully; this is a harness risk, not a detector risk.
- The detector question is conflated with a fit-primitive-robustness question.

**Verdict.** Rejected for the first cold test. Revisit only after Option A passes and the smoothness issue is investigated separately.

## Recommendation

**Sequential two-target adoption: Option A (RC) as sandbox_09, Option C (Kepler) as sandbox_10, both pre-committed before either runs.**

The honest version of the single-target recommendation: RC alone is a ~70% test of the generalization claim. Component B's vocabulary has been exercised on `exp`-primitive corpora across sandbox_07, sandbox_08, and gp045, and RC keeps the primitive the same while varying the domain, variables, and nesting structure. RC passing would refute "Component B overfits to Planck shapes" but would not refute "Component B overfits to `exp`-grammar."

Option C (Kepler) closes that gap because it has no `exp` anywhere. If Component B also fires correctly on Kepler, the generalization claim jumps from ~70% to ~95% because the `fn:{fname}|arg{i}|has_op:{OP}` vocabulary has demonstrably worked on `math.exp`, `math.eml`, and `math.sqrt` primitives — three families with no shared non-trivial operator.

**Why sequential rather than Kepler-first:** Kepler's fit-routine port is genuinely uncharted (sqrt's domain constraint `2/r - 1/a ≥ 0` requires guard clauses the existing routines don't have; gate thresholds have never been calibrated for monotone-decreasing-unbounded surfaces). If Kepler runs first and fails, we cannot distinguish "Component B's vocabulary is domain-specific" from "our sqrt fit-routine port has a bug." Running RC first de-risks the protocol (proves the three-mode cold-test discipline works) at the cost of a few engineering days, then Kepler tests the hardest claim against a protocol we trust.

**Why not RC alone:** the two-run promotion gate for Component B has been the standing discipline since GP-061 was seamed. Promoting it after one non-Planck pass on the same primitive would violate the discipline's spirit even if it satisfies the letter. The pre-commitment to run Kepler before any live wiring makes the discipline real.

**Single structural slot framing for RC:** Option A makes a single, crisp structural slot the discriminator for mode (c) — but this spec deliberately does not name that slot in a section the operator reads before sealing the pre-reg. Naming it here would anchor mode (c) verdict interpretation. The expected-void analysis for each target is written into the target's sealed pre-reg, not into this spec.

## Implementation Sketch

### Generator

```
V(t, R) = V_inf * (1 - math.exp(-t / (R * C))) + V_offset
```

- `t` visible grid: `{0.0, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8}` (10 points)
- `R` sweeps: `{100, 316, 1000, 3160, 10000}` (5 values, log-spaced over 100× range). Five sweeps (not three) ensure at least two have their 63% rise point inside the visible `t` grid, giving `C` cross-sweep leverage to separate from `V_inf`.
- `V_inf`, `C`, `V_offset`: identifiable parameters (sealed GT values disclosed only in eventual pre-reg).
- `V_inf > 0`, `C > 0` by physical interpretation. `V_offset ∈ ℝ` unconstrained.

Numerical generation discipline:

- Deterministic, no noise, no `numpy` random seed needed.
- IEEE double throughout.
- Evidence files formatted to mirror sandbox_08's float-column convention (inheritance, not re-derivation).

### Evidence surfaces

- `evidence.txt`: 10 × 5 = 50 visible points.
- `evidence_holdout.txt`: interior `t ∈ {0.025, 0.3, 2.4}` × all 5 R sweeps = 15 points.
- `evidence_farther_tail.txt`: `t ∈ {25.6, 51.2}` × all 5 R sweeps = 10 points.
- All three surfaces computed from the sealed GT and frozen byte-for-byte before any run.

### Grammar contract

`fit_expression_grammar = "math_exp_only"` (new axis):

- `fit_declaration` expression: allow `math.exp`, `math.log`, `math.sqrt`, `math.e`, `math.pi`. Forbid any non-`math` direct call. **`eml` explicitly forbidden.**
- `I_model` body: `math.*` only via `validate_python_model_grammar()`, with `eml` removed from the allowed direct-call set.

### Expected Component B void signature

Three cold-test modes. Modes (a) and (b) are plumbing; mode (c) is decisive. Authorship constraint per §Decision: fresh-agent or operator drafting only.

**(a) Plumbing — failed corpus.** Fresh-agent-drafted or operator-drafted corpus of ≥5 families, all grammar-valid under the target's grammar, all with `latest_visible_max_abs_residual ≥ 0.15`. The pre-reg (sealed per-target) specifies exactly one structural slot the corpus must systematically avoid. The expected primary void on mode (a) is the named slot. Any other voids surfaced are logged but do not count toward the verdict.

**(b) Plumbing — healthy corpus.** Same shape, ≥5 families, all grammar-valid, all with residuals ≥ 0.15, all filling the named slot. Expected: the named slot is NOT in the dense-void output.

**(c) Decisive — live-mutator harvest.**

1. Scaffold the target project (charter, evidence, harness, seed, grammar) with Component B **disabled** at harvest time. The disable path is a pre-cold-test code change: add a `--disable-negative-space-extractor` flag to `autoresearch_loop.py`'s post-eval hook that short-circuits the `run_negative_space_extractor` call and skips the provisional write. This flag must exist and ship to the pinned commit before mode (c) runs; its addition is logged in the fingerprint block below and requires a fingerprint re-capture.
2. Run the standard autoresearch loop for a **15-iteration budget** (matching sandbox_08 — not 10; the RC target is textbook-easy and mutators may converge fast).
3. **Harvest-stress rule (pre-committed):** if at iteration 15 the harvest contains fewer than 5 failed families (`latest_diagnostic_classification == "structural_misfit"` with residual ≥ 0.15), tighten every gate threshold by 3× and **replay** the harvest from the same seed (not extend). Adding iterations just gives the mutator more room to converge; tightening gates forces failure diversity. Maximum two replays; if the third replay also under-harvests, mode (c) is declared unrunnable and the target is retired in favor of the queued Kepler sandbox_10 (or, if this is already sandbox_10, Option B logistic as a fallback).
4. Run `python -m src.ztare.validator.negative_space_extractor --project <target_slug>` cold against the harvested `structural_memory.json`.
5. Verdict criterion (pre-committed in writing by the operator before the mode (c) output is viewed): the surfaced void set is operator-verifiable against the harvest's family labels. Every single dense void must correspond to an operator type the mutator truly never used inside that `(fname, arg_pos)` position. "Grep-countable reason" means: for each void `exp(arg0|has_op:Div)`, the operator runs `grep -c "exp(.*/.*)" structural_memory.json` (or equivalent family-label search) and confirms zero matches. If any void fails its grep check, the verdict is FAIL regardless of whether the pre-stated expected slot was also surfaced.
6. The expected-slot name is **not disclosed in this spec** — it lives in the per-target sealed pre-reg, opened only after the operator has committed verdict criterion (5) in writing. This prevents anchor bias on mode (c) interpretation.

**Pinned run configuration:**

- Entry point: `python -m src.ztare.validator.negative_space_extractor --project <project_slug>`
- Residual threshold: `0.15` (Component B default; overrides logged and verdict re-evaluated if used)
- Input schema: `<project>/workspace/structural_memory.json` mirroring the Planck-cold-test format (`family_label`, `latest_diagnostic_classification`, `latest_visible_max_abs_residual`)
- Family count ≥ 5 per corpus (headroom above `MIN_FAMILIES_FOR_VOID = 3`)

**Verdict table:**

| Mode (a) | Mode (b) | Plumbing verdict |
|---|---|---|
| `Div` in voids | `Div` not in voids | **PASS** — proceed to mode (c). |
| `Div` in voids | `Div` in voids | **FAIL** — density guard over-emitting; investigate `_group_by_key` + `MIN_FILLED_SLOTS_PER_KEY` on `math_exp_only` ASTs. |
| `Div` not in voids | `Div` not in voids | **FAIL** — under-sensitive; investigate `extract_generalized_feature_matrix` on `math.exp` call nodes. |
| `Div` not in voids | `Div` in voids | **FAIL** — inverted. Stop. |

Mode (c) verdict is separate: the surfaced void set must be operator-verifiable against the harvest's family labels. Only mode (c) passing unblocks live wiring on non-Planck projects.

**Co-firing discipline.** Component A must NOT fire on mode (a) or mode (c) corpora (if it does, the corpus is readable by the positive-space path and does not need Component B — re-draft or re-harvest). Component A firing on mode (b) is permitted. GP-062 firing is orthogonal and does not affect verdict in any mode; logged for audit.

### Identifiability check (pre-seal, operator-side)

Runs before the generator is sealed and evidence surfaces are frozen. Stronger than sandbox_06's original bootstrap — rank at a single point is insufficient (that's what sandbox_06 taught us).

1. **Multi-start fit consistency.** 10 randomized initial points over a 3-decade range around the sealed GT. All 10 must converge to the same fit within 1e-4 relative tolerance.
1b. **Pairwise loss-surface bowl check.** For each parameter pair `(V_inf, C)`, `(V_inf, V_offset)`, `(C, V_offset)`, 5×5 grid at ±20% around the GT. Each surface must have a unique minimum at the center with no gutter direction.
2. **Rank-along-trajectory.** Jacobian must have full column rank (3) at the GT *and* at each of the 10 multi-start converged points. Condition number threshold **1e4** (tightened from 1e6 — 1e6 is already suspicious at 3 parameters).
3. **Bootstrap.** 200 resamples with 1e-6 gaussian noise, relative SE < 1% on all three parameters.

Any failure revises the spec (denser grid, wider `R` range, drop `V_offset`) before sealing.

### Gate battery

**Threshold calibration procedure (replaces the v2 draft's guessed thresholds).** All numeric thresholds below are placeholders marked `<calibrated>`. Before sealing the pre-reg, the operator runs a naive seed model through the harness — specifically `V_unfit = V_inf_guess` (single-constant model at the mean of the sealed GT prediction surface) — and reads back the residuals on each of the three evidence surfaces. Each gate threshold is then set to 30-50% of the unfit-seed residual range at the corresponding scope. This turns threshold-setting into a deterministic inherited procedure and removes the "smoother surface" hand-wave from the v2 draft.

```yaml
deterministic_gates:
  - name: hidden_global_residual
    metric: max_abs_residual_on_holdout
    threshold: <calibrated>
    operator: lt
    evidence_source: evidence_holdout.txt
    scope: all_sweeps
  - name: hidden_asymptote_R_min
    metric: terminal_value_abs_error_R_100
    threshold: <calibrated>
    operator: lt
    evidence_source: evidence_holdout.txt
    scope: R_100
  - name: hidden_asymptote_R_mid
    metric: terminal_value_abs_error_R_1000
    threshold: <calibrated>
    operator: lt
    evidence_source: evidence_holdout.txt
    scope: R_1000
  - name: hidden_asymptote_R_max
    metric: terminal_value_abs_error_R_10000
    threshold: <calibrated>
    operator: lt
    evidence_source: evidence_holdout.txt
    scope: R_10000
  - name: hidden_rise_time_R_min
    metric: rise_time_63pct_relative_error_R_100
    threshold: <calibrated>
    operator: lt
    evidence_source: evidence_holdout.txt
    scope: R_100
  - name: hidden_rise_time_R_mid
    metric: rise_time_63pct_relative_error_R_1000
    threshold: <calibrated>
    operator: lt
    evidence_source: evidence_holdout.txt
    scope: R_1000
  - name: hidden_rise_time_R_max
    metric: rise_time_63pct_relative_error_R_10000
    threshold: <calibrated>
    operator: lt
    evidence_source: evidence_holdout.txt
    scope: R_10000
  - name: farther_tail_global_residual
    metric: max_abs_residual_on_farther_tail
    threshold: <calibrated>
    operator: lt
    evidence_source: evidence_farther_tail.txt
    scope: all_sweeps
  - name: rise_ordering_at_intermediate_t
    metric: rise_ordering_violation_count_at_t_1_6
    threshold: 0
    operator: eq
    evidence_source: evidence_holdout.txt
    scope: all_sweeps
```

The final gate encodes: `V(t=1.6, R=100) > V(t=1.6, R=316) > V(t=1.6, R=1000) > V(t=1.6, R=3160) > V(t=1.6, R=10000)` at the GT. **This is a structural gate, not a numerical one** — it checks qualitative ordering not residual magnitude. It is retained because it discriminates `exp(-t/(R*C))` from `exp(-t*R/C)` directly (large `R` in the wrong place reverses monotonicity). Pre-seal validation: plug the wrong form `V_inf*(1 - exp(-t*R/C)) + V_offset` through the harness with the sealed GT values for `V_inf, C, V_offset` and confirm it fails this gate but passes the asymptotic residual gate — if it passes both, the gate is not discriminating and must be re-designed. The grading protocol weights structural gates the same as numerical gates but annotates them as such in the post-run audit.

### Apparatus inheritance

Direct port from sandbox_06/07/08: `gate_harness.py` shape (adapted to new variables and gates), `harness_smoke_gate.py`, `autoresearch_loop` post-eval hook (unchanged — three producers still run in parallel, all stay provisional on first run), Component A, GP-062, Component B.

New:

- Grammar axis `math_exp_only`
- Variable set `{t, R}`
- Gate set centered on rise-time + rise-ordering instead of peak location + decay ratio
- Physical domain (electrical)

### Detector fingerprint pinning

The detector under test must be captured before any cold-test mode runs. The working tree currently contains the `_normalize_family_label` word-boundary regex fix from 2026-04-15 which is not yet committed to `main`. Required pins — populated by the operator post-commit, before mode (a) executes:

- `git_commit_hash`: _<operator to supply>_
- `sha256(src/ztare/validator/negative_space_extractor.py)`: _<operator to supply>_
- `sha256(src/ztare/validator/structural_constraint_extractor.py)`: _<operator to supply>_
- `sha256(src/ztare/validator/derived_constraints.py)`: _<operator to supply>_

If any field is empty when mode (a) or (c) runs, the cold test is unauthorized and the result is inadmissible as generalization evidence.

### If mode (c) fails on either target — pre-committed failure branch

Pre-committed before either sandbox runs, so the response is not a post-hoc rationalization:

- **Outcome F1 — mode (c) surfaces voids the operator cannot grep-verify.** Component B is not live-wired. A post-mortem seam is opened under GP-061 naming the specific families whose labels contradicted the surfaced voids. The detector's density guard (`MIN_FILLED_SLOTS_PER_KEY`, `_candidate_universe` op catalog) is audited for the observed failure pattern. Sandbox_09 or sandbox_10 is closed under Outcome D (apparatus failure) and the promotion-gate clock resets — no Planck-family cold tests count any more, the two-run gate starts over from the failure on a new target.
- **Outcome F2 — harvest-stress under-harvests twice on both RC and Kepler.** Component B's evaluation is stuck on "no mutator exhibits a structurally disjoint blind spot on targets we can afford to build." Retire the generalization target slate; open a seam on whether the two-run promotion discipline needs a live-failure-corpus source beyond bespoke sandboxes (e.g. running over closed unrelated ZTARE projects in the ledger and treating their failed families as a passive corpus).
- **Outcome F3 — Component A or GP-062 fires on mode (a) or (c) for either target.** The chosen target does not isolate Component B's unique contribution. Not Component B's fault; the target is re-drafted. If re-drafting fails twice the target is retired and the next queued option (B logistic for RC slot, or the logistic fallback named in §Recommendation) is promoted.

In all three outcomes, no edit to `negative_space_extractor.py` happens until the post-mortem seam has read and approved the specific failure pattern. Fixing first and analyzing later is how we got the sandbox_08 hint-template conflation.

### What this spec does not authorize

- Live wiring of Component B into any non-Planck project (requires mode (c) pass).
- Edits to the detector or its siblings (pinned by fingerprint).
- Executing sandbox_09 under the paused pre-reg (orthogonal, still paused).
- Sealing a pre-registration for this target. Pre-reg comes after operator approval + identifiability pass + fingerprint capture.

## Open Questions

**All resolved 2026-04-15. Spec is CLOSED for pre-reg seal.**

- ~~Q1 (target choice)~~ → RC primary as sandbox_09, Kepler pre-committed as sandbox_10, both required to pass before live wiring.
- ~~Q2 (slot reuse)~~ → reuse the sandbox_09 slot.
- ~~Q3 (`V_offset`)~~ → keep.
- ~~Q4 (mutator backend)~~ → same as sandbox_07/08.
- ~~Q5 (corpus drafter)~~ → **fresh subagent, grep-audited.** Spawn an Explore agent with read access to this spec + `negative_space_extractor.py` + `structural_constraint_extractor.py` + `AGENTS.md` only. Operator reviews the subagent's tool-call log before accepting the corpus; any `planck`/`sandbox_07`/`sandbox_08` grep activity invalidates. Operator hand-draft is the fallback if the subagent's audit fails.
- ~~Q6 (calibration seed)~~ → **`V_unfit = V_inf_guess` single constant at mean GT prediction**, not zero. Zero inflates residuals and sets thresholds too loose.
- ~~Q7 (disable flag placement)~~ → **pre-cold-test code change.** The `--disable-negative-space-extractor` flag is added to `autoresearch_loop.py`'s post-eval hook before mode (c) runs; fingerprints are re-captured after the code change.

## Cross-references

- **Seam:** `research_areas/private/seams/GP-061_constraint_accumulation_as_output_seam.md` (Component B live-emission discipline, cold-test promotion gate)
- **Live pre-reg:** `research_areas/private/seams/GP-023_sandbox_09_pre_registration.md` (v2 RE-SEALED 2026-04-15, §A1 amendment; RC step-response target, v2 grid)
- **Retired predecessor:** `research_areas/private/seams/GP-023_planck_sandbox_09_pre_registration_RETIRED_2026-04-15.md`
- **Prior cold tests (Planck-family, insufficient for generalization):**
  - sandbox_07: 12 failed families, 7 voids, `exp(arg0|has_op:Pow)` filled
  - sandbox_08: 8 failed families, 7 voids, `exp(arg0|has_op:Pow)` void
  - gp045_cold_residual_01: 5 failed families, 4 voids, mis-labeled as non-Planck (actually frozen GP-037/GP-042/GP-043 substrate)
- **Detector source:**
  - `src/ztare/validator/negative_space_extractor.py`
  - `src/ztare/validator/structural_constraint_extractor.py` (bug-fixed 2026-04-15)
  - `src/ztare/validator/derived_constraints.py` (`CONSTRAINT_PRODUCERS` extended)

## Status Note

- 2026-04-15 08:00 spec'd (v1, misfiled under seams/).
- 2026-04-15 (same session) v2 — protocol 3rd-party review merged (10 issues).
- 2026-04-15 (same session) **v3 — content 3rd-party review merged + Open Questions 1-4 resolved inline by operator.** Moved to correct location `research_areas/private/specs/active/` per AGENTS.md §4a. Eight content-level fixes merged: pre-stated void leakage to operator (split into sealed-until-post-run pre-reg), harvest-stress tightening rule, gate-threshold calibration procedure, rise-ordering structural-gate annotation, authorship-rule fresh-agent allowance, `--disable-negative-space-extractor` flag as explicit precondition, harvest budget raised to 15, pre-committed failure branch added.
- Remaining before pre-reg seal: resolve the 3 open questions (corpus drafter, calibration seed, flag placement), run the §Implementation Sketch identifiability check, capture detector fingerprints post-commit, then seal the sandbox_09 pre-reg (RC) with the expected-slot name sealed inside. Sandbox_10 pre-reg (Kepler) follows the same pattern and is sealed before sandbox_09 runs, not after.
- Authorship-contamination constraint and the mode (c) expected-slot sealing are both decisive; do not relax either without re-running the 3rd-party review.

## v3 Review-merge log (content review, this session)

| # | Issue | Fix |
|---|---|---|
| 1 | Spec pre-states expected void to operator → anchors mode (c) verdict | Expected slot sealed per-target in pre-reg, not in this spec. Operator commits verdict criterion in writing before pre-reg seal is opened. |
| 2 | RC mutator may converge too fast, leaving no corpus for mode (c) | Pre-committed harvest-stress tightening rule (3× gate tightening, replay from same seed, max 2 replays, then retire target). |
| 3 | Gate threshold 0.01 not justified | Replaced with `<calibrated>` placeholders + deterministic calibration procedure (unfit-seed residual × 30-50%). |
| 4 | Rise-ordering gate is structural not numerical | Annotated as structural. Pre-seal validation plugs the wrong form through the harness to confirm it's actually discriminating. |
| 5 | Authorship rule doesn't allow fresh subagents | Rule amended: fresh subagent with no Planck exposure and clean tool-call log is acceptable; operator hand-draft is fallback. |
| 6 | `--disable-negative-space-extractor` flag doesn't exist | Added as explicit pre-cold-test code change; re-capture fingerprints after adding. |
| 7 | 5 R-sweeps may make mutator converge faster (hurts mode c) | Flagged; harvest-stress rule in fix #2 covers this. Not changed. |
| 8 | No "if Component B is wrong" failure branch | Added three-outcome pre-committed failure branch (F1/F2/F3) before what-this-spec-does-not-authorize. |

Harvest budget also raised 10→15 to match sandbox_08.
