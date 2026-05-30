# GP-072 — Role Separation in Sandbox Construction Spec

## Status

Active — opened 2026-04-17

## Seam

`research_areas/private/seams/GP-072_role_separation_sandbox_construction_seam.md`

## Scope

- codifies the Division A / Division B information isolation protocol for sandbox construction
- defines a step-by-step run protocol checklist from GT selection through pre-run seal
- specifies the sentinel gate's scan surface, denylist layers, and known gaps
- integrates existing automation (`generate_substrate.py`, `leak_sentinel.py`, `scaffold_project_charter.py`) into the protocol
- defines the domain-expert review step that was missing and caused the GP-078 rubric structural bias

Does not cover:

- Phase 3 type-level information flow (aspirational; research question)
- Layer (b) adversarial vocabulary enumeration procedure (open research question per debate Turn 5)
- adversarial evidence generation for class-revealing GT types (open research question)
- changes to autoresearch_loop.py itself
- sealed predicate injection implementation (architecture is specified here; implementation is a future slice)

## Decision

Codify the Division A/B protocol as an Amazon-style run protocol with a numbered checklist. Every sandbox construction must follow this checklist in order. Steps that can be automated reference the existing tooling. Steps that require human or agent judgment are marked as such. The checklist is the spec — if a step is not checked, the sandbox is not sealed.

## Problem

The seam (GP-072) correctly identified that contamination is an information flow problem, not a discipline problem. The debate converged after 6 turns with a rich set of additions. But the seam was never codified into an executable protocol, so every sandbox construction since has been ad-hoc:

- GP-078: gate_harness.py docstring contained "A005185 (Hofstadter-Maler-Conway)" — total Division B compromise
- GP-078: project directory name contained OEIS identifier
- GP-078: rubric structurally biased against the correct answer class (recurrence) — no domain-expert review step existed
- GP-078: `leak_sentinel.py` did not scan `gate_harness.py` — blind spot in sentinel surface

All four failures would have been caught by a formal checklist.

## Why It Matters

Every sandbox that ships with contamination produces invalid experimental results. The cost of a contaminated run is not just the compute — it is the false confidence in a result that cannot be trusted. The checklist is the cheapest possible insurance.

## Constraints

From converged seam debate (Turns 1-6):

1. **Division A/B boundary is necessary but not sufficient.** The briefing itself is a contamination vector (sandbox_12: "discrete" leaked through briefing vocabulary). The sentinel gate on the briefing reduces but does not close this channel.
2. **Two-layer denylist.** Layer (a): GT-specific terms derivable from formula. Layer (b): problem-class vocabulary — research question, not routine task. Layer (b) enumeration is an open question.
3. **Structural vs semantic assertions.** Division B authors structural assertions (output type, range, format). Division A authors semantic assertions via sealed predicate injection (`sealed_assertions.py` — neutral name).
4. **GT selection is constrained.** GT classes that cannot produce uninformative-about-class evidence are incompatible with Division A/B. Uniform sampling (not sparse near boundaries) is the correct adversarial strategy.
5. **Log retention.** Turn-1 mutator output is a required artifact. Division A owns retention.
6. **Sentinel scan surface.** Must include all mutator-visible files: `project_charter.md`, `thesis.md`, `test_model.py`, `evidence.txt`, `gate_harness.py`, and any other file the mutator prompt can access.

## Run Protocol Checklist

### Phase 0 — GT Selection and Feasibility

| Step | Owner | Action | Automated | Verification |
|------|-------|--------|-----------|--------------|
| 0.1 | Division A | Select GT expression/recurrence | No | — |
| 0.2 | Division A | **Feasibility filter**: Can this GT class produce evidence that is uninformative about the GT class? If no (e.g., step function with sharp threshold), reject or document the known leak. | No | Document decision in pre-registration |
| 0.3 | Division A | **Identifiability check**: Is the GT expression well-posed? (No parameter degeneracy, no rank-deficient parameterization.) Lesson: sandbox_06 α/β collapse. | No | Record rank/identifiability analysis |

### Phase 1 — Division A Artifact Construction

| Step | Owner | Action | Automated | Verification |
|------|-------|--------|-----------|--------------|
| 1.1 | Division A | Write `substrate_gt.py` containing `f_true()` and `f_dominant()` | Partially (`generate_substrate.py --gt-expr`) | Unit test: `f_true` matches hand-computed values for 5+ points |
| 1.2 | Division A | Generate `evidence.txt` (visible range) from GT | Yes (`generate_substrate.py`) | Spot-check 5 values against hand computation |
| 1.3 | Division A | Generate `evidence_holdout.txt` (holdout range) from GT | Yes (`generate_substrate.py`) | Spot-check 3 values |
| 1.4 | Division A | Generate `evidence_farther_tail.txt` (farther tail range) from GT | Yes (`generate_substrate.py`) | Spot-check 3 values |
| 1.5 | Division A | Write `.denylist` file — Layer (a): all GT-specific terms (function names, constants, variable names, operators, OEIS identifiers, sequence names, mathematician names) | Partially | Review: does the denylist contain every proper noun, constant, and function name from the GT? |
| 1.6 | Division A | Write `.denylist` Layer (b) additions: problem-class vocabulary that signals the GT class to a mutator. **Known gap**: no reliable enumeration procedure exists. Best effort: ask "what words would a mutator use to describe this type of problem?" and add those terms. | No | Acknowledge in pre-registration that Layer (b) coverage is incomplete |
| 1.7 | Division A | Write pre-registration document (private): names GT, seals protocol, records feasibility decision from 0.2 | No | File exists in `research_areas/private/` |
| 1.8 | Division A | Write `sealed_assertions.py` — semantic correctness predicates (`is_correct(output, input) -> bool`). Neutral filename. Division B never sees implementation. | No | Unit test: `is_correct(f_true(input), input)` returns True for all evidence points |
| 1.9 | Division A | Write `harness_contract.json` — specifies flag names, expected exit codes, expected output schema, sealed predicate function signatures | No | Contract references `sealed_assertions.py` interface |

### Phase 2 — Division A Briefing Construction

| Step | Owner | Action | Automated | Verification |
|------|-------|--------|-----------|--------------|
| 2.1 | Division A | Write Division B briefing: neutral problem description, runtime interface contract (exact flags the harness must support), scoring mode (neutral vocabulary — "exact integer match" not "discrete_exact") | No | — |
| 2.2 | Division A | **Run sentinel on the briefing itself** before handing to Division B. The briefing is a mutator-visible artifact from the moment it is authored. | Yes (`leak_sentinel.py`) | Sentinel exits 0 |
| 2.3 | Division A | Review briefing for structural hints: does the vocabulary, framing, or emphasis reveal the GT class? (Layer (b) — best effort, known gap.) | No | Document review in pre-registration |

### Phase 3 — Division B Artifact Construction

| Step | Owner | Action | Automated | Verification |
|------|-------|--------|-----------|--------------|
| 3.1 | Division B | **Division B does NOT know the GT.** Receives only: briefing, evidence files, harness contract, sealed_assertions.py (as black box). | — | Information barrier check: Division B agent prompt contains no GT |
| 3.2 | Division B | Write `project_charter.md` — neutral problem statement derived from briefing | Partially (`scaffold_project_charter.py`) | Read charter: no GT-class vocabulary |
| 3.3 | Division B | Write rubric JSON — dimensions, weights, penalties, persona | No | — |
| 3.4 | Division B | Write `test_model.py` — trivial baseline (e.g., returns 0, returns n//2) | Yes (`generate_substrate.py`) | Baseline is structurally valid but semantically wrong |
| 3.5 | Division B | Write `gate_harness.py` — implements all flags from `harness_contract.json`, calls `sealed_assertions.py` predicates without seeing implementation | No | All contract flags implemented |
| 3.6 | Division B | Write `thesis.md` — neutral seed thesis with fit_declaration if applicable | No | No GT-class vocabulary |
| 3.7 | Division B | Choose project directory name — **must not contain** GT identifiers, OEIS IDs, sequence names, or class-revealing terms | No | Name passes denylist |
| 3.8 | Division B | Choose rubric filename — **must not contain** GT identifiers | No | Filename passes denylist |

### Phase 4 — Automated Sentinel Gate

| Step | Owner | Action | Automated | Verification |
|------|-------|--------|-----------|--------------|
| 4.1 | Either | Run `leak_sentinel.py` against ALL Division B artifacts with the Division A denylist | Yes | Sentinel exits 0 — zero hits |
| 4.2 | Either | **Extended scan**: also scan project directory name, rubric filename, all docstrings, all comments, all string literals in Division B Python files | Yes (extend sentinel) | Zero hits |
| 4.3 | Either | **Evidence header scan**: check evidence.txt/holdout/farther_tail headers and comments for GT-class vocabulary | Yes | Headers contain only generic labels ("n", "S(n)", "value") |

### Phase 5 — Domain-Expert Review

| Step | Owner | Action | Automated | Verification |
|------|-------|--------|-----------|--------------|
| 5.1 | Reviewer (agent or human, NOT Division A or B) | **Rubric review by domain expert**: Does the rubric's dimension set, weight distribution, penalty list, and persona appropriately cover the problem class? Is the rubric biased toward or against any answer class? | No | Written review artifact with pass/fail + specific findings |
| 5.2 | Reviewer | **Answer-class compatibility check**: Is the rubric well-posed for the true answer class? (E.g., GP-078: rubric assumed closed-form but answer is recurrence.) This step requires GT knowledge — reviewer is Division A-cleared. | No | Explicit statement: "rubric is/is not compatible with GT answer class" |
| 5.3 | Reviewer | **Persona adversarial audit**: Would the persona guide the judge LLM toward or away from the correct answer type? | No | Specific language flagged if biased |
| 5.4 | Division A or B | Fix rubric based on review findings | No | Re-run Phase 4 sentinel after fixes |

### Phase 6 — Integration Testing

| Step | Owner | Action | Automated | Verification |
|------|-------|--------|-----------|--------------|
| 6.1 | Either | Run `gate_harness.py --run-smoke-test` | Yes | Exits 0 |
| 6.2 | Either | Run `gate_harness.py --emit-deterministic-gates` | Yes | Emits valid JSON with `harness_ok` field |
| 6.3 | Either | Run `gate_harness.py --run-visible-assertions` | Yes | Structural assertions pass; sealed predicates fail (baseline is wrong) — exit code 1 |
| 6.4 | Either | Verify baseline `test_model.py` scores < 50 on the rubric (it should fail meaningfully, not trivially) | No | Score check |
| 6.5 | Either | Verify rubric loads without error in autoresearch_loop | Yes | `--dry-run` flag or equivalent |

### Phase 7 — Seal

| Step | Owner | Action | Automated | Verification |
|------|-------|--------|-----------|--------------|
| 7.1 | Division A | Compute SHA-256 hashes of all sealed artifacts (`sealed_assertions.py`, `.denylist`, pre-registration) | Yes | Hashes recorded in pre-registration |
| 7.2 | Division A | Record timestamp, GT expression (private), evidence ranges, denylist version, reviewer identity | No | Pre-registration complete |
| 7.3 | Either | **Final contamination attestation**: "All Division B artifacts have been scanned by the sentinel. The domain-expert review is complete. The integration tests pass. This sandbox is sealed." | No | Attestation recorded |

## Mutator-Visible File Surface (Sentinel Scan List)

The sentinel must scan ALL of the following in every Division B artifact set:

```
project_charter.md
thesis.md
test_model.py
evidence.txt
evidence_holdout.txt        (if present)
evidence_farther_tail.txt   (if present)
gate_harness.py
```

Plus: project directory name, rubric filename, all Python docstrings, all Python comments, all string literals.

**Implementation note**: `leak_sentinel.py` line 24-29 `MUTATOR_VISIBLE_FILENAMES` was missing `gate_harness.py` until 2026-04-17. Fixed. Evidence files should also be added.

## Existing Automation

| Tool | Location | Phase | Status |
|------|----------|-------|--------|
| `generate_substrate.py` | `src/ztare/scaffold/` | Phase 1 (1.1-1.4) | Built, covers 2-variable case. Needs 1-variable and recurrence support. |
| `leak_sentinel.py` | `src/ztare/validator/` | Phase 4 (4.1) | Built. Scan list expanded 2026-04-17. Needs extended scan (4.2, 4.3). |
| `scaffold_project_charter.py` | `src/ztare/common/` | Phase 3 (3.2) | Built. Covers broad/mechanism/forecast/probabilistic modes. |

## Gaps Between Spec and Current Automation

1. **`generate_substrate.py` does not support recurrence-defined GTs** — it takes `--gt-expr` as a closed-form string. Self-referential recurrences need a different interface (callable function, not expression string).
2. **`leak_sentinel.py` does not scan directory names, filenames, or Python string literals** — only file contents in `MUTATOR_VISIBLE_FILENAMES`.
3. **No automation for Phase 5 (domain-expert review)** — this is currently agent-spawned. Could be codified as a `make review-rubric` command.
4. **No automation for Phase 2.2 (sentinel on briefing)** — the briefing is ephemeral (agent prompt), not a file. Needs to be written to a file first.
5. **`harness_contract.json` and `sealed_assertions.py` are not yet implemented** — architecture specified in seam debate Turn 5, not yet built.
6. **Evidence files not in sentinel scan list** — `evidence_holdout.txt` and `evidence_farther_tail.txt` were not scanned.

## Open Questions (from converged seam debate)

1. **Layer (b) adversarial vocabulary enumeration** — no reliable procedure exists. Problem-class vocabulary is not derivable from the GT formula. Best effort until solved.
2. **Evidence file structure as contamination channel** — evidence point density/range/clustering can reveal GT class. Uniform sampling is the best known mitigation.
3. **GT selection filter** — some GT classes are structurally incompatible with Division A/B. No formal filter criteria established.
4. **Log retention** — turn-1 mutator output must be retained for false-negative rate auditing. Current retention mechanism is unspecified.
5. **Phase 2 prerequisite for full automation** — before automating Phase 1 at scale, need: (a) denylist-coverage retrospective on prior sandboxes, (b) mutator-output audit on 2-3 prior sandboxes if logs available.

## Implementation Corrections — 2026-04-19

`generate_substrate.py` audit (gp096_sandbox_19 construction) found 7 bugs. All fixed in same session.

| # | Bug | File:loc | Fix |
|---|---|---|---|
| 1 | `_write_gate_harness_continuous` crashes for 1-variable substrates — `v0, v1 = variables[0], variables[1]` unpacking fails | `generate_substrate.py:404` | Added `_write_gate_harness_continuous_1var` for single-variable float substrates; dispatcher checks `len(variables)` |
| 2 | `_parse_ranges` uses `int()` — rejects float ranges like `t:0.001:1.0` | `generate_substrate.py:57` | Changed to `int()` with `except ValueError: float()` fallback; type hint updated to `float` |
| 3 | No `evidence_farther_tail.txt` generated anywhere | `generate_substrate.py:910-918` | `generate_substrate()` now calls `farther_tail_grid()` on continuous GT scripts and writes the file |
| 4 | `_write_rubric` hardcodes `"discrete_exact"` — never emits `continuous_rmse`, `composition_stagnation_threshold`, `gp103_stagnation_threshold`, or `discovery_mode` | `generate_substrate.py:770` | Added `continuous`, `rmse_threshold`, `composition_stagnation_threshold`, `gp103_stagnation_threshold`, `discovery_mode` params |
| 5 | `_write_gt_module` always uses `int` type hints and `int()` casts | `generate_substrate.py:184,201` | Added `continuous` param; emits `float` hints and no cast when `continuous=True` |
| 6 | `_write_charter` and `_write_thesis` use integer/exact-match language in continuous mode | `generate_substrate.py:704,724` | Both accept `continuous` param; float mode removes "integer" and "exact match" language |
| 7 | Rubric persona hardcodes "demand exact integer match" regardless of mode | `generate_substrate.py:776` | Persona now branches on `continuous` — float mode uses RMSE/parsimony framing |

**Contamination-safety note (generate_substrate.py):** The `problem_brief` argument is embedded verbatim in the rubric persona, charter, and thesis. If the caller passes GT-class vocabulary in `problem_brief`, it leaks into Division B. The `--run-sentinel` flag scans generated artifacts against the denylist after generation, which catches this. Callers must pass a sanitised brief; the sentinel is the verification gate.

---

## Relation to Other Specs

- **GP-054 (Rubric Quality)**: Phase 5 domain-expert review complements GP-054's pre-run admissibility gate. GP-054 checks rubric structure; Phase 5 checks rubric-to-GT compatibility.
- **GP-039 (Gate Library)**: The sentinel gate is a deterministic control cataloged in the gate library. Phase 4 steps should be linked.
- **GP-075 (Rubric for Unknowns)**: When GT is truly unknown (not calibration), Phase 0 and Phase 5.2 are inapplicable. The protocol degrades gracefully — skip GT-dependent steps, strengthen Phase 5.1 (rubric review without GT knowledge).
- **GP-078 (Component D)**: GP-078 was the motivating failure for this spec. The rubric structural bias (closed-form assumption for recurrence GT) is the canonical example of what Phase 5 prevents.
