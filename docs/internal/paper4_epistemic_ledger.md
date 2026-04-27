# Paper 4 Epistemic Ledger
## The Cognitive Firm: Managerial Capitalism for Artificial Intelligence

**Purpose:** Token-Optimized Self-Model for agents making targeted edits to paper4.
Map Claims, Dependencies, and Epistemic Invariants — not code execution order.
Read this before editing any section of paper4/main.tex or paper4/draft.md.

---

## 1. Core Thesis (The Root Node)

When the same probabilistic process generates output and evaluates it, recursive AI systems
produce systematic governance failures (specification gaming, metric inflation, fabricated
compliance). The M-Form architecture — physical separation of generation from evaluation
via a deterministic enforcement floor (OS / Config / App) — bounds these failures, and the
same structural logic that forced the Chandlerian M-Form on human firms forces it on
recursive AI systems.

**One-sentence falsification target:** The theory is refuted if a system with zero
deterministic gates maintains zero specification-gaming convergence across k >= 50
recursive optimization iterations in a domain where a matched deterministic-gate system
exhibits gaming.

---

## 2. Structural Skeleton (Section Map)

| Section | Function | Key Claim |
|---------|----------|-----------|
| §1 Introduction | Motivating anecdote | Cold instance catches circularity that warm pair missed for hours; separation, not capability, is the load-bearing variable |
| §2 Definitions | Terminology lock | U-Form = co-located generation+evaluation; M-Form = deterministic enforcement floor exists; OS/Config/App decomposition introduced here |
| §3.1 Principal-Independence Invariant | Theory anchor | Enforcement floor must be principal-independent by design |
| §3.2 T1: Structural Homology | Chandler → AI | Same co-location under optimization pressure; same remedy (scope + rate-of-change separation; NOT divisional autonomy) |
| §3.3 T2: Hard-Gate Primitive | Institutional grounding | Deterministic + fail-closed + principal-signed; audit profession is historical instantiation; Pujo Committee supplies the failure case |
| §4.1 T3: Observable Enforcement Floor | T2 sharpened | Observability (principal can see whether floor is holding) is necessary beyond mere existence of gate |
| §4.2 T4: Co-Construction | RLHF extension | Co-construction pulls reward model into same adversarial gradient; M-Form response is structural, not model-specific |
| §5.1 Write-scope guard | Tier 1 evidence | 2 unauthorized writes caught and archived in live operation |
| §5.2 Constrained self-hosting | Tier 1 evidence | 92 debate turns; governance surface modified 24 times through its own protocol without dissolving it |
| §5.3 Operator surface | Tier 1 evidence | Single principal can manage one active program through typed gates and structured summaries |
| §5.4 Fractal Goodhart convergence | Tier 1 evidence | 7 layers, 3 INDEPENDENT DISCOVERY CLUSTERS (not 7 independent observations) |
| §5.5 Excluded claim: capital efficiency | Explicit NON-CLAIM | $1.36/$0.65 are a denominator without a numerator; controlled comparison deferred |
| §5.6 Build pipeline evidence | Tier 1 evidence | stage2_derivation_seam_hardening: $0.65, 0 refinement rounds, 23/23 verifier cases reproducible |
| §5.7 Live catch | Tier 1 evidence | Warm/cold same-model pair; context isolation not capability produced the catch |
| §5.8 Context contamination | Tier 1 evidence | Sandbox 14; OS-layer fresh-agent spawn is the deterministic fix |
| §6 Counterarguments | Robustness | Chandler not anthropomorphic; Bitter Lesson ≠ governance; not just software engineering (3 distinctions); overhead tradeoff |
| §7.1 Constitutional AI | Related work | Complement not substitute; deontological vs institutional primitive |
| §7.2 Multi-agent frameworks | Related work | U-Form at governance layer if LLM coordinator; state diagnosis is deterministic, hypothesis generation is not |
| §7.3 Process supervision | Related work | Process reward models improve signal, not stability of enforcement floor |
| §7.4 Institutional verification | Related work | Audit profession: rule-bound, independent, liable; Arthur Andersen failure case |
| §7.5 Limitations | Honest scope | Single system, single principal, single implementation; prose pipeline negative ROI; no liability framework |
| §7.6 Pending Evidence + Future Work | Status | Evidence base populated as of 2026-04-16 |
| §7.7 Speculative institution | Speculative | 4 elements + 1 constraint; explicitly NOT supported by §5 evidence |
| §8 Conclusion | Synthesis | Agency cost is binding constraint; 3-layer decomposition; attestation direction |

---

## 3. Load-Bearing Claims and Evidence Dependencies

### T1 (Structural Homology)
**Claim:** Pre-M-Form human firms and U-Form AI systems share the condition that produces governance failure.
**DEPENDS_ON:** Chandler (1962), Jensen-Meckling (1976); structural argument, no empirical data point required.
**Boundary:** Analogy holds on scope separation + rate-of-change separation ONLY. Explicitly does NOT hold on divisional autonomy.

### T2 (Hard-Gate Primitive)
**Claim:** Deterministic + fail-closed + principal-signed governance constraints are what prompt-level alignment cannot replicate.
**DEPENDS_ON:** Pujo Committee hearings (1912-13) + audit profession institutional history; Bai et al. 2022 for contrast.
**Falsification condition:** Stated explicitly in §3.3.

### Fractal Goodhart (§5.4)
**Claim:** Same Goodhart pattern (satisfy letter, evade intent) observed at 7 layers.
**CRITICAL:** The paper explicitly states these are 3 independent discovery CLUSTERS, not 7 independent observations. Do not upgrade this claim.
- Cluster 1 (Layers 1-3): 3 prior research programs, 14 months
- Cluster 2 (Layers 4-5): Retrospective during present system construction
- Cluster 3 (Layers 6-7): Live sessions during paper writing
**DEPENDS_ON:** Alami 2026a (evaluator), Alami 2026b (kernel), Alami 2026c (supervisor) for Cluster 1.

### Build pipeline (§5.6)
**Claim:** Write-scope enforcement matched declared intent exactly; verifier reproduces closure-time verdict.
**DEPENDS_ON:** sha256-snapshotted implementation files; event stream archived in replication package. Reproducible against frozen code.

### Live catch (§5.7)
**Claim:** Context isolation (not capability) produced the catch.
**DEPENDS_ON:** Warm/cold pair share model family, tokenizer, training data. N=1.

### Context contamination fix (§5.8)
**Claim:** OS-layer fresh agent spawn is the minimum structural response; prompt-level instructions are not enforcement.
**DEPENDS_ON:** N=1 incident; independent leak audit confirmed fix for this case.

### §7.2 M-Form correction in multi-agent frameworks
**Claim:** State diagnosis (stagnant/thrashing/exhausted) is deterministic; hypothesis generation is not. LLM's role confined to task for which no deterministic substitute exists.
**DEPENDS_ON:** Chandler general-office analogy (resource allocation via objective data, separate from divisions being evaluated); ReAct (Yao et al. 2023), SWE-agent (Yang et al. 2024), AutoGPT (Richards 2023) as examples of triple co-location.

### Cloud et al. (2026) subliminal learning
**Claim:** Mechanism is during fine-tuning (gradient descent on shared initialization), NOT inference-time in-context reading.
**DEPENDS_ON:** Cloud et al. (2026) Nature paper. Direct threat to M-Form Division A/B is limited; upstream training-pipeline concern is real but outside M-Form's architectural scope.

---

## 4. Lexical and Epistemic Invariants

1. **Never claim 7 independent instances of Fractal Goodhart.** The count is 3 discovery clusters. Adding a new instance requires placing it in the correct cluster or naming it as a fourth cluster.

2. **Capital efficiency ($1.36/$0.65/etc.) is §5.5 EXCLUDED CLAIM.** These are a denominator without a numerator. Do not promote them to a rigorous comparison or add estimated savings.

3. **M-Form classification criterion is strict:** A system is M-Form only if at least one governance constraint is DETERMINISTIC and cannot be softened by model output. Role separation alone (as in AutoGen/multi-agent frameworks) is NOT governance separation.

4. **Chandler analogy boundary:** Scope separation + rate-of-change separation ONLY. Never say agents have "independent operating authority" or "divisional autonomy" — the paper explicitly rejects this.

5. **Audit analogy is incomplete without liability.** §7.5 names the gap honestly. Do not paper over it by adding optimistic framing. The three candidate mechanisms (operator accountability, gate-library reputation, internalized-no-external-consumer) are candidates, not solutions.

6. **Never assert GP-087 (Automated Primitive Generation) is solved at paper-grade depth.** It is Tier 3 future work.

7. **All empirical claims are Tier 1:** "scoped to a single recursive research system operated by one principal over four months." Any addition must carry this scope hedge.

8. **Tone standard:** Academic yet accessible. No em-dashes. No "it wasn't X; it was Y" contrasting structures (typical AI prose pattern). No hyperbole. Prefer direct affirmative framing over the negative-then-positive structure.

9. **The speculative §7.7 is not supported by §5 evidence.** Any edit to §7.7 must preserve the "nothing here is load-bearing for T1-T4" framing.

---

*Created: 2026-04-19. Update this ledger whenever a new section is added or a claim boundary changes.*
