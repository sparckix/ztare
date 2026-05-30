# GP-216b — Mechanization Roadmap: Two-Cultures Ops as Gates vs Director Judgment

> **Seam metadata** · `seam_id:` GP-216 · `track:` engine · `status:` active · `last_updated:` 2026-05-08


**Status:** active *(inferred 2026-05-08 — needs operator review)*

*2026-05-05. Companion to GP-216 (theory-building) + paper 5b (problem-solving sister vocabulary). Empirical correction recorded: ZTARE seams are 47% problem-solver-shaped, 5% theory-builder-shaped (not the other way around as I predicted).*

## Decision frame

For each of the 18 ops (12 tb_ + 6 ps_), classify into one of three categories:

- **Mechanizable (deterministic gate)** — can be checked by code with no LLM-in-loop; fail-closed; runtime-cheap.
- **Hybrid (gate + LLM judgment)** — partial mechanization; deterministic part shipped as gate, judgment part stays with Director.
- **Director-only (org/ agent: Codex/Claude)** — irreducibly judgment; cannot be mechanized without LLM-in-loop; Director recognizes and handles.

The Mungerian discipline: when a class of error is deterministically catchable, mechanize it. When the move requires creative recognition / object invention / framework selection, keep it as Director judgment. The gate library grows; the Director's load shifts toward genuinely judgment-bound work.

## Per-op classification

### Theory-building vocabulary (12 ops)

| Op | Mechanizable? | Gate candidate | Notes |
|---|---|---|---|
| **tb_01** Foundational Object Redefinition | NO | — | Requires recognizing when one object class is wrong for the problem. Director-only. |
| **tb_02** Cross-Domain Unification | NO | — | Requires noticing two domains map. Director-only. |
| **tb_03** Surrogate Problem Substitution | PARTIAL | `SufficientConditionTraceabilityGate` — verify any "X via Y" claim has a Lean-checked entailment Y → X | Currently: Codex's NS Track B falsifier-spine theorems already approximate this. Could be generalized as a deterministic gate. |
| **tb_04** Constraint-Driven Solution Forcing | YES | `ConstraintStackTracebilityGate` — every required structural constraint must have a named receipt before solution accepted | Already partially mechanized in NS Track B's `TrackBFiniteFalsifierSurface` typed object. Generalize. |
| **tb_06** Tacit Pattern Formalization | YES | `TacitPatternRecurrenceDetector` — scan F-rows for recurring patterns (≥3 instances), propose formalization as named Lean predicate or gate | This is the meta-gate: ZTARE's most-instantiated tb op (Pass 8: 4/40 cycles). Auto-detect recurring resolution moves and surface candidate-formalization proposals. |
| **tb_08** Parameter Space Internalization | NO | — | Requires recognizing parametric family structure. Director-only. |
| **tb_09** Systematic Vocabulary Lifting | NO | — | Too abstract; requires structural-mapping creativity. Director-only. |
| **tb_11** Limitative Theorem Construction | YES | `NamedFalsifierEnumerableSurfaceGate` — every closure obligation must enumerate its named falsifier theorems | Already shipped at Track B finite-falsifier-spine level (Codex Turn 51-62). Generalize to other substrates. |
| **tb_NEW_HOF** Diagonal Self-Application | NO | — | Requires creative diagonal construction. Director-only. |
| **tb_NEW_POLYA** Strategic Specialization | PARTIAL | `StagnationSpecialCaseHintGate` — when score stagnates ≥N iterations, propose structurally-narrow special cases | Selecting the *right* special case stays Director. Detection of stagnation + suggestion-trigger is mechanizable. |
| **tb_LAK1** Refutation-Driven Concept Revision | PARTIAL | `CounterexampleConceptRevisionDetector` — when a counter-example invalidates a definition, flag for revision and surface which sub-clause it broke | Detection mechanizable; revision itself stays Director. |
| **tb_LAK2** Proof-Analysis Under Counter-Example | PARTIAL | `SubstepLocalizationGate` — when proof fails on counter-example, automatically run binary-search-style sub-step localization | Localization is mechanizable (Lean-tactical); incorporation as a new lemma is judgment. |

**TB ops gate-candidates:** tb_03 (partial), tb_04 (yes), tb_06 (yes — the meta-gate), tb_11 (yes), tb_NEW_POLYA (partial), tb_LAK1 (partial), tb_LAK2 (partial).

### Problem-solving vocabulary (6 ops)

| Op | Mechanizable? | Gate candidate | Notes |
|---|---|---|---|
| **ps_01** Structural Partitioning | PARTIAL | `StructuredChaoticPartitionGate` — when problem is decomposable, verify partition has structured + chaotic typing | Detection of decomposability is judgment; verification of typing is mechanizable. |
| **ps_02** Governed Iterative Refinement | YES | `PotentialFunctionMonotonicityGate` — for any iteration with a declared potential, verify (i) potential strictly improves each iteration, (ii) ceiling holds, (iii) iteration terminates | **High-priority candidate.** Catches stagnation + infinite-loop in any iterative substrate. Universal across rubric modes. |
| **ps_03** Formal Equivalence Transfer | NO | — | Requires noticing the cross-domain bridge. Director-only. |
| **ps_04** Black-Box Theorem Application | PARTIAL | `BlackBoxPreconditionGate` — when an existing theorem is invoked as black-box, verify its preconditions are met by the current substrate | Detection of "applicable theorem" is search; precondition verification is mechanizable. |
| **ps_05** Induction on Structural Rank | PARTIAL | `InductionRankWellFoundednessGate` — for any inductive proof, verify the rank function is well-founded and the induction step is correct | Standard ATP technique. Lean has tools. |
| **ps_06** Proof by Estimate Chaining | YES | `BoundChainConsistencyGate` — for any proof chaining bounds, verify each step's premise matches prior step's conclusion (no unit-mismatch, no scope-leak, no implicit constant abuse) | **High-priority candidate.** Catches a real failure mode: silent constant inflation across bound chain. Concrete and useful. |

**PS ops gate-candidates:** ps_02 (yes — high priority), ps_06 (yes — high priority), ps_01/04/05 (partial).

## Top 4 candidate gates worth shipping (priority order)

### 1. PotentialFunctionMonotonicityGate (ps_02) — UNIVERSAL VALUE

**What it does:** For any rubric mode that involves iteration (most ZTARE rubrics), declare a *potential function* in rubric metadata. Each iteration's score is checked against the previous iteration's score under the potential function. The gate fires fail-closed if:
- Potential does not strictly improve for ≥3 consecutive iterations (stagnation)
- Potential exceeds declared ceiling (out-of-bound iteration)
- Potential function is not declared (forces explicit declaration)

**Why high-priority:** catches genuine failure modes (infinite-loop iteration; score-game where potential decoupled from real progress; missing termination proof). Universal across substrates. Cost: ~50 lines Python + rubric-metadata schema extension. Return: potentially saves dozens of wasted iterations per substrate run.

### 2. BoundChainConsistencyGate (ps_06) — LEAN/PROOF VALUE

**What it does:** For any Lean theorem chain (NS Track B falsifier surface, etc.), the gate parses the chain's bound declarations and verifies:
- Each bound's premise variables match the prior step's conclusion variables
- No silent constant inflation (e.g., bound 1 says `≤ C·E`, bound 2 says `≤ C·E·5`, gate fires)
- Each bound's scope domain is declared and consistent with substrate's topology

**Why useful:** catches a class of error that's hard to spot in Lean review. Codex's recent NS Track B work would benefit. Cost: ~200 lines Python (Lean AST walker) + receipt-typing convention. Return: precludes a class of false-positive Clay-bridge candidates.

### 3. TacitPatternRecurrenceDetector (tb_06) — META-GATE

**What it does:** Periodically scans F-rows and seams for recurring resolution patterns (≥3 distinct instances of the same structural-move-class). Surfaces candidate-formalization proposals to the Director. The Director decides whether to formalize as a typed Lean predicate.

**Why interesting:** This is GP-215's pattern-bank-injection at meta-meta-level. ZTARE's most-instantiated theory-building op (Pass 8: 4 of 40 cycles). Cost: ~150 lines Python (F-row pattern miner + recurrence threshold + proposal renderer). Return: shifts theory-building work from "Codex notices a recurring pattern" to "ZTARE auto-surfaces the candidate."

### 4. StagnationSpecialCaseHintGate (tb_NEW_POLYA) — DIRECTOR-ASSIST

**What it does:** When ZTARE score stagnates ≥N iterations on a substrate, the gate surfaces a list of structurally-narrow special-case candidates derived from the rubric's grammar. The Director picks one (judgment). The gate ensures the Director is presented with the option, doesn't choose blindly.

**Why useful:** addresses GP-180/181-style stagnation where the principal frame is wrong, not the parameters. Cost: ~80 lines Python + grammar enumeration. Return: faster Director recognition of frame-vs-parameter stagnation.

## What stays Director (Codex/Claude when launched via org/)

The 8+ ops that resist mechanization are the genuine work of the org/-launched Director:

- **tb_01 Foundational Object Redefinition** — recognizing when the WHOLE object class is wrong (variety→scheme decision)
- **tb_02 Cross-Domain Unification** — noticing two domains have a structural correspondence
- **tb_08 Parameter Space Internalization** — recognizing a parametric family
- **tb_09 Systematic Vocabulary Lifting** — recognizing when porting an entire theory is the right move
- **tb_NEW_HOF Diagonal Self-Application** — creative diagonal construction
- **ps_03 Formal Equivalence Transfer** — noticing the cross-domain bridge

Plus the *judgment* portion of partial-gates: choosing which special case (tb_NEW_POLYA), choosing the right concept revision (tb_LAK1), incorporating localized lemmas (tb_LAK2), recognizing decomposability (ps_01).

These are precisely the moves Gowers calls "creative" rather than "technical." Mechanizing them would require LLM-in-loop or AI-research-assistant capability beyond ZTARE's deterministic-gate scope.

## Recommendation

**Ship in order:**

1. PotentialFunctionMonotonicityGate (ps_02) — universal, catches real failure modes; ~50 lines + schema; ship this week.
2. BoundChainConsistencyGate (ps_06) — high-leverage on NS Track B closure; ~200 lines + Lean walker; 1-2 days.
3. TacitPatternRecurrenceDetector (tb_06) — meta-gate that compounds (gates beget gates); ~150 lines; 1 day.
4. StagnationSpecialCaseHintGate (tb_NEW_POLYA) — Director-assist; ~80 lines; 1 day.

**Defer:**

- All Director-only ops stay with Codex/Claude in org/ — no code work.
- Hybrid gates (ps_01/04/05, tb_LAK1/LAK2) wait until specific use-case appears in active substrate work.

**Total cost ~480 lines of Python + minor schema extension. Total return: 4 deterministic gates that mechanize 4 real failure modes, leaving the Director free for genuinely judgment-bound work.**

## Honest correction

My prior prediction was wrong: I predicted ZTARE seams would be theory-builder dominant. The keyword classifier returned 47% problem-solving / 5% theory-building (and 46% unclassified). Even acknowledging the keyword-bag bias toward grand mathematical-theory vocabulary, ZTARE works MORE as a problem-solver than as a theory-builder. The 18% theory-building rate from Pass 8 (per-cycle LLM mapping) is the careful number; the keyword classifier under-detects theory-building. Both findings together: ZTARE has problem-solver foundation with theory-building moments.

This corrects the implicit "ZTARE = theory-building apparatus" framing in some prior memos. The accurate framing: ZTARE = adversarial-verification apparatus, structurally problem-solver-shaped, with periodic theory-building moments when tacit patterns are formalized into Lean gates.
