# Review — self-play + training-corpus infrastructure (the STP pending task)

Cluster: `scripts/public/control/leanmill/self_play_conjecturer.py` (328), `src/ztare/leanmill/solver/void_self_play.py` (208), `export_training_corpus.py` (315), `scripts/public/models/void_sft/format_corpus.py` (179), `sample_vllm.py` (88), `passk_score.py` (106), `kernel_check.py` (137) + targeted reads in `solver_core.py`, `autoformalize.py`, `repl_compile.py`, `proof_cache.py`, `gen_samples.py`. ~1,360 LOC in full + ~500 supporting. Entry points exercised live (REPL up, dry-run completed); corpus counts verified; holdout tested against the real 197-row corpus.

## Runnable-today verdict

**Mechanically YES — but the run as pointed would grow nothing.** Live: `void_self_play --selftest` 12/12; conjecturer `--dry-run --seeds 25` completes end-to-end (toolchain v4.30.0-rc2 matched, 38.3s Mathlib import, 9 proposals → 5 gated). No renamed-API breakage in the uncommitted tree.

Exact blockers for "grow 96→several hundred":

1. **Orphaned output (the real blocker).** `self_play_conjecturer.py:13` claims "a self_play_corpus.jsonl the exporter folds in" — but `export_training_corpus.py:43-46` reads only certs/faith/nogood/plan stores. **Zero consumers of `self_play_corpus.jsonl` repo-wide.** Proof-transfer closures (lines 275-277, explicitly "skip solve_adhoc's cert") land in a file no pipeline consumes; only `--codex-fallback` closures would surface (via solve_adhoc's own cert write). The transfer row schema (`proof`, no `outcome`/`ts`/`proof_text`) also wouldn't survive `prover_rows`' filters (`export_training_corpus.py:174-180`: requires `outcome=="closed"`, `proof_text`, `ts >= clean_since` — missing `ts` ⇒ dropped) even if folded in.
2. **Stale default seeds.** Candidate list at `self_play_conjecturer.py:212-213` tries `scripts/public/models/void_sft/corpus_fresh/` (doesn't exist) then `~/void_sft_artifacts/corpus_fresh/prover_corpus.jsonl` — the stale Jul-2 96-row copy. The canonical fresh export (`analytics/public/leanmill/training_corpus/prover_corpus.jsonl`, 197 rows) is not in the list; `pc` at line 210 is dead. Must pass `--prover-corpus` explicitly.
3. **Yield expectation.** 25 seeds → 5 gated proposals ⇒ extrapolated over 197 seeds, transfer-only yields tens, not "several hundred," before the prover runs.

**Never fired:** no `self_play_corpus.jsonl` anywhere; zero `*_sp` targets among 777 cert rows; zero `_sp_*.lean` substrate files. The conjecturer has never produced a kept row.

## Findings

### self_play_conjecturer.py / void_self_play.py
- **Proof-transfer-first: genuinely implemented.** Lines 263-281 splice the seed's proof and compile via warm REPL (`timeout=90`, `reject_sorry=True`) before any codex call; codex opt-in (`--codex-fallback`, default OFF). The design lesson is in the code.
- **ISO_ROUTE/decomposition NOT disabled on the fallback.** With `--codex-fallback`, the `solve_adhoc` call at line 301 passes no mode and doesn't set `ZTARE_LEANMILL_ISO_ROUTE=0`/`ZTARE_LEANMILL_DECOMPOSE_FIRST=0` (both default-on, solver_core.py:4957, 4884) — each conjecture gets the full recursive-planner cascade, the exact heavy path the design lesson said to avoid. The `notes` seed-proof hint (line 298) even feeds the decomposition planner.
- **NON-TRIVIAL gate fails open on def-carrying probes — empirically confirmed.** `gate()` (line 176) calls `default_triviality(probe, ...)` on the full emitted probe; `autoformalize.py:1811` short-circuits `_define_then_state_blob` probes (any def/variable/open block before the theorem — most self-play candidates; 110/197 seeds are void_novel) to `return False` — the cheap-tactic (`rfl`/`simp_all`/`tauto`) and `nondegenerate_instance_probe` (vacuity) legs never run; only the lexical check fires. Confirmed live: dry-run kept `root ∈ granted ∧ root ∈ boundary → root ∈ granted ∩ boundary` (tauto-trivial) as "non-trivial," while `default_triviality` on the same statement without preamble correctly returns True. Failure: trivial and vacuous-hypothesis variants (the vacuous-bridge RCA class — unsatisfiable instance combos from `instance_vary` are exactly what `nondegenerate_instance_probe` exists for) pass the gate, transfer-close instantly, pollute the corpus with zero-signal rows. Additionally `gate()` :178-180 swallows `default_triviality`'s deliberate fail-closed raise into keep — inverting its contract.
- **α-key dedup properly shared:** `_akey` (71-77) → exporter's `_akey` → `proof_cache.normalize_statement_equiv` — one door; normalizer verified comparable across gate keys and corpus keys.
- **No kernel-verification receipt bound to artifact bytes.** Transfer record carries `{target, statement, proof, recompilable_probe, source, seed, mode, checker}` — no `ts`, no `goal_sha`, no governance/solver_validation block. `checker: "lean_lake"` is asserted but verification was `compile_probe_via_repl` — a mislabel. Nothing binds verdict to bytes (violates the data-admissibility standing rule).
- **void_self_play.py is a disconnected sibling.** Selftest passes; nothing imports it; `amplify` never fired; duplicates the conjecturer's role via a different mechanism (`anti_unify` schemas vs signature mutation) with a different dedup entry. Two self-play lanes, neither aware of the other — the anti-sibling pattern.

### Exporter + format_corpus + real corpus
- **Jaccard near-dedup correctly opt-in** (`--dedup-near` default OFF, autoformalization NL only); α-key is the prover default. Matches pre-registration.
- **Corpus counts verified:** manifest (197/110/32/227/20/166 = 610) matches actual line counts exactly.
- **Family-holdout leaks siblings — measured on the real corpus.** `content_family_map` (format_corpus.py:101-119) implemented as claimed, but the "no transitive chaining" choice + per-probe def subsets defeats it: `split_family_holdout(rows, 30)` on the 197 rows yields 137 train / 60 eval with **33 eval/train family pairs sharing ≥1 custom def** and **31 of 60 eval rows at ≥0.8 token-Jaccard to a train row** — including eval `e2e_conj_route_conj1` vs train `e2e_conj_route_conj2` at 1.0 and eval `iso_lemma2_…` vs train `iso_lemma1_…` at 1.0. Pure-Mathlib targets get `solo:<name>` families, so name-siblings split freely (the now-dead name-based `_family`/`_is_generic` at :82-98 would have caught `e2e_conj_route_conjN`). Failure: the pre-registered ft-vs-fewshot headline is inflated by memorization of near-identical train siblings — the exact inflation design-step-2 existed to kill.

### sample_vllm + passk_score
- **Chen pass@k correct** (verified numerically vs brute force). The `k > n ⇒ float(c>0)` degrade is documented but silent — scoring a K=16 gens file at k=32 quietly reports "any compiled" as pass@32.
- **Bootstrap CI correct and the delta properly paired** (same resample indices both arms per iteration — the right test for the pre-registered delta claim).
- **Arms matched** in sample_vllm (one SamplingParams; ft=LoRA, fewshot=base). In the fallback sampler actually used (gen_samples.py), dynamic `max_new` (context-fit, :88-92) gives longer fewshot prompts a smaller generation budget — a small systematic anti-fewshot asymmetry (fallback path only).
- **Silent fallbacks that could invalidate the claim:** (a) `score_arm` on a missing/misspelled arm key yields `(0,0)` → scores 0.0 silently; (b) `kernel_check._compiles` swallows all exceptions to False — a broken lake/REPL environment scores every sample FAIL for both arms and prints a plausible "not significant" with no infra warning; (c) `rank = ....get("r", 64)` defaults silently.

### What has actually run
- Jul 2 (round 1, 96-row corpus): format+split ran (65 train / 31 eval), LoRA trained, NLL eval ran (NLL lift; faithfulness_acc 0→0.844) — but sampling used the **transformers fallback at K=16 on only 11 targets** (gen_passk3.log), not the pre-registered vLLM N=32 over ≥30 holdout; **no kernel pass@k report exists in the repo. The pre-registered headline has not been produced.**
- Self-play: built + dry-runnable; prover never fired.

### Cross-check vs uncommitted tree
No breakage — all imported APIs exist and match; only latent import risk (`vllm`) is GPU-box-only by design.

## Top 3 remediations

1. **Close the wiring gap at the cert chokepoint, not the exporter.** The transfer path should append a real cert row (`ts`, `goal_sha`, `checker` reflecting the REPL, probe-bytes sha) to `adhoc_closure_certificates.jsonl` instead of the private `self_play_corpus.jsonl` — exporter, clean-since filter, and receipt discipline then work unchanged, and the missing-receipt defect dies in the same diff. Also prepend the canonical 197-row corpus path to the seed candidates; delete the dead `pc` line.
2. **Fix the holdout before the pre-registered run.** Merge families transitively on shared custom defs; give `solo:` targets a name-stem key (resurrect the dead `_family` for that case); regenerate holdout_eval; confirm 0 cross-split def-sharing pairs and no ≥0.9-Jaccard cross-split pairs. Without this the headline CI is not defensible.
3. **Make NON-TRIVIAL real on the self-play path.** In `gate()`, splice the cheap-tactic cascade (`by first | trivial | rfl | simp_all | omega | decide | tauto | norm_num`) into the candidate and compile via the already-warm REPL (same cost as the transfer compile) instead of `default_triviality`'s blob-skipping entry; let its fail-closed raise reject rather than swallowing. Restores both the rfl-trivial and vacuous-hypothesis legs.
