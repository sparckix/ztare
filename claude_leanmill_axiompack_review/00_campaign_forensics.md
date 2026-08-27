# LeanMill + AxiomPack review — campaign forensics (evidence lane)

Reviewer: Claude (conductor lane). Date: 2026-07-17.
Measured directly from the working tree, `analytics/public/`, and project memory — not from docs.

## Apparatus scale

- `src/ztare/leanmill/`: **113,150 LOC** (of which `solver/`: 38,669). Larger than the entire ARC worldmodel layer (39.8k).
- Uncommitted working tree (leanmill): **+3,144 / −273 across 21 files**, plus **7 new untracked modules**: `campaign_closure_gate.py`, `compound_implication_sieve.py`, `external_science_admission.py`, `formal_task_boundary.py`, `formal_task_campaign_executor.py`, `generative_representation.py`, `first_order_baseline.py`.
- ~130 top-level modules in leanmill/ + ~50 in solver/.

## Training corpus (analytics/public/leanmill/training_corpus/manifest.json)

| metric | value |
|---|---|
| prover_pairs | 197 (110 void-novel, 32 with CoT) |
| autoformalization_pairs | 227 |
| faithfulness_discriminator_pairs | 166 |
| falsification_pairs | 20 |
| total_distinct_pairs | 610 |
| raw_closed_certs | 673 |
| dedup_near | false (α-dedup only — matches the ruled design) |

Growth since the 2026-07-02 memory snapshot: prover corpus 96 → 197 pairs. The corpus is compounding.

## AxiomPack live state

- `axiom_pack_live_eval.json`: mode **live**, model codex, n=8; blueprint lint ok with required receipts (nontriviality, consistency_smoke, model_or_example, strength_comparison, separation_or_interpretation, downstream_yield); **proof_credit_quarantined: true**; `second_domain_probe_ok: null` (pending); `next_domain_to_stress: inverse_semigroups`. Downstream yield policy: shadow_replay, `proof_credit_eligible: false`, `theorem_campaign_admissible: false` — packs are correctly held conditional.
- `conjecture_book.jsonl`: **36 event rows** (e.g. `instance_confirmed` with finite-instance evidence), single run_tag `apr_waterfall` (2026-06-24). Small; one campaign's worth.
- Workbench jobs: 12 files in `analytics/public/leanmill/workbench/jobs/`.
- Solver lane snapshot (`leanmill_solver_lane_results.json`): 1 row, `closed`, credit boundary **advisory_only_no_factory_credit** — typed exits explicitly not credit-ready without the governance receipt path.

## Pending tasks from project memory (the STP thread)

From `project_void_sft_passk_inflight` (2026-07-02) + `reference_notes_to_direct_prompt_and_selfplay_prover`:

1. **Self-play first** (operator-agreed refinement): with ~96 proofs the SFT loop is data-starved → run `self_play_conjecturer.py` on codex (no GPU) to grow the corpus to several hundred, THEN round-1 LoRA training.
2. Then the A10 sequence: bootstrap venv → `train_lora.py` → `sample_vllm.py --n 32` → `passk_score.py` on the Lean VPS → pass@k curve + CIs.
3. Pre-registered claim: SFT on kernel-verified NON-math proofs lifts unbiased pass@k on held-out non-math families over base+few-shot, matched K/temp; headline = pass@8/16 delta CI > 0; a null is informative (corpus-vs-loop bottleneck).
4. Design lesson already paid for: the self-play prover must be CHEAP — proof-transfer-first (splice the seed's proof, warm REPL ~2s), codex only as adapt-fallback, defer the hard tail. Result when applied: 2 verified in 2 min vs 0 in the prior hour with the heavy cascade.

Note: corpus already grew 96 → 197 prover pairs since that memory, so step 1's premise (data starvation) should be re-measured before the GPU spend.

## Reusable RCA classes this review must check against (from memory index)

- Statement-integrity laundering (binders-after-colon; warm-path statement alteration) — FOUND+FIXED historically; verify not regressed.
- Faithfulness prior-confirmed short-circuit name-brittleness (#105).
- Scratch-artifact collision → content addressing.
- P0 time-to-closure under-reporting (formalize/prove split).
- `#print axioms` does not catch corpus leakage; authoritative axiom gate was module-incompatible once (runs void).
- Premise-shelf leakage; carrier ghost; env-parity single door; decomp-cache reuse churn.
- Vacuous-bridge / consolidation GATE 3 triviality (relevant to conjecture non-triviality gates).
