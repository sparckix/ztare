# Verdict — LeanMill + AxiomPack: soundness, iatrogenics, the STP program, and how AxiomPack gets more novel

Consolidates 00-06 (six reviews, ~75k LOC read across ~113k, load-bearing claims verified by execution: selftests run, tamper tests, live dry-runs, corpus probes). Date: 2026-07-17.

---

## 1. One-paragraph verdict

LeanMill's kernel boundary is genuinely sound — no reviewer found a path that mints "closed" without a Lean compile, historic laundering vectors are covered, and AxiomPack's independence witnesses survive deliberate tampering at three layers. But the *authority periphery* leaks in exactly the places the ARC review predicted: a banned-axiom rejection is laundered back into closure evidence on the live AxiomPack lane, the formal-task lane has no axiom leg at all, faithfulness admission is a single-family LLM vote permanently promoted to certificate while the real certificate leg sits unwired with z3 not even installed, and the ratification stamp fails open on governance crash. Meanwhile the two things you actually want to run next — STP self-play and AxiomPack promotion — are both **built and dark**: the conjecturer has never produced a kept row because its output file has no consumer, and zero packs have ever been promoted because both ratification evidence producers are cold. The novelty is real but sits one seam away: kernel-checked premise attribution + batch-CEGIS countermodel amortization is already unclaimed territory; add one *checked signature interpretation* with discharged obligations (the dischargers already exist and are sound) and the "Langlands-style" framing becomes defensible instead of aspirational.

## 2. Soundness scoreboard

| Layer | Verdict | Sharpest hole |
|---|---|---|
| Solver kernel boundary | **Sound** — every closure route ends in `_is_compile_ok` + anti-laundering + axiom audit | Ratification stamp fail-open on outer governance crash (solver_core.py:5204; one-line fix) |
| Statement integrity | Sound — binders-after-colon, warm-path alteration, notation hijack all covered | — |
| AxiomPack independence | **Sound and verified by tamper test** — semantic replay at 3 layers, Z3 never trusted raw | Cheap-filter stuck at carrier size 2; its own demo domains can't certify (dead size-5/7 knobs) |
| Campaign closure evidence | **Leaky** | `rejected_banned_axiom` laundered via compile-only recheck (lean_consequence_bridge.py:449 — LIVE lane); formal-task lane has no axiom check; audit_external vacuous-pass + zero callers; recompilation advisory |
| Faithfulness admission | **Judge-vibes** | 2/3 single-family vote → permanent `confirmed=True` before solving; certificate leg unwired, z3/sympy not installed (dead instrument); defs structurally blind since the `_claim_signature` change |
| Training corpora | **Contaminated** | Selftest FalseRender row exported as training data; discriminator corpus single-class with wrong artifact recorded; 27% NLs truncated; holdout leaks siblings (31/60 eval rows ≥0.8 Jaccard to train) |

## 3. Same iatrogenic disease as ARC, different organ distribution

The ARC review's defect classes recur here almost verbatim:

- **Produce/verify split** (the LeanMill-specific signature): verifiers wired, producers cold. AxiomPack ratification (`verify_ratification_receipt` live, `evaluate_shadow_ab`/`certify_conditional_lowering` zero callers → 0 promotions ever); certified faithfulness (honest 3-verdict code, no production caller); audit_external (the external trust door, zero callers); campaign_closure_gate (enforced in code, zero receipts ever written).
- **Built-but-unwired / orphaned outputs:** self-play corpus file with zero consumers; void_self_play.py as a disconnected sibling conjecturer; typed_exit unused by the frontier layer; morphism layer with zero receipts; resume preflight never run in any flow.
- **Parallel implementations of one boundary:** anti-laundering kernel invoked twice with different baselines (same bug patched separately at both sites — the repo's named "missed sibling" class, live); two self-play lanes; two AxiomPack systems sharing one name; parallel status vocabularies instead of typed_exit.
- **Monoliths breeding placement bugs:** solver_core.py 5,912 lines (the L9 decomposition backlog), frontier_campaign_runner.py grown to 9,828 — every mode-dependent door bug (preverified champion dropped in dag mode; decompose-first outside the leakage quarantine) is a placement bug these monoliths make easy.
- **Receipt identity incompleteness:** kernel_parity rows with no timestamp/hash/run-id; certs with run_id in 0 of 777; workbench results bound by path string; job specs silently rewritten 14 days post-run.
- **Selftest pollution of production ledgers** (a named RCA class, recurred): FalseRender in the no-good store AND the falsification training corpus.
- **The P0 timing RCA re-opened:** `time_to_closure_s` is again prove-window-only; no measured end-to-end time-to-closure exists in analytics.
- **Overhead ratio:** ~4:1 governance-to-proving in the campaign runner; a third of the plumbing layer is telemetry-on-telemetry.

Difference from ARC: the inner ring here is stronger (the kernel is a real, external authority — the one thing that cannot be Goodharted), and several uncommitted diffs are disciplined root-cause fixes. The disease is concentrated in the periphery and in the gap between "wired" and "fired."

## 4. Prioritized remediation

### P0 — soundness on live paths (small diffs, this week)
1. **One axiom-audit chokepoint:** kill the `rejected_banned_axiom` upgrade (lean_consequence_bridge.py:449) or make the recheck run `audit_axioms_subset`; add the axiom-receipt check to formal_task_campaign_executor.py:928-943; make audit_external fail closed unless every decl appears in probe output (`axiom_probe_satisfied` shape already exists in proof_audit.py).
2. `integrity_unverified=True` in the outer governance except (solver_core.py:5204).
3. Fix the two live-lane loop breakers: `_receipted_reject_all` ValueError (theory_navigator.py:439-472) and the `prediction_formula_id` key mismatch (theory_lineage_synthesis.py:130).
4. `git add src/ztare/leanmill/first_order_baseline.py` (untracked file imported into five module chains incl. the CLI).
5. Purge the FalseRender selftest row from no-good store + falsification corpus; guard `_record_statement_false_no_good` when solve_fn is injected.
6. Disposition-supersession path before the budget-reopen machinery ships (else the first genuinely-discharging extended campaign wedges).

### P1 — make the pending STP run count (the user's task)
7. **Wire self-play at the cert chokepoint:** transfer closures append a real cert row (ts, goal_sha, correct checker, probe-bytes sha) to `adhoc_closure_certificates.jsonl` instead of the orphaned `self_play_corpus.jsonl`; point default seeds at the canonical 197-row corpus.
8. **Fix NON-TRIVIAL:** splice the cheap-tactic cascade via the warm REPL instead of `default_triviality`'s blob-skipping entry; let its fail-closed raise reject.
9. **Fix the family-holdout** (transitive def-sharing merge + name-stem keys for `solo:` targets; verify 0 cross-split def-sharing and no ≥0.9-Jaccard pairs) — without this the pre-registered headline is not defensible.
10. If using `--codex-fallback`, set `ZTARE_LEANMILL_ISO_ROUTE=0` / `ZTARE_LEANMILL_DECOMPOSE_FIRST=0` (the cheap-prover lesson, second occurrence).
11. Then run self-play over the 197 seeds; re-measure the data-starvation premise (corpus already doubled since the memory) before committing GPU time.

### P2 — economics and honesty
12. One closure epilogue chokepoint (fixes the decomposition-lift banking amnesia + stamp placement); one anti-laundering invocation; preverified-champion door in dag mode.
13. Timing: stamp `record_campaign` at frontier launch; consumers read `wall_s`.
14. Rebuild training corpora with provenance filters (altered-probe recording, cross-corpus consistency pass, kill the `nl[:400]` cap); persist verdict provenance in the faithfulness store; install z3/sympy.
15. Receipt identity: job_id + source hash in results; timestamp/hash/run-tag in kernel_parity; run_tag in certs.
16. Deletion pass: decidability_router, governance_organs, void_self_play (fold into the conjecturer), theory_landscape_morphism (or rebuild per P3), dead knobs, stale flags, the `src/src/` duplicate tree. Execute the L9 solver_core decomposition; stop growing frontier_campaign_runner.

### P3 — the novelty program (AxiomPack → actually Langlands-ish)
17. **Route pack screening through the SMT finder** (make the size-5/7 knobs live) so the demo domains can certify their own separations (M3/N5 need size 5).
18. **Close the ratification loop:** wire `evaluate_shadow_ab` + `certify_conditional_lowering` into the live campaign lane — one pack promoted end-to-end validates the whole contract stack (currently 0 ever).
19. **Build the one checked interpretation seam:** signature morphism (source ops → target terms) + axiom translation, obligations discharged by `certify_implication`/SMT for finite obligations and the consequence bridge for Lean-level ones. Delete or rebuild theory_landscape_morphism on it.
20. **Run E4 (morphism transport of conjectures) — zero training required** — then E1 (STP-lite band-selection on the non-math corpus), per `06_stp_research_program.md`. Prototype morphism *discovery* (LLM-proposed, kernel-verified, non-triviality-obligated interpretations between independently invented theories) — the single addition that converts AxiomPack from "in-house ETP + little theories" into an unclaimed research object.

## 5. Direct answers

**"Can STP self-play work for our non-mathlib niche?"** Yes, and the literature now supports the niche premium quantitatively (TaoBench: SOTA provers drop ~26% off-mathlib; Seed-Prover has nearly saturated human benchmarks — the frontier is exactly self-generated domains). The mechanism to adapt: STP's (0,1/4] pass-rate band for conjecturer training signal, anchored to your unclosed-target distribution instead of a human statement pool (Q1-Q5 in file 06). Precondition: P1 above — today the loop would write into a void through a fail-open gate onto a leaking holdout.

**"Self-play on all the things we've generated, including AxiomPack?"** This is the strongest idea in the whole program. Self-play *inside machine-invented, kernel-verified axiom systems* — with countermodels making every conjecture resolvable (prove-or-refute, ETP-style) and independence witnesses as a difficulty signal where pass-rate bands saturate — appears genuinely unclaimed (Q6-Q11; nearest art: Minimo on fixed human theories, FERMAT without kernel-verified self-play). E3 + E4 are the pre-registered entry points; E4 needs no training.

**"AxiomPack is very novel and can be more novel — it's a Langlands-style program."** Honest split: today the mechanics are a disciplined little-theories/in-house-ETP program with one genuinely novel seam already in the code — kernel-checked premise attribution (leave-one-out replay proving a consequence depends on the pack) + batch-CEGIS countermodel amortization + receipted residual pricing. It is *not yet* Langlands-style: the morphism layer maps fingerprints to themselves with permanently-pending obligations, and zero transport receipts exist. The distance to the real claim is one seam (P3.19) plus morphism discovery — both buildable with dischargers you already have. A discovered, kernel-verified, non-trivial interpretation between two machine-invented theories would be the first receipt of its kind anywhere.
