# GP-164 — ZTARE v2.0 Meta-Architecture: REFRAME + ANALOGY

> **Seam metadata** · `seam_id:` GP-164 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: draft (architectural proposal, no implementation)
Opened: 2026-04-26
Track: kernel
Related: GP-152 (Framer spec v2.0), GP-103 (compression primitive), GP-085 (grammar ceiling hypothesis)

## Trigger

2026-04-26 — A 23-year-old with no advanced math training solved a
60-year Erdős conjecture on primitive sets using ChatGPT Pro. Terence
Tao's commentary: "people did look at it, and the humans that looked
at it just collectively made a slight wrong turn at move one." The AI
applied "a formula that was well known in related parts of math, but
which no one had thought to apply to this type of question."

Source: Scientific American, April 2025. Qiacochu Yuan (Twitter/X,
2026-04-25): "spooky implication that there is potentially some whole
universe of 'shadow math' that you have to make inhuman mental movements
to access."

This result has direct implications for ZTARE's architecture. The
apparatus currently searches within a FIXED grammar library — the
operator decides which functional forms are available. The Erdős
result shows the binding constraint on mathematical discovery is not
intelligence, compute, or rigor — it's the SEQUENCE IN WHICH TOOLS
ARE CONSIDERED. ZTARE's grammar library IS a canonical ordering.
The breakthrough came from bypassing that ordering.

## Eigenquestion

> Can ZTARE's architecture be extended from single-axis search
> (grammar enumeration) to three-axis search (grammar × coordinate
> transforms × cross-domain structural analogies) while preserving
> all three philosophical legs (Invert, Compress, Adversarial
> Disagreement) and the cognitive gym constraints?

## The Three Search Axes

### Axis 1: GRAMMAR (v1.0 — current, shipped)

**What it searches:** Functional forms from a curated library.
Example: `{a*exp(-b*x), a/(x+b), a*sin(b*x+c)*exp(-d*x), ...}`

**How it works:** The mutator (LLM) proposes a form. The compression
primitive (`compress_champion.py`) enumerates templates from the
grammar. SciPy fits parameters. Gates validate.

**Binding constraint:** The library is FIXED per run. If the true law
requires a form not in the library, ZTARE hits a grammar ceiling
(INS-050: Planck recovery required adding UNIVERSAL_DENOMINATOR).

**Files:**
- Template library: `src/ztare/primitives/primitive_library.py`
- Compression: `src/ztare/fit/compress_champion.py`
- Grammar config: rubric field `fit_expression_grammar`
- Grammar ceiling hypothesis: `research_areas/private/seams/mission/GP-085_grammar_ceiling_hypothesis_seam.md`
- Grammar ceiling proof: E-GP083-CRUCIAL-02-EXT (compute doubling, zero structural change) vs E-GP083-CRUCIAL-03 (grammar expansion, Planck recovered)

**What it cannot do:** Find the right form if the form is in a
domain the operator didn't think to include. This is the "move one"
constraint from the Erdős result.

### Axis 2: REFRAME (v2.0a — specced, not implemented)

**What it searches:** Coordinate transformations on input/output
variables. Example: `{(x, y), (log x, y), (x, 1/y), (x^2, log y), ...}`
from a transform library `Σ = {identity, shift, scale, power_k, log,
exp, reciprocal}` at composition depth ≤ 2.

**How it works:** Before running the grammar solver, REFRAME tries
each (h_in, h_out) pair from Σ×Σ, fits the grammar in the
transformed coordinates, evaluates MDL in RAW coordinates (Jacobian-
corrected, frame-invariant), and selects the frame that minimizes MDL.

**Key insight:** A law that is complex in raw coordinates may be
simple in transformed coordinates. Example: y = exp(x²)/(1 + log x)
is complex in (x, y) but linearizes in (x², log y - log(1 + log x)).
REFRAME finds this automatically.

**Binding constraint:** Transforms are axis-separable and from a
fixed library. If the correct transform is NOT in Σ (e.g., a Möbius
transform, a Fourier transform, a Lorentz boost), REFRAME cannot
find it. This is a WITHIN-domain search — it changes coordinates
but stays in the same mathematical domain.

**Files:**
- Spec: `research_areas/private/specs/active/GP-152_framer_architecture_spec_v2.md`
- Panel review: `projects/gp152_framer_architecture_audit/` (champion 91)
- Spec critique: `projects/gp153_framer_spec_critique/` (v2.0 MDL formula)
- Gates: G-LIB-COVER (MDL gain ≥ 100 bits), G-FILTER-INDEP (bootstrap |corr| < 0.3), G-SYM-FN (detection ≥ 0.95)
- Rubric flag: `enable_framer` (not yet wired)

**What it cannot do:** Import a tool from a different mathematical
domain. REFRAME finds the right COORDINATES; it doesn't find the
right TOOL. The Erdős breakthrough was a tool transfer, not a
coordinate change.

### Axis 3: ANALOGY (v2.0b — conceptual, not specced)

**What it searches:** Cross-domain structural patterns. Example:
"The residual from the current best form has the shape of a
saturation curve with an asymptote. What mathematical structures
from ANY domain produce this shape?"

**How it would work:**

```
ANALOGY PIPELINE:

1. RESIDUAL EXTRACTION
   Input: champion form f(x), visible data {(x_i, y_i)}
   Output: residual vector r_i = y_i - f(x_i)
   Source: deterministic (same as GP-112 margin_of_safety)

2. STRUCTURAL FINGERPRINT
   Input: residual vector r_i
   Output: structural descriptor S = {
     "shape": "saturation_with_asymptote",
     "monotonicity": "increasing_then_plateau",
     "symmetry": "none",
     "periodicity": "none",
     "tail_behavior": "bounded_above",
     "inflection_count": 1,
     "zero_crossings": 0
   }
   Source: deterministic code (extends GP-110 statistical_fingerprint)
   File: src/ztare/fit/statistical_fingerprint.py (exists, extend)

3. ANALOGY QUERY (LLM-driven, untrusted)
   Input: structural descriptor S (NO domain names, NO variable names)
   Prompt: "The following residual structure was observed after
   removing the best-fit form. What mathematical functions from ANY
   domain produce this structural pattern? List candidate forms as
   symbolic expressions with named parameters."
   Output: list of candidate forms [f1(x; θ1), f2(x; θ2), ...]
   Source: LLM (frontier model, treated as UNTRUSTED hypothesis)
   
   CONTAMINATION GATE (critical):
   - Prompt contains ONLY structural descriptors
   - NO data values, NO variable names, NO domain context
   - LLM response is parsed for symbolic expressions ONLY
   - Domain names in response are STRIPPED before passing to solver
   - Example: LLM says "this looks like Michaelis-Menten kinetics:
     V_max * S / (K_m + S)" → stripped to "a * x / (b + x)"

4. CANDIDATE TESTING (deterministic)
   For each candidate form f_k:
     a. Add f_k to the grammar library (temporary, this run only)
     b. Compose: f_new(x) = f_champion(x) + f_k(x; θ_k) [additive]
        OR f_new(x) = f_k(x; θ_k) [replacement]
     c. SciPy fit on visible data → fitted params
     d. Run full gate stack: holdout, farther-tail, BIC
     e. If gates pass AND BIC improves → candidate survives
     f. If gates fail → candidate dies (Leg 1: cheap failure)
   Source: deterministic (same pipeline as grammar search)

5. META-JUDGE INTERROGATION (Leg 3)
   If any candidate survives gates:
     - Report to meta-judge: "Candidate form f_k was proposed via
       structural analogy from residual pattern S. It passes holdout
       with MRE X. Is the structural basis for this analogy justified,
       or is it a coincidental fit?"
     - Adversarial review committee attacks the analogy basis independently
     - If judges disagree → adversarial escalation (standard)
   Source: LLM judges (multi-model, standard ZTARE Leg 3)

6. PROMOTION (operator-gated)
   If candidate survives gates + meta-judge + adversarial review committee:
     - Report to operator: "Analogy-derived form f_k passes all gates.
       Source structural pattern: S. Do you approve promotion?"
     - Operator decides. Operator is the accountability surface (P9).
```

**Binding constraint:** The analogy query is LLM-driven and therefore
UNTRUSTED. It is a hypothesis generator, not an oracle. The validation
pipeline (steps 4-6) is identical to the grammar search pipeline.
The LLM's contribution is: "here are candidate forms you haven't
tried." The apparatus's contribution is: "here's whether they work."

**What makes this different from just "asking the LLM for ideas":**
The structural fingerprint (step 2) is DETERMINISTIC and DOMAIN-FREE.
The LLM never sees the data, the domain, or the context — only the
residual's structural shape. This prevents contamination (the LLM
can't recognize the problem and retrieve a known answer) while
enabling cross-domain transfer (the LLM can recognize that the
residual shape matches a tool from a different field).

**What it cannot do:** Discover forms that no LLM has seen in
training. If the "shadow math" is truly novel (not in any training
corpus), ANALOGY cannot find it. It can only find tools that EXIST
in the LLM's training data but were not ASSOCIATED with the current
problem class. This is exactly the Erdős case: the formula existed;
the association was missing.

## Architectural Diagram

```
ZTARE v2.0 ITERATION FLOW
══════════════════════════

                    ┌──────────────────────┐
                    │   MUTATOR (LLM)      │
                    │   Proposes thesis     │
                    │   + functional form   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   R1 CONTRACT CHECK   │
                    │   (deterministic)     │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼────────┐ ┌────▼────┐ ┌─────────▼─────────┐
     │  AXIS 1: GRAMMAR │ │ AXIS 2: │ │  AXIS 3: ANALOGY  │
     │  (v1.0, shipped) │ │ REFRAME │ │  (v2.0b, concept) │
     │                  │ │ (v2.0a) │ │                   │
     │  Template enum   │ │         │ │  1. Extract resid  │
     │  from rubric     │ │ h_in×   │ │  2. Fingerprint    │
     │  grammar library │ │ h_out   │ │  3. Query LLM      │
     │                  │ │ from Σ  │ │     (structural    │
     │  Fixed forms     │ │         │ │      only, no      │
     │                  │ │ MDL_v2  │ │      domain)       │
     │                  │ │ in raw  │ │  4. Parse forms     │
     │                  │ │ coords  │ │  5. Strip domain    │
     └────────┬─────────┘ └────┬────┘ └─────────┬──────────┘
              │                │                │
              │    All candidates merged        │
              └────────────────┼────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │  SOLVER (SciPy)      │
                    │  fit_primitive or    │
                    │  fit_primitive_feats │
                    │  (deterministic)     │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  CAGE ORCHESTRATOR   │
                    │  (16 gates, v5.0)    │
                    │                      │
                    │  Holdout MRE gate    │
                    │  Farther-tail gate   │
                    │  Asymptotic gate     │
                    │  BIC ranking         │
                    │  G-LIB-COVER (framer)│
                    │  G-SYM-FN (framer)   │
                    │  Charter gates       │
                    │  (deterministic,     │
                    │   fail-closed)       │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  META-JUDGE + FIRING │
                    │  SQUAD (multi-LLM)   │
                    │                      │
                    │  Attacks form basis  │
                    │  Attacks analogy     │
                    │  validity (if v2.0b) │
                    │  Attacks frame       │
                    │  justification       │
                    │  (Leg 3: disagree-   │
                    │   ment is signal)    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  HARD GATE OVERRIDE  │
                    │  (deterministic)     │
                    │                      │
                    │  holdout_hard_gate   │
                    │  G-CIRC, G-FALSIFY   │
                    │  Score → 0 if fail   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  CHAMPION PROMOTION  │
                    │  + STAGNATION ENGINE │
                    │                      │
                    │  If improved → new   │
                    │  champion + compress │
                    │  If stagnant →       │
                    │  pivot / purge /     │
                    │  ANALOGY trigger     │
                    └──────────────────────┘
```

## The Stagnation → ANALOGY Trigger

ANALOGY should NOT fire on every iteration. It fires when the
standard search (grammar + REFRAME) has stagnated:

```
STAGNATION-ANALOGY TRIGGER LOGIC:

if stagnation_count >= ANALOGY_TRIGGER_THRESHOLD (default: 5):
    if enable_analogy_search:
        residual = champion_form - visible_data
        fingerprint = structural_fingerprint(residual)
        candidates = analogy_query(fingerprint)  # LLM, untrusted
        for candidate in candidates:
            result = solver_fit(candidate, visible_data)
            if gate_stack_passes(result):
                report_to_meta_judge(candidate, fingerprint)
        if no_candidate_passes:
            log("ANALOGY: no cross-domain form passes gates")
            # Continue standard stagnation (pivot/purge)
```

This means ANALOGY is a FALLBACK, not a primary search mode. It
fires only when the standard axes have exhausted their search space.
This preserves the principle that grammar + REFRAME should handle
most substrates; ANALOGY is for the cases where "move one" was wrong.

## Contamination Analysis

The critical risk in ANALOGY is contamination: if the LLM recognizes
the problem domain from the structural fingerprint and retrieves a
known answer, it's not discovery — it's retrieval wearing an
analogy mask.

**Defense layers:**

1. **Structural-only fingerprint:** The LLM receives `{"shape":
   "saturation_with_asymptote", "inflection_count": 1, ...}` — not
   data, not variable names, not domain nouns. Many domains share
   the same structural shapes (enzyme kinetics, population growth,
   signal attenuation). The fingerprint is AMBIGUOUS by design.

2. **Domain-name stripping:** If the LLM response contains domain
   names ("Michaelis-Menten", "logistic growth", "Beer-Lambert"),
   the parser extracts ONLY the symbolic expression and strips the
   attribution. The solver receives `a*x/(b+x)`, not "Michaelis-
   Menten."

3. **Anti-retrieval gate:** Same as GP-159. Check the fitted
   constants against known values for the domain. If they match
   canonical constants (e.g., a₀ = 1.2e-10 for MOND), flag as
   retrieval.

4. **Multi-domain ambiguity test:** If the LLM proposes a form,
   query a SECOND LLM: "In what domains does the form f(x) = a*x/
   (b+x) appear?" If the second LLM names the actual domain of the
   substrate → contamination risk. If it names 5 unrelated domains
   → structural analogy (safe).

## What This Enables: The "Shadow Math" Capability

The Erdős result shows that frontier LLMs can make cross-domain
connections that human mathematicians miss because humans have
canonical orderings (training, intuition, field boundaries) that
LLMs don't share.

ZTARE v2.0b with ANALOGY mechanizes this capability:

1. The LLM's cross-domain pattern matching (its "shadow math"
   access) generates hypotheses.
2. ZTARE's deterministic validation pipeline (gates, holdout,
   adversarial judges) separates signal from hallucination.
3. The operator approves or rejects the validated result.

Neither component alone suffices:
- LLM without validation = hallucination risk (Leg 1 violation)
- Validation without LLM cross-domain search = grammar ceiling
  (the Erdős "wrong turn at move one")

The combination is what makes v2.0b architecturally distinct from
both pure-LLM approaches (no validation) and pure-SR approaches
(PySR, AI Feynman — fixed search axes, no cross-domain).

## Relationship to Paper 5

Chapter 3 of Paper 5 names three operations that did NOT decompose:
eigenquestion selection, recognizing when to reframe, and the social
dynamics of live pressure-testing.

ANALOGY directly addresses the second: "recognizing when to reframe."
The Erdős result shows that reframing is not just coordinate
transformation (REFRAME) — it's recognizing that a tool from a
completely different field solves your problem. If ANALOGY works,
the "recognizing when to reframe" residual shrinks, and Paper 5
Chapter 3 should be updated with the narrower boundary.

This does NOT address eigenquestion selection (what question to ask)
or social dynamics (how to pressure-test in real time). Those remain
in the human residual.

## Three Legs Compliance Check

| Leg | Requirement | REFRAME compliance | ANALOGY compliance |
|-----|------------|-------------------|-------------------|
| Invert (cheap failure) | Failed forms die immediately | ✅ Frame with MDL_gain < 100 bits → auto-disabled | ✅ Analogy candidate failing gates → dead, not softened |
| Compress (asymptotic survival) | Must survive outside fit window | ✅ Evaluated in raw coords, holdout gate applies | ✅ Same holdout + farther-tail gates as grammar search |
| Disagreement (no single oracle) | Multi-judge interrogation | ✅ Meta-judge attacks frame justification | ✅ Meta-judge + adversarial review committee attack analogy basis; multi-domain ambiguity test |

## Cognitive Gym Compliance Check

| Gym layer | v1.0 owner | REFRAME owner | ANALOGY owner |
|-----------|-----------|---------------|---------------|
| Semantic Router (pick the form) | LLM mutator | LLM mutator + REFRAME proposer (deterministic enum) | LLM analogy query (untrusted hypothesis) |
| Topological Sieve (narrow the search) | Component C (residual fingerprint) | Framer frame-invariance gates | Structural fingerprint (deterministic) |
| Deterministic Sidecar (fit parameters) | SciPy curve_fit | SciPy in framed coords, evaluate in raw | SciPy on analogy candidates, same pipeline |
| Contamination Gate (suppress hints) | Denylist + cold variable names | Frame discovery from residual geometry, not domain hints | Structural-only fingerprint, domain-name stripping, anti-retrieval gate |

## Implementation Sequencing

| Phase | What ships | Rubric flag | Depends on |
|-------|-----------|-------------|------------|
| v1.0 (current) | Grammar search + compression | `enable_fit_primitive` | Shipped |
| v2.0a (REFRAME) | Coordinate transform search | `enable_framer` | GP-152 spec v2.0 (done), implementation (not done) |
| v2.0b (ANALOGY) | Cross-domain structural analogy | `enable_analogy_search` | GP-164 (this seam), REFRAME (nice-to-have, not blocking), structural fingerprint extension |

**ANALOGY does not require REFRAME.** They are independent search
axes. ANALOGY can fire without REFRAME (propose forms from cross-
domain pattern matching without coordinate transforms). REFRAME can
fire without ANALOGY (search coordinates without cross-domain tools).
Both are independently valuable. Both feed into the same validation
pipeline.

## Popper Falsifier (pre-registered)

The ANALOGY primitive is falsified if:

1. On ≥ 3 substrates where grammar search stagnates (stag ≥ 5),
   ANALOGY proposes candidates, but NONE pass the gate stack. This
   means the LLM's cross-domain pattern matching adds noise, not
   signal.

2. On ≥ 3 substrates, ANALOGY proposes candidates that pass gates
   BUT are subsequently shown to be retrieval (anti-retrieval gate
   or post-hoc expert review identifies the form as a known result
   from the substrate's own domain). This means ANALOGY is retrieval
   in disguise, not genuine cross-domain transfer.

3. On ≥ 3 substrates, ANALOGY is indistinguishable from "adding more
   forms to the grammar library manually." If the operator could have
   predicted which forms to add, ANALOGY provides no value over
   informed grammar curation.

If any of these falsifiers fires, ANALOGY is rolled back and the
finding documented.

## Open Questions (for panel review before spec)

1. **Should ANALOGY use the same LLM as the mutator?** If yes, the
   LLM's "move one" bias infects ANALOGY. If no, which model? A
   different model family (per epistemic airgap) may have different
   cross-domain associations.

2. **How to prevent the structural fingerprint from leaking domain
   identity?** "Saturation with asymptote at y=K" is structural,
   but if the data is enzyme kinetics and K matches known V_max
   values, the fingerprint is de facto domain-identifying.

3. **Should ANALOGY candidates be additive corrections (f_new =
   f_champion + f_analogy) or full replacements?** Additive preserves
   the champion's structure and corrects the residual. Replacement
   is more radical but may find simpler total forms.

4. **How to evaluate the "cross-domain-ness" of an analogy?** If the
   LLM proposes a form from the SAME domain (just a form the mutator
   hadn't tried), that's grammar expansion, not analogy. Is there a
   metric for analogy distance?

## Debate Log

### Turn 1 (Panel debate, 2026-04-26)

Simulated 6-persona debate: Alien-1 (cross-domain pattern matcher),
Alien-2 (constraint eliminator), Ramanujan (pattern seer), Hardy
(rigor enforcer), Popper (falsificationist). Key findings:

- Aliens: ZTARE's grammar library IS "move one." COMPRESS enum from
  fixed library = canonical ordering. Cross-domain association
  primitive is the missing capability.
- Ramanujan: Patterns are real. Formalization (holdout gates) is
  decisive. Creative bypass belongs to mutator, not apparatus.
  Don't collapse proposal and verification.
- Hardy: "Holistic verification without decomposition" is what we
  call intuition, and intuition is exactly what ZTARE was built to
  distrust. The Erdős case is proof-search, not fitting. Different
  problem class.
- Popper: Produce a substrate where unconstrained LLM discovers
  what ZTARE can't. If you can't, the alien critique is unfalsifiable.

### Turn 2 (Architectural synthesis, 2026-04-26)

Three-axis architecture proposed. ANALOGY is a stagnation-triggered
LLM query over structural fingerprints, validated through the same
gate pipeline. Contamination defense via structural-only descriptors,
domain-name stripping, anti-retrieval gate, multi-domain ambiguity
test. All three legs preserved. Cognitive gym constraints met.

## Next Action

1. Open GP-152 REFRAME implementation as Phase 1 (v2.0a). Spec is
   done; code is not. This is the prerequisite for v2.0a runs.
2. Draft GP-164 ANALOGY spec after REFRAME ships and is validated
   on ≥ 2 substrates. ANALOGY spec depends on understanding how
   REFRAME changes the stagnation landscape.
3. Run a "would ANALOGY have helped?" retrospective on 3 stagnated
   substrates (GP-085 grammar ceiling, GP-096 Langevin depth-1
   ceiling, GP-088 log-land absorbing state) to estimate whether
   cross-domain structural fingerprinting would have proposed the
   correct form.

### Turn 3 (Operator correction + L0/L1/L2 reframe, 2026-04-26 morning)

The Turn 2 framing implied L2 (primitive generation) is "out of scope / not implemented." That was wrong. ZTARE already has three L2-lite mechanisms shipped, all gated on stagnation triggers that have not fired on the substrates run this week:

**L2-lite-A — Topology Synthesizer (GP-078 Component D)**
- Code: `src/ztare/composition/topology_synthesizer.py` (1,370 lines)
- Mechanism: when the primitive library exhausts (Feynman Wall), composes existing primitives under a strict AST grammar to produce *new* primitives the base library did not contain
- Includes generated operators: `CONVOLVE` (Dirichlet convolution), `DERIVE` (forward difference)
- Three components: FailurePackager, LibraryCompiler (no LLM in loop), CompositionMutator (LLM- or PySR-guided)
- Engagement: requires Feynman Wall trigger (≥ K iters of library exhaustion). Has not fired this week.

**L2-lite-B — Margin of Safety library extension (GP-112)**
- Artifact: `workspace/margin_of_safety.json` written in 5+ projects
- Mechanism: post-compression stress tests detect grammar gaps (e.g., Lucky-number loglog deviation). Extends library with the missing primitive and re-fits
- Engagement: requires margin-gate failure. Fired on Lucky number (a=1.200 drift at 500K → loglog grammar gap added).

**L2-lite-C — Reflexive Primitive Discovery (GP-102)**
- Artifact: `research_areas/private/specs/active/apparatus/instrumentation/GP-102_reflexive_primitive_discovery_spec.md`
- Mechanism: cross-project audit detecting zero-variance stagnation (Groundhog Day signature) and proposing new reflexive primitives for principal review
- Output: a seam, not code (creative invention remains principal judgment)
- Engagement: cron-triggered Kaizen audit, not in-run

So the corrected taxonomy:

| Layer | Mechanism in ZTARE | Engagement status |
|---|---|---|
| L0 — Recombination | Mutator + grammar + fit_primitive | Always engaged ✅ |
| L1 — Cross-domain analogy | NOT YET (proposed in this seam) | Architecturally absent ❌ |
| L2-lite-A — Composition | topology_synthesizer | Shipped, fires at Feynman Wall (rare) |
| L2-lite-B — Library extension | margin_of_safety | Shipped, fires on margin-gate fail |
| L2-lite-C — Reflexive detection | GP-102 cron audit | Shipped, out-of-band |
| L2-full — Primitive generation outside human library | Not attempted | Genuinely open research |

**Key correction:** L2-lite is shipped but rarely engaging. The ENGAGEMENT problem is the same problem REFRAME has: the gates protecting these primitives from over-eager firing also prevent them from firing on substrates where they would help. The fix is engagement-logic surgery, NOT new architecture.

### Architectural correction on REFRAME

REFRAME (GP-152) is wired ONLY into the 1D fit_primitive path (autoresearch_loop.py:5038-5052). The N-D fit_primitive_features path has no framer dispatch. This means REFRAME has **never engaged on gp163d, gp154, gp155, gp156, gp158** — all of which use the N-D path. The "homogeneous substrate skip" cited earlier was a different gate (`target_convention_homogeneity` — a prompt-injection control, not a framer-engagement gate).

**Phase 1 fix (this turn):** wire REFRAME into the N-D fit_primitive_features dispatch in autoresearch_loop.py, with a coordinate-transform model adapted for feature-dict substrates (per-feature log/sqrt/inverse on numeric features; identity on categorical).

**Phase 2 fix (Turn 4+):** L1 ANALOGY scaffold building on the existing topology_synthesizer's CompositionMutator, but with a cross-domain query path that the synthesizer currently lacks.


### Turn 4 (ANALOGY wired end-to-end, 2026-04-26 morning)

L1 ANALOGY ships, observe-mode default.

**Code paths shipped:**

  * `src/ztare/fit/analogy.py` (~280 lines) — `build_residual_fingerprint`
    (anonymizes feature names → `cat_feature_0/value_0`),
    `query_analogy` (single-call OpenAI with `response_format=json_object`,
    stdlib urllib, no openai-py dep), `log_analogy` (jsonl audit at
    `workspace/analogy_log.jsonl`), `should_engage` (rubric-flag +
    stagnation/pathological gate).
  * `src/ztare/orchestrator/briefing_providers/analogy_candidates.py`
    — surfaces logged candidates to mutator's next-iter briefing.
    OBSERVE mode renders with "logged, not endorsed" tone; ACTIVE
    mode (rubric flag `enable_analogy_active=true`) renders as
    concrete suggestions.
  * `autoresearch_loop.py` post-fit hook (~line 5360-5430) — reads
    fit_features_result.json, calls should_engage, fires query, logs.
    Wrapped in `try/except` so dispatch errors are non-fatal to the
    iter.

**Engagement gates (per spec):**

  1. Rubric flag `enable_analogy=true`
  2. Prior fit succeeded (need a residual fingerprint)
  3. `stagnation_count >= analogy_min_stagnation` (default 3) OR prior
     fit flagged `pathological=true`

**Contamination defenses (per spec):**

  * Fingerprint anonymizes feature names: `system_class` → `cat_feature_0`,
    individual values → `value_0/value_1/...`. The LLM sees structural
    statistics (residual sign, magnitude envelope, dynamic-range
    decades, cardinality) but NOT the substrate's domain vocabulary.
  * Prompt explicitly forbids domain identification: *"DO NOT name
    physical phenomena (no 'this is Planck', 'this is Michaelis-
    Menten', 'this is RAR'). Domain identification is forbidden."*
  * Briefing provider's "REMINDER" footer reinforces structural-only
    interpretation: *"Do NOT import their domain-of-origin axioms."*
  * Conservation discipline preserved: candidates are per-iter only,
    do NOT modify the operator's static grammar. Cross-substrate
    promotion remains explicit operator action via
    `global_primitives/approved/`.

**Smoke-test (synthetic):** anonymization confirmed (no `system_class`
in output, only `cat_feature_0`); engagement fires when `pathological=
True` even at `stagnation_count=2`; briefing renders structural
descriptors + candidate forms + reasoning + reminder.

**Live-test gate (next):** enable on a substrate that has stagnated
≥ 3 iters this week. Candidates are gp163d (basin-locked at iter 1
with form-class repetition) or any future substrate that hits a
Feynman Wall. Verify the live LLM produces structural rather than
semantic candidates; verify the briefing provider doesn't re-inject
the same candidate across consecutive iters.

**Arch map updated:** 142/142 claims verified post-edit.


### Turn 5 (model selection refactored, 2026-04-26 morning)

**Operator concern:** the initial implementation hard-coded `gpt-4.1`
as the analogy query model and used direct urllib calls to OpenAI's
API. This forks the run's declared model surface and breaks the
cross-family epistemic airgap when the run's judge is intentionally
on a different provider (Claude / Gemini).

**Resolution:**

  * `query_analogy` now requires `model_id` (no default). Hard-coding
    a default is forbidden by spec: it would silently fork the model
    surface declared by the run's `--mutator_model` / `--judge_model`
    flags.
  * Routes through `LLMRuntime.call_text` (existing provider-agnostic
    dispatch in `src/ztare/common/llm_runtime.py`). Inherits the
    apparatus's standard retry policy, cross-provider failover, token
    extraction, and `ZTARE_DISABLE_MODEL_FALLBACK` discipline.
  * Direct urllib + OpenAI-key env-var path removed.

**Model selection convention:**

  1. Default: run's `JUDGE_MODEL_ID` (already configured under cross-
     family discipline; keeps the analogy generator architecturally
     distinct from the mutator's form proposer).
  2. Operator override: rubric flag `analogy_model_id` (e.g. for a
     third-party model when the operator wants a third-perspective
     generator distinct from both mutator and judge).
  3. NEVER a hard-coded default. The early implementation's
     `gpt-4.1` default was a bug; corrected this turn.

**Why judge model and not mutator:**

The mutator generates forms within the operator-curated grammar.
ANALOGY generates forms *outside* that grammar. These are
architecturally distinct generation tasks. Reusing the mutator
model collapses the distinction; reusing the judge model preserves
it (judge is already the "outside perspective" model under cross-
family discipline). The operator may legitimately prefer a third
model entirely; the rubric flag exists for that case.

**Smoke-test:** `query_analogy(fp)` (no model_id) returns
`error="no model_id supplied; analogy must use the run's judge or
mutator model (cross-family hygiene). Pass model_id explicitly from
the dispatch hook."` — fails cleanly, does not crash.



### Turn 6 (Weighted-χ² fit primitive shipped, 2026-04-25 night)

**Context:** during scaffold of the gp165 audit, the operator surfaced
that ANALOGY does not ship alone — REFRAME has been wired into the
N-D path (`framer_nd.py`) and the framer's heteroscedasticity
auto-disable has been the binding scope check on real heteroscedastic
substrates (gp163d's RAR data has SPARC-style measurement-error
heterogeneity that the OLS-only solver cannot model). Gemini-Pro's
diagnosis on the gp163d run: "to break this wall, you need a Weighted
MDL or a Weighted Scipy Solver that can take the per-row measurement
error as an input."

**Decision:** v2.0 = REFRAME + ANALOGY + weighted-χ² fit primitive.
All three ship together; gp165 audits the whole bundle.

**Implementation (`src/ztare/fit/fit_primitive_features.py`):**

  * New parameters: `weighted_residuals: bool = False`, `sigma_key: str = "sigma"`.
  * Pre-computed `sigma_list` aligned with visible_list. Per-row σ=1
    fallback when key missing on a row, when σ ≤ 0, or when σ is
    non-finite (defensive — matches gp163d's `errV_frac` schema where
    some rows might be missing the field).
  * Objective branch: when `weighted_residuals=True`, contribution is
    `((y_pred - y_obs) / σ_i)²`. Backward-compat preserved: weighted=
    False → unchanged behavior (relative_residuals or raw SSE).
  * BIC switch: when weighted, BIC = χ² + K·log(N) (proper MDL form
    when σ is given, not estimated). Reports χ²/N as `sigma_sq` for
    comparability — χ²/N ≈ 1 indicates a good fit per dof. Unweighted
    path unchanged: BIC = N·log(σ̂²) + K·log(N).

**Implementation (`src/ztare/framer/active_framer.py`):**

  * New rubric flag `framer_sigma_provided`: when True, the post-frame
    heteroscedasticity guard (`_check_post_frame_heteroscedasticity`)
    is bypassed — the weighted solver downstream is now the load-
    bearing check, and the guard's job (catching heteroscedasticity
    that breaks BIC's likelihood) is no longer needed.
  * **Acknowledged gap (becomes F7 in the gp165 audit):** the inner
    `branch_and_bound_search` and `evaluate_pair` still use unweighted
    `np.polyfit`. The framer's frame-choice can therefore disagree
    with the weighted solver's optimal frame on heteroscedastic data.
    The bypass is a v0 — full wMDL inside the framer search is a
    follow-on patch.

**Implementation (`src/ztare/validator/autoresearch_loop.py`):**

  * Fit dispatch site reads `fit_weighted_residuals` and `fit_sigma_key`
    from rubric_data and threads through to `fit_features`. Logs a
    one-line "weighted χ² ENABLED" notice when active.
  * Framer dispatch site auto-mirrors `fit_weighted_residuals=True` to
    `framer_sigma_provided=True` (operator can override explicitly via
    the rubric).

**Smoke tests (all pass):**

  * Unweighted fit on linear y = 2x + 3 + N(0, 0.05): a=2.017, b=2.963, BIC=-213.
  * Weighted fit, σ=0.1 homoscedastic: a=2.017, b=2.963, χ²/N=1.21 (BIC=68).
  * Heteroscedastic test (σ=1.0 for rows 0-9, σ=0.05 for rows 10-49):
    weighted recovers a=1.997, b=3.019; unweighted recovers
    a=2.009, b=2.961. Weighted is closer to the true (2, 3) — the
    expected behavior of weighted χ² when the noisy regime is small
    in count but loud in unweighted SSE.
  * Backward compat: weighted=False (default) unchanged; relative_
    residuals path unchanged.

**Open audits (deferred to gp165 + post-gp165 follow-ons):**

  1. F7 (in seed list): wMDL gap inside `branch_and_bound_search`.
     The σ-aware bypass is conservative-correct but the framer's
     internal MDL is still an unweighted-likelihood approximation.
  2. Cross-component F8: per-iter engagement-cost asymmetry. REFRAME
     and wMDL are deterministic (cheap); ANALOGY is API-bound
     (expensive). No per-run cap currently caps ANALOGY firings.

---

## Appendix: Alien-Math Panel Framings (2026-04-27)

**Source:** 4-agent expert panel review of gp163d_unified_accel iter-5 (boost-kernel + sigmoid-suppress form, score 100, identified by all four panelists as RH-18 kernel-camouflage hack). The alien-math forward-looking theorist agent produced three concrete framings outside the McGaugh / Newton / MOND template space. These are the asset repository for the GP-168 Forced-REFRAME mechanism: when the apparatus stagnates AND the same architectural family has been refined for ≥5 iters, the next iter's mutator briefing pulls one or more of these framings as **mandatory disjoint architectures** (the existing family is banned for that iter).

### Framing F1 — Renormalization-Group flow on a single dimensionless coupling

Treat the dimensionless ratio `u = log(g_obs / g_bar)` as a flow along a logarithmic scale variable `t = log(g_bar / μ)` governed by a beta-function with one nontrivial fixed point:

```
du/dt = β(u) = -u · (1 - u/u_*) · (1 + γ · log M)
```

Closed-form integration:

```
log(g_obs/g_bar) = u_*(M) / (1 + (g_bar / g_*)^(1 + γ · log M))
u_*(M) = u_0 + γ_1 · log(M / M_0)
```

K=5: `u_0`, `g_*`, `γ`, `γ_1`, `M_0`. Expressible in current grammar (exp, log, division). Predicts a universal logistic shape in log-log space with slow logarithmic mass running, no kernels, no piecewise switches. The wide-binary y/x<1 regime emerges as sub-fixed-point overshoot; cluster excess emerges as the same fixed point reached at slightly higher u_*. **Recommended primary alien-math attempt.**

### Framing F2 — Modular-form q-expansion in (log g_bar, log M)

Embed `(log g_bar, log M)` as the real and imaginary parts of complex coordinate τ, treat log-residual as truncated q-expansion of a weight-zero modular function. After expansion:

```
log(g_obs/g_bar) = A · exp(-κ · g_bar^p) · cos(ω · log M + φ)
                 + B · exp(-2κ · g_bar^p) · cos(2ω · log M + 2φ)
```

K=6-7. Needs `cos` (already in whitelist). Predicts periodic structure in log M; cluster enhancement and binary suppression as consecutive lobes of the same oscillation with calculable phase relationship.

### Framing F3 — Multifractal Legendre transform on quadratic τ(q)

Treat the (g_bar → g_obs) map as a coarse-graining operator on a singular measure with Hölder exponent α; parameterize log-residual as Legendre transform of a quadratic multifractal spectrum:

```
log(g_obs/g_bar) = α_0 · log(g_bar/g_*)
                 + c_2 · (log(g_bar/g_*) + q_0)^2
                 + δ · log(M/M_*)
```

K=5-6. Already in grammar. Predicts parabolic structure in log-log residuals, asymmetry between binary and cluster regimes given by single offset q_0.

### Panel-recommended log-scale-collapse test

Implementable in the existing analysis layer without rerunning ZTARE. Define `u_i = log(g_obs,i / g_bar,i)`, `t_i = log(g_bar,i / g̃)`. Fit a single rescaling `t_i → t_i · (1 + γ · log M_i)`. If three classes collapse onto a single monotone curve (residual variance drops by >5×), Framing F1 is on the right track. If they show oscillatory structure in log M with consistent phase, F2. If parabolic with mass-shifted vertex, F3. **Backtest result:** see gp163d backtest log under projects/gp163d_unified_accel/workspace/alien_math_backtest.json (when implemented).

### Generalization to other substrates

The three framings translate directly to any substrate where multiple classes span orders of magnitude in some scale-defining feature. For gp154 scaling laws: `log g_bar` → `log N`, `log M` → `log D`. F1's RG-flow logistic is the natural Chinchilla generalization.

### GP-168 forcing-function integration (pending)

When the Forced-REFRAME mechanism fires, the mutator's prompt for that iter must commit to one of {F1, F2, F3} as the base architecture, with the prior architectural family explicitly banned. The judge persona for that iter receives a REFRAME-mode flag scoring architectural disjointness. This converts the framings from "candidates the mutator may consider" into "mandatory alternatives the mutator picks from."

## Appendix: Organizational Topology Alternatives (2026-04-27)

**Source:** GP-168 v2 reframe charter + GP-129 biological panel + GP-167 multi-agent UI panels. Loaded by `alien_math_seam_loader.load_alien_math_alternatives(domain="org_topology")` when a substrate's rubric declares `substrate_domain: "org_topology"`.

**Use case:** when the apparatus stagnates on an organizational-topology substrate (gp168 lineage), the mutator briefing pulls from this appendix instead of the math-family framings above. Each entry describes a *coordination topology family* — a structural specification on the four GP-168 fingerprint axes (Coordination locus, Information flow shape, Death-spiral containment primitive, Locus of priority decision). The mutator's job is to derive the concrete artifacts (mandates, signals, gates, persistence substrate) and the falsification surface from the family.

**Banned:** any topology that shares 3+ fingerprint values with the v1 GP-168 collapse family (centralized priority queue + bounded operator window + TTL decay + per-agent stake + damage multiplier + peer-review escrow + caste-on-queue). Renaming does not unban.

### Framing F1 — Stigmergic / pheromone-trail coordination

```
fingerprint:
  coordination_locus:   stigmergic
  info_flow_shape:      pheromone-trail (read-modify-write on shared environment)
  death_spiral_primitive: graceful pruning by external decay signal on artifacts
  priority_locus:       stigmergic reinforcement (no central operator)
mechanism:
  - shared filesystem encodes prior intent as artifacts with timestamps
  - agents read recent artifacts, modify them, leave new ones
  - artifact age + reinforcement count = priority signal
  - human attention = a stigmergic reader, not a routing target
falsification:
  - if agents converge on stale artifacts (no fresh signal), the trail-decay
    rate is mistuned — observe artifact-age distribution
  - if conflicting modifications cascade, lacks read-write commutativity
```

What it captures: ant-colony / pheromone foraging analog. No central coordinator, no priority queue, no bounded operator. Coordination emerges from artifact persistence + decay + reinforcement. Asymmetric persistence is satisfied by-construction (agents are ephemeral, the trail persists on disk). Death-spiral resistance by structural decay, not by quota.

### Framing F2 — Market / bid–ask coordination

```
fingerprint:
  coordination_locus:   market
  info_flow_shape:      bidirectional (asks broadcast, bids private)
  death_spiral_primitive: market clearing (overpriced tasks expire unfunded)
  priority_locus:       market clearing price (no operator decision)
mechanism:
  - tasks priced by reservation values; bids accumulate; clearing price emerges
  - human posts reservation values for outcomes; agents compete on cost
  - failed clearings = under-priced or over-supplied tasks; signal to operator
falsification:
  - if clearing prices saturate at a single agent's cost basis, market is thin
    (monopsony) — observe price-vs-volume scatter
  - if agents collude on price (price floors), no longer market — observe
    bid-distribution skewness
```

What it captures: Hayekian price-discovery analog. No fixed priority. Agents internalize the cost of their own work. Death-spiral resistance because over-supplied tasks naturally expire. Falsifiable through price-distribution shape. Bidirectional legibility: prices are agent-readable; bid history is human-readable.

### Framing F3 — Mycelial / federation of small autonomous cells

```
fingerprint:
  coordination_locus:   peer-to-peer federation
  info_flow_shape:      local with thin cross-cell channels (rate-limited bus)
  death_spiral_primitive: per-cell hard quota; cells fail independently
  priority_locus:       local autonomy within each cell; cross-cell handshakes
mechanism:
  - many small cells (3-8 agents), each with full local mandate
  - cross-cell channel = rate-limited message bus (e.g., 1 message / cell / hour)
  - human is a cell of one, federated with the others
  - silence = the cell is functioning; it surfaces only on quota breach
falsification:
  - if cross-cell channel becomes the bottleneck (queue grows), federation has
    leaked back into hierarchical routing
  - if a cell exceeds quota and the federation does not isolate it, no real
    structural redundancy — observe cell-failure correlation
```

What it captures: mycelial network / Burning Man theme camp / Gore-Tex lattice. Asymmetric persistence by-cell: each cell maintains its own state file. Death-spiral contained by cell-level quotas; one cell failing does not cascade. Counterfactual against M-form: M-form routes everything through the principal; mycelial routes only inter-cell exceptions.

### Framing F4 — Bicameral / adversarial-pair structure

```
fingerprint:
  coordination_locus:   distributed (two structurally separated bodies)
  info_flow_shape:      bidirectional veto handshake
  death_spiral_primitive: mutual veto (each body can stop the other)
  priority_locus:       distributed committee with veto rights
mechanism:
  - two independent role-cohorts (e.g., "engineer-cohort" + "reviewer-cohort"),
    each with full read access, each able to veto an action by the other
  - actions require matching commits from both cohorts before persisting
  - human is a third veto-holder that breaks ties on rare unresolved cases
falsification:
  - if vetoes accumulate without resolution, mutual constraint exceeds adaptive
    capacity — observe veto-resolution-time distribution
  - if one cohort never vetoes the other, the structural separation is
    cosmetic — observe veto-rate per cohort over time
```

What it captures: Roman tribunes / US bicameral legislature / scientific peer review at architectural scale. Death-spiral resistance because no single body can unilaterally amplify a failure mode. Death-spiral risk if veto-resolution is itself a death-spiral (deadlock); the falsification surface watches that.

### Framing F5 — Karpathy ALU/RAM split (stateless judgment + persistent accumulation)

```
fingerprint:
  coordination_locus:   distributed (judgment-kernel agents + accumulation-kernel)
  info_flow_shape:      pull-on-demand from RAM, write-only to RAM
  death_spiral_primitive: append-only RAM with structural redundancy
  priority_locus:       no central prioritization; agents pull what they need
mechanism:
  - "ALU" agents are stateless validators that read + judge but never persist
  - "RAM" is an append-only artifact corpus (ZTARE-style)
  - any agent can read RAM; only certified writers can write
  - human is a RAM curator, not a routing target
falsification:
  - if RAM grows faster than agents can read it, the pull-cadence is
    mistuned — observe (RAM-bytes / agent-read-bytes-per-day)
  - if ALU agents cache RAM internally, the stateless property is broken —
    observe inter-call ALU consistency on identical RAM snapshots
```

What it captures: ZTARE-on-itself analog. Asymmetric persistence is the ENTIRE design (ALU is ephemeral by-construction, RAM is the persistence substrate). Bidirectional legibility through structured RAM artifacts. Death-spiral resistance by append-only structure.

### Framing F6 — Acentric two-phase commit handshake

```
fingerprint:
  coordination_locus:   distributed
  info_flow_shape:      bidirectional handshake (prepare + commit)
  death_spiral_primitive: hard timeout on prepare-phase
  priority_locus:       no central decision; pairs match independently
mechanism:
  - all decisions require matching commits from two unrelated agent kinds
  - phase 1: agent A proposes, agent B prepares; both lock the artifact
  - phase 2: both must commit within timeout window or rollback
  - human is a tiebreaker only when phase 1 prepares but phase 2 deadlocks
falsification:
  - if rollback rate > threshold, the agent-pair-matching is producing
    incompatible proposals — observe rollback-cause distribution
  - if one agent kind always commits and the other always prepares-only,
    the pair is degenerate (asymmetric collapse) — observe per-kind rates
```

What it captures: distributed-systems 2PC at organizational scale. Death-spiral contained by hard timeout. Falsification through rollback-rate and per-kind asymmetry. Counterfactual against M-form: M-form has a single committer (the principal); 2PC has two structurally separate commit kinds.

### Framing F7 — No-formal-org / emergent coordination via shared file-space

```
fingerprint:
  coordination_locus:   emergent (no formal locus)
  info_flow_shape:      pull-on-demand on shared artifacts
  death_spiral_primitive: no central containment; resilience by structural redundancy
  priority_locus:       no explicit prioritization
mechanism:
  - no roles, no mandates, no signals as first-class objects
  - all coordination through artifacts in shared file space
  - agents read what they want, write what they think relevant
  - human reads occasional summaries; emergence is the design
falsification:
  - if all agents converge on writing the same artifact (collision rate >
    threshold), emergence has produced a centralization — observe artifact
    write-rate distribution
  - if no agent reads what others write, no coordination at all — observe
    read-ratio per artifact
```

What it captures: maximum-disorder anchor. Useful as the lower-bound counterfactual: any topology that beats this on coordination-quality has earned its complexity. If a thesis cannot show its proposed topology beats the no-formal-org case on at least one named failure surface, it is not actually a structural improvement.

### Generalization across substrates

Each framing is a generic coordination-topology, not specific to gp168's evidence surface. Translate to other substrates by re-naming the artifact substrate (filesystem ↔ shared memory ↔ message bus) and the agent kinds. The fingerprint axes remain invariant.

### REFRAME firing on org_topology substrates

When `gp168_stagnation_threshold` is exceeded on a substrate with `substrate_domain: "org_topology"`, the loader returns these seven framings as REFRAME candidates. The mutator's iter prompt commits to one of {F1..F7} as the base topology family with the prior iter's family explicitly banned. The judge persona scores Topology Family Disjointness against this list.
