# GP-211 — Lean-Proof Substrate Class

> **Seam metadata** · `seam_id:` GP-211 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-09


Status: shipped (smoke verified, full make-loop validation pending)
Opened: 2026-05-03
Owner: GP-211 / paper 8

## Eigenquestion

> When a rubric declares the substrate is a Lean proof, what artifact must
> the apparatus actually run to falsify it — and how do we prevent the
> judge from scoring Lean-shaped prose as if it were a verified theorem?

## The gap (motivating failure)

GP-211 iter-1 (score 93) and iter-2 (score 95) both shipped a thesis that:

- Cited two Mathlib v4.30 lemmas in PROSE: `Mathlib.CategoryTheory.Sites.Pushforward`
  and `Sites.Equivalence.transport_isSheaf`.
- Verified by hand: NEITHER lemma exists in Mathlib v4.30. Both hallucinated.
- Wrote a Python tautology `I_model() -> 0.5` to `test_model.py` — passed
  G-FALSIFY (≥1 numeric assertion present) and the deterministic charter
  gates (no explicit Lean check).
- Had no ```lean fenced block at all.

The judge (gpt4.1) cannot run Lean. It scored:
  - the prose mentioning real-shaped Mathlib paths,
  - the Python tautology returning True,
  - the deterministic gates passing,
as "validated." The tautology was the decisive falsifier; the Lean
content was decorative. Result: a score-95 promotion of a thesis whose
core citations don't exist.

This is the same class as the GP-135 P4 gate failure ("lake build succeeds
does not guarantee mathematical truth") but one layer earlier: here lake
build wasn't run AT ALL because the apparatus had no notion of "this
substrate is Lean."

## Architecture

Three-piece dispatch:

1. **`src/ztare/gates/lean_proof_gate.py`** — pure gate module.
   - `extract_lean_from_thesis(thesis_path) -> str | None` parses the largest
     ```lean fenced block from thesis.md.
   - `write_lean_target(source, slug, root) -> Path` writes to
     `ztare_proofs/ZtareProofs/<slug>_iter.lean` verbatim (preserves imports
     and namespace declarations exactly).
   - `compile_lean(path, root, timeout) -> dict` runs `lake build
     ZtareProofs.<stem>` from the ztare_proofs root with explicit cwd, env,
     timeout, no shell=True.
   - `audit_axioms(path, root) -> dict` reuses `scripts/public/lean/verify_lean_stub.py`
     for the lexical-token sweep (`sorry`/`admit`/`native_decide`/standalone
     `axiom`) and runs a lake-built `<stem>_axioms.lean` driver to extract
     `#print axioms` output (lake-aware so Mathlib imports resolve).
   - `compute_secondary_observables(path) -> dict` returns
     `{line_count, mathlib_lemma_count, applied_lemmas}` for the rubric's
     Generative Yield dimension.
   - `run_lean_proof_gate(...)` orchestrator: extract → write → compile →
     audit → observables → `gate_passed = compiled AND axiom_audit_passed
     AND not forbidden_tokens`.

2. **`src/ztare/validator/lean_substrate_runner.py`** — integration shim.
   - `is_lean_proof_substrate(rubric)` returns True iff
     `rubric["cage_meta"]["substrate_class"] == "lean_proof"`.
   - `run_lean_substrate_iteration(project_dir, rubric, iteration)` reads
     `thesis.md`, dispatches to the gate, maps the verdict to the existing
     `test_suite_status` taxonomy (`pass` / `fail_assert` / `fail_runtime`),
     and persists the full gate dict to `lean_proof_gate_result.json` for
     audit.
   - `format_judge_facing_summary(gate_result)` renders the structured
     "LEAN UNIT TEST RESULT" block (one field per line) that REPLACES the
     tautological "✅ PASS: All discriminators passed" string the judge
     previously saw.

3. **Patch in `src/ztare/validator/test_thesis.py`** — minimal dispatch.
   Inserted at the top of LEVEL 3 falsification suite execution: when
   `is_lean_proof_substrate(main_rubric)` is True, call the runner and
   slot its result (`test_result_summary`, `test_suite_status`) into the
   existing eval pipeline. Other substrate classes go through the
   unchanged `test_model.py` path. Diff is ~30 lines.

## Contract: `cage_meta.substrate_class: "lean_proof"`

Downstream, this declaration means:

- The thesis MUST contain a ```lean fenced block. No block ⇒ gate fails
  with "extracted=False" and the iteration is rejected.
- The block is written verbatim to `ztare_proofs/ZtareProofs/<slug>_iter.lean`
  and built via `lake build`. Imports, namespaces, and tactics are the
  mutator's responsibility.
- `lake build` exit 0 is necessary but not sufficient. The post-compile
  axiom audit rejects any theorem depending on axioms outside
  `{propext, Classical.choice, Quot.sound}`, and the lexical scan rejects
  `sorry`, `admit`, `native_decide`, or standalone `axiom` declarations.
- The judge's UNIT TEST block becomes:

      LEAN UNIT TEST RESULT
      compiled: <bool>
      lake_exit_code: <int>
      compile_duration_s: <float>
      axiom_audit_passed: <bool>
      extra_axioms: [...]
      forbidden_tokens: [...]
      line_count: <int>
      mathlib_lemma_count: <int>
      applied_lemmas: [...]

  The rubric's Generative Yield dimension scores these directly; the judge
  no longer sees a tautological PASS string.
- `test_model.py` is reduced to a one-line stub (`assert 1 < 2`) so
  G-FALSIFY's mechanical precondition is satisfied without giving the
  Python path any epistemic weight.

## Anti-gaming checklist

| Pattern | How GP-211 iter-2 evaded | How the new gate kills it |
| --- | --- | --- |
| Hallucinated Mathlib lemma in prose | judge can't check Mathlib | thesis must put the lemma INSIDE a ```lean block; lake build resolves the import; missing lemma → "unknown identifier" → gate fail |
| Python tautology test_model.py | passed G-FALSIFY | runner bypasses test_model.py entirely; only `lake build` exit code counts |
| `sorry` in proof | lexical scan was off | `verify_lean_stub.lexical_scan` runs every iteration |
| Smuggled `axiom foo : P; apply foo` | no `#print axioms` audit | lake-built `<stem>_axioms.lean` driver; any axiom outside allowlist → fail |
| `native_decide` on abstract goal | bypasses kernel | covered by the same lexical scan |
| Lean-shaped pseudocode (no compile) | no compile happened | extraction step fails on missing language tag; OR compile fails if the syntax is invalid |
| Mismatch between prose claim and Lean theorem | judge accepted prose | judge sees `applied_lemmas` and `mathlib_lemma_count` from the Lean source itself, not the prose |

## Smoke test (verified 2026-05-03)

- (A) GP-211 iter-2 thesis as-is (no ```lean block): `gate_passed=False`,
  rationale = "No ```lean fenced block found in thesis.md" — rejected at
  extraction.
- (B) Synthetic minimal thesis containing `theorem one_eq_one : 1 = 1 := rfl`:
  `gate_passed=True`, compiled in ~3s, axiom audit passed.
- (C) Synthetic hallucination thesis with `import
  Mathlib.CategoryTheory.Sites.Pushforward` + a fake lemma reference:
  `gate_passed=False`, `lake_exit_code=1`, compile failed.

All three exercise the orchestrator end-to-end against the real
`ztare_proofs` lake project with Mathlib v4.30-rc2.

## Open questions / future work

1. **`lean --check` against pre-built cache.** Rubric's Throughput Realism
   dimension targets ≤5s/candidate. Current `lake build` from-scratch is
   2-3s for trivial proofs and many minutes for Mathlib-heavy ones. Need
   to wire `lean --check` against a pre-built oleans cache for production
   throughput. Currently `compile_lean` always uses `lake build`.
2. **Driver clean-up race.** `_audit_axioms_via_lake_driver` writes
   `<stem>_axioms.lean`, builds it, then deletes it. If two iterations of
   different substrates run concurrently against the same `ztare_proofs`,
   they could collide. M-form serialization currently makes this moot,
   but flag for parallel-org runs.
3. **Generative-Yield rubric scoring.** The rubric expects the secondary
   observables to be a calculable, surviving Newton-mode signal.
   `mathlib_lemma_count` is permissive (counts surface usage). Tighten
   to `lake build`-resolved identifiers if the count becomes a gaming
   target.
4. **Promote `lean_proof_gate.py` into the deterministic-charter gates
   surface.** Currently the gate is dispatched via the test-suite path,
   not the `deterministic_charter_gates` schema. If we want gate-stack
   reporting (G-FALSIFY-style row in `score_contract`), wire it through
   `global_gates.py`.
5. **Apply to other formal-substrate rubrics.** Once the contract is
   stable, audit other rubrics for `cage_meta.substrate_class` values
   that imply external verifiers (Coq, Isabelle, SMT, etc.) and design
   sibling runners.

## Files

Created:
- `src/ztare/gates/lean_proof_gate.py`
- `src/ztare/validator/lean_substrate_runner.py`
- `research_areas/private/seams/engine/GP-211_lean_proof_substrate_class_seam.md` (this file)

Modified:
- `src/ztare/validator/test_thesis.py` — substrate-class dispatch (~30 lines).
- `projects/gp211_paper8_lean_proofs/test_model.py` — replaced tautology
  with one-line stub + comment redirecting to `lean_substrate_runner`.

Unchanged but referenced:
- `rubrics/gp211_paper8_lean_proofs.json` — already has
  `cage_meta.substrate_class: "lean_proof"`; no changes needed.
- `scripts/public/lean/verify_lean_stub.py` — imported (not modified) for axiom-allowlist
  + forbidden-token logic.

## Update 2026-06-07 — runner already reuses the canonical leanmill kernel (NOT naive)

Re-audited `lean_substrate_runner` against leanmill (the question: is it a parallel/weaker Lean
verifier that should route to leanmill?). Finding: **it already routes through the ONE canonical
governance kernel.** `run_lean_substrate_iteration → run_lean_proof_gate` (lean_proof_gate.py) which,
with `enforce_anti_laundering=True` (default), calls **`run_anti_laundering_kernel`** — the same v33 +
`statement_integrity` anti-laundering stack leanmill's `solve_adhoc` uses. So it is NOT a duplicate/weaker
governance and needs no rewrite for soundness.

What it deliberately does NOT do — and correctly so: it **VERIFIES** the mutator's `thesis.md` Lean proof,
it does not **SEARCH** for a proof. The only future "route to leanmill" that would ADD capability is if the
autoresearch loop wants the **solver** to actually attempt/produce the proof (not just grade the mutator's) —
that is a `solve_adhoc` call, a feature addition, not a correctness fix. Until then the runner stays as a
governed verifier reusing the shared kernel. (The old G3/ansatz "blocked on live Lean pipeline" concern is
likewise resolved — see GP-144 §9.)
