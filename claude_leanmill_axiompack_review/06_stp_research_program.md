# STP-style self-play for LeanMill — literature dive, precise questions, experiment program

Research agent report (web-verified, arXiv-cited), 2026-07-17. Context: LeanMill's non-mathlib niche + AxiomPack invented theories + the validated self-play conjecturer + the pre-registered pass@k harness.

## 1. STP mechanism summary

Source: Dong & Ma, "STP: Self-play LLM Theorem Provers with Iterative Conjecturing and Proving," [arXiv:2502.00212](https://arxiv.org/abs/2502.00212) (v4 March 2025, ICML 2025; code at github.com/kfdong/STP). Full text read.

**Motivation (data scarcity).** Expert iteration on a fixed statement pool plateaus: rewards are sparse and ~98.5% of compute is spent on failing proof attempts. STP manufactures new statements at the capability frontier so reward density stays high (≥47% of its generated conjectures are provable).

**Roles.** One model, two roles. The *prover* does standard expert iteration (K=32 samples/statement). The *conjecturer* is prompted with a seed lemma extracted (by the verifier) from a verified proof, plus the seed theorem and its proof, and emits a new conjecture; 50% of the time the lemma slot is replaced by `True` to force open-ended generation.

**Difficulty-band selection (the core signal).** No literal Elo; the band is an empirical pass-rate window. A conjecture becomes conjecturer training data iff its pass rate under the current prover is in **(0, 1/4]** — "barely provable." Additional filters: the seed lemma must actually appear in the proof (relevance); an "elegancy" filter drops the bottom 20% by min-proof-length/conjecture-length ratio (kills padded statements); dedup.

**Collapse avoidance.** (1) **Wasserstein-distance reweighting** matching selected conjectures to the distribution of still-unproved statements in the human dataset (prevents topical mode collapse — the piece with no obvious analogue when there is no human dataset, which matters for LeanMill); (2) replay buffer of correct proofs from the last 3 iterations + periodic re-training from base on all accumulated correct proofs; (3) the elegancy filter.

**Loop and results.** 48 iterations in Lean (58 Isabelle), 51.3B generated tokens, 241M proofs + 3.6M conjectures. LeanWorkbook cumulative 28.5% (vs 13.2% expert-iteration best), miniF2F-test 65.0% pass@3200, ProofNet 23.9%, PutnamBench 8/644. A LeanWorkbook-only variant still hits 61.1% miniF2F — the conjecturing loop learns transferable proving skill.

## 2. Post-STP landscape (2025 → mid-2026)

| Work | ID | Mechanism | Reusable for LeanMill |
|---|---|---|---|
| Minimo (Poesia et al.) | [2407.00695](https://arxiv.org/abs/2407.00695) | Self-play from *axioms only* (prop logic, arithmetic, groups): constrained/type-directed decoding guarantees well-formed conjectures from random init; hard-but-provable moving target; MCTS + hindsight replay | Closest prior art for self-play in axiom systems; well-formedness-by-construction beats filter-after |
| AlphaProof | Nature s41586-025-09833-y (Nov 2025) | AlphaZero-style RL over ~1M autoformalized problems; Test-Time RL generates variants of the target; IMO 2024 silver | Variant-generation-at-test-time = instance_vary as inference-time curriculum |
| DeepSeek-Prover-V2 | [2504.21801](https://arxiv.org/abs/2504.21801) | Subgoal-decomposition RL; miniF2F 88.9% pass@8192 | Decomposition as a proposal op |
| Kimina-Prover | [2504.11354](https://arxiv.org/abs/2504.11354) | RL on structured formal-reasoning pattern; miniF2F ~82% | Reasoning-trace SFT format |
| Goedel-Prover-V2 | [2508.03613](https://arxiv.org/abs/2508.03613) | *Scaffolded data synthesis* (statements at intermediate difficulty by construction) + verifier-guided self-correction; miniF2F 88-90% pass@32 | Difficulty band by construction rather than measurement |
| Seed-Prover | [2507.23726](https://arxiv.org/abs/2507.23726) | Lemma-style whole-proof + deep/broad search; IMO 2025 5/6, miniF2F 99.6% | Human benchmarks near-saturated → the frontier is exactly non-mathlib/self-generated domains |
| Bourbaki | [2507.02726](https://arxiv.org/abs/2507.02726) | Self-generated goal-conditioned MDPs; MCTS over self-proposed subgoals; 26 PutnamBench at 7B | Conjecture = subgoal; cheap-model ensembling |
| Leanabell-Prover-V2 | [2507.08649](https://arxiv.org/abs/2507.08649) | Verifier-integrated RL (Lean feedback in the loop) | Typed error feedback as reward shaping |
| LeanConjecturer | [2506.22005](https://arxiv.org/abs/2506.22005) | Seed Mathlib files → LLM conjectures; gates: compiles / not-aesop-trivial / novel; survivors feed GRPO; 3,776/12,289 pass gates | Their gate stack ≈ LeanMill's novelty/well-formed/non-trivial gates — independent validation |
| State-transition generation | [2503.04772](https://arxiv.org/abs/2503.04772) | Millions of synthetic Lean theorems via state-transition graphs | Symbolic (non-LLM) conjecture mass production |
| DreamProver | [2604.26311](https://arxiv.org/abs/2604.26311) | Wake-sleep: wake proves + proposes lemmas; sleep abstracts a transferable lemma library | Sleep-phase consolidation ↔ AxiomPack conjecture book |
| TaoBench | [2603.12744](https://arxiv.org/abs/2603.12744) | Analysis-I formalized *without* Mathlib definitions; SOTA provers drop ~26% vs paired Mathlib forms | The quantitative case that the non-mathlib niche is underserved |
| Self-play theory (Chen & Li) | [2606.01861](https://arxiv.org/abs/2606.01861) | Prover-conjecturer self-play expands the provable set exponentially iff the theorem graph is well-connected; identifies "artificially complex conjecture" collapse; fix = diversity regularizer on contrastive embeddings | Theoretical justification + a concrete replacement for STP's Wasserstein anchor |
| Learnable info-gain condition | [2603.02218](https://arxiv.org/abs/2603.02218) | Self-play plateaus unless each iteration's synthetic data carries learnable information gain | Loop health/stopping criterion |
| Learning to Disprove | [2603.19514](https://arxiv.org/abs/2603.19514) | Counterexample generation in Lean 4; training data via symbolic mutation (= drop_hypothesis); multi-reward expert iteration | Prove-or-refute dual signal |
| ConjectureBench | [2510.11986](https://arxiv.org/abs/2510.11986) | Conjecturing as a distinct measured task | Evaluation hygiene for the conjecturer |
| FERMAT | [2511.14778](https://arxiv.org/abs/2511.14778) | RL environment for theory formation; interestingness measures synthesized by LLM evolutionary search | Learned interestingness vs hand-coded non-triviality |
| Equational Theories Project | [2512.07087](https://arxiv.org/abs/2512.07087); Krympa [2605.21200](https://arxiv.org/abs/2605.21200) | 4,694 magma laws, all 22,028,942 implications resolved via Lean + ATPs + finite countermodels | The at-scale template for AxiomPack's universe: implication graph + countermodel duality |
| Classic theory exploration | AM/Eurisko (Lenat); HR (Colton 2002); IsaCoSy (JAR 2011); Hipster [1405.3426](https://arxiv.org/abs/1405.3426); QuickSpec (JFP 2017) | Term generation + testing-against-models + interestingness heuristics | AxiomPack's finite-model filtering is the QuickSpec move; the lineage's failure mode (unfalsifiable "interestingness") is what kernel verification + countermodels fix |

Adjacent: [2509.14274](https://arxiv.org/abs/2509.14274) (theorem discovery with in-context proof learning), [2603.04528](https://arxiv.org/abs/2603.04528) (multi-agent concept discovery).

## 3. Precise, falsifiable research questions

**(a) Non-mathlib niche:**
- **Q1.** Does STP-style self-play (conjecturer ops + band selection) beat compute-matched pure expert iteration on family-holdout pass@k over the kernel-verified non-math corpus? Falsified if the self-play arm's delta CI does not exceed the expert-iteration arm's.
- **Q2.** Is the (0, 1/4] pass-rate band at K=32 the right difficulty signal when every statement is self-generated (no human anchor)? Falsified if band arms (0,1/8] / (0,1/4] / (1/4,1/2] are indistinguishable on downstream closure growth.
- **Q3.** STP's Wasserstein anchor needs a human pool. Does anchoring to LeanMill's *unclosed conjecture-book / open campaign targets* prevent the collapse signature of 2606.01861 (rising conjecture complexity, falling downstream pass rate)? Falsified if the unanchored arm shows no drift over N iterations.
- **Q4.** Niche premium: prediction — SOTA provers drop ≥20% (TaoBench-style) on LeanMill artifacts vs matched-difficulty mathlib controls, and in-domain self-play SFT recovers more of the gap than equal-token mathlib SFT. Falsified if mathlib SFT recovers as much.
- **Q5.** Does a cheap proof-transfer-first prover shift the optimal band? (Transfer makes "easy" ≠ "search-provable".) Falsifiable by comparing bands computed on transfer-inclusive vs search-only pass rates.

**(b) AxiomPack (self-play inside machine-invented theories):**
- **Q6.** Novelty as an empirical claim: no published system runs LLM self-play *inside machine-invented axiom systems* (Minimo: fixed human axiomatizations; FERMAT: invents concepts but no kernel-verified self-play SFT over invented theories). Falsified by a single counterexample paper; none found as of 2026-07.
- **Q7.** Does a conjecturer trained in one AxiomPack theory transfer zero-shot to a freshly invented theory of the same signature class (higher well-formed/non-trivial/provable fraction than a mathlib-trained conjecturer)?
- **Q8.** Prove-or-refute as a third signal: in finite-model universes most conjectures should be resolvable (proof or countermodel — ETP resolved all 22M implications). Prediction: refutation training (2603.19514 recipe) improves provability calibration (Brier) and cuts compute on false conjectures. Falsified if calibration doesn't move.
- **Q9.** In tiny theories, pass-rate bands saturate. Is an *independence-based* difficulty signal (load-bearing-axiom count in the proof; independence from a sub-pack witnessed by countermodel) a better curriculum signal than pass rate? Head-to-head falsifiable.
- **Q10.** Do conjectures transported along verified theory morphisms have a higher hit rate (provable ∧ non-trivial in target) than de-novo conjectures in the target theory? **The load-bearing question for the "Langlands-style" framing.**
- **Q11.** Does self-play skill from synthetic AxiomPack theories transfer back to the artifact corpus (BFT/EF1/ARC invariants) as a cross-domain pass@k lift? Falsified if the lift CI includes zero.

## 4. Novelty positioning (honest)

Every *ingredient* has named prior art:
- **Theory interpretations transporting theorems:** institutions (Goguen & Burstall 1992); IMPS "little theories" (Farmer et al., JAR 1993) — transporting theorems along interpretations was IMPS's explicit working method; MMT/OMDoc theory graphs with views (Rabe & Kohlhase, [1105.0548](https://arxiv.org/abs/1105.0548)); Isabelle locales + Transfer/Lifting; Coq isomorphism transfer ([1505.05028](https://arxiv.org/abs/1505.05028)); transport via partial Galois connections ([2303.05244](https://arxiv.org/abs/2303.05244)); Lean's `@[to_additive]`; Mizar MML.
- **Machine exploration of equational universes with countermodels:** the Equational Theories Project is the dominant prior art — AxiomPack's magma/equational finite-model universe is, bluntly, a small in-house ETP.
- **Conjecture generation with model-based filtering:** QuickSpec/Hipster/IsaCoSy did generate-filter-prove fifteen years ago; HR had interestingness + countermodels.
- **Self-play from axioms:** Minimo.

**What appears genuinely unclaimed is the composition:** (1) the system invents the axiom packs (kernel-checked independence witnesses), (2) an STP-style self-play loop conjectures and proves *inside* those invented theories with countermodel machinery as a resolve-or-reject gate, (3) theory morphisms serve as a *conjecture-generation operator and transfer-evaluation instrument* inside the loop. ETP has (2)'s substrate but human/ATP-driven, one signature; Minimo has (2)'s loop but fixed theories, no morphisms; MMT has (3)'s machinery but no learning loop.

**Caution on "Langlands-style":** theory interpretations are functorial and mechanical; Langlands is about *discovered, nonobvious* correspondences. While morphisms are operator-declared, the honest name is a "little-theories / theory-graph program," and reviewers who know that literature will say so. **The one addition that most sharpens the claim: morphism *discovery*** — LLM-proposed, kernel-verified interpretations between *independently invented* theories, with a non-triviality obligation (the interpretation must transport at least one law not already a theorem of the target, certified by the independence machinery). A discovered, verified, non-trivial interpretation between two machine-invented theories is a defensible micro-Langlands event; nothing surveyed does this.

## 5. Experiment designs (pre-registerable, using existing infrastructure)

**E1 — STP-lite on the non-math corpus (Q1, Q3).** Arms: (A) expert iteration only; (B) + all provable conjectures; (C) + band-selected (0,1/4] at K=32. Compute-matched. Primary: family-holdout pass@k delta CI vs few-shot. Secondary: collapse telemetry (conjecture complexity trend, embedding spread), anchor-to-unclosed-targets on/off sub-arm. Pre-register C > B > A.

**E2 — Difficulty-signal head-to-head (Q2, Q5, Q9).** Arms: three pass-rate bands; search-only vs transfer-inclusive pass rates; independence-based difficulty (AxiomPack arm). Metric: closure growth on a frozen unclosed target set + downstream pass@k. Indistinguishability is itself a finding.

**E3 — Prove-or-refute self-play in AxiomPack universes (Q8).** Every conjecture resolves: kernel proof or finite countermodel; unresolved past budget → logged, excluded. Train both polarities. Metrics: resolution rate (predict >90%), Brier via existing forecast_router machinery, pass@k on held-out invented theories.

**E4 — Morphism transport of conjectures (Q10).** For each verified interpretation T1→T2: transport top-n gated conjectures from T1; measure hit rate in T2 = provable ∧ non-trivial ∧ novel. Control: n de-novo conjectures in T2, matched on novelty gate. Primary: hit-rate difference CI. Secondary: "transport surprises" — transported conjectures *refuted* in T2 by countermodel; each is a falsification datum about the morphism's semantic reach, ledgered — making morphisms falsifiable instruments rather than decoration. **Requires no training.**

**E5 — Niche-premium measurement (Q4).** Matched-difficulty pairs (LeanMill artifact statements vs mathlib-native, matched by baseline pass@k). External SOTA prover + LeanMill few-shot on both; gap recovery from equal-token SFT on in-domain self-play data vs mathlib data. Pre-register ≥20% drop and larger recovery from in-domain.

## 6. Recommended first move

**Run E4 first.** Zero training — only the conjecturer, the morphism layer, and countermodel machinery. One cycle, fully pre-registerable, and it directly tests the claim that positions AxiomPack against all named prior art (morphisms as productive conjecture-transport instruments). Either outcome pays: a positive hit-rate delta seeds the novelty paper; refuted transports populate the falsification ledger that makes the "Langlands-style" framing honest. Queue E1 as the first training run (E2/E3/E5 reuse its plumbing). In parallel, prototype **morphism discovery** — the single addition converting AxiomPack from "in-house ETP + little theories" into an unclaimed research object.

Fetch caveats: Kimina-Prover and the classic theory-exploration works cited from stable knowledge + search confirmation rather than full-text fetches; Minimo difficulty-signal details from abstract/snippets.
