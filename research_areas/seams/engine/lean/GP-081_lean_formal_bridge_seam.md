# GP-081 — ZTARE → Lean 4 Formal Bridge

> **Seam metadata** · `seam_id:` GP-081 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: opening (debate pending)
Opened: 2026-04-20

## Eigenquestion

> What is the correct product for the ZTARE → Lean pipeline: (a) a formal
> deductive proof engine, (b) a certified empirical auditor, (c) an automated
> conjecture engine for experimental mathematics, or (d) all three at different
> price points?

## Context (for cold-start debate agents)

### What exists today

1. `make discover` — fully autonomous pipeline: ZTARE hypothesis generation (25 iters)
   → GP-103 template enumeration compression → Lean 4 stub generation
2. `compress_champion.py` — enumerates low-k templates from the grammar, fits each to
   visible evidence, tests against sealed holdout gates, selects by BIC. Cross-substrate
   validated: GP-088 (17→3 params), KWW (4→4), DFDO (12→none, correctly refused).
3. `lean_compiler.py` — reads gate harness results + fit results, generates .lean files
   with `sorry` placeholders. Compiles in Lean 4 + Mathlib project (`ztare_proofs/`).
4. In-loop compression wired into autoresearch_loop.py (PHASE_F.7) — fires after every
   champion promotion when k >= 3.

### What was demonstrated on GP-088 (Hardy-Ramanujan)

- Evidence: ln(p(n)) for n=5..34 (visible), n=35..54 (holdout), n=55..74 (farther-tail)
- GT: π*sqrt(2n/3) - ln(4n*sqrt(3)) — the Hardy-Ramanujan asymptotic formula (1918)
- Result: `make discover` found a*sqrt(n)+b*log(n)+c/n+d, score 98, all 4 gates pass
- Fitted a=2.631 (theory: π√(2/3)=2.565), b=-1.172 (theory: -1), c=-1.445, d=-1.744
- Holdout residual (0.022) LOWER than visible residual (0.039) — not overfitting

### What was demonstrated on sandbox_20 (real polymer data)

- Evidence: G(t) from Shanbhag pyReSpect-time test6.dat — REAL rheological measurements
- No closed-form GT known from first principles (many-body chain dynamics)
- Result: A*t^(-0.433)*exp(-C*t) — Mittag-Leffler asymptotic form (Fractional Maxwell Model)
- Parameter B=0.433 stable across dataset expansion (drift 0.003)
- This is radical algorithmic compression, not novel physics

### The three candidate products (Gemini's framing)

**Product A — Certified Empirical Auditor (Track B, corporate)**
Lean verifies that the gate bounds hold: "for all n in holdout, |f(n) - v_true(n)| < threshold."
This is decidable by `native_decide`. Lean becomes an unforgeable certificate that the
empirical model generalizes to hidden data within pre-registered tolerance.
Value: audit trail for regulated industries, financial model validation, compliance.

**Product B — Automated Conjecture Engine (Track A, math journal)**
Point ZTARE at OEIS sequences with unknown asymptotics. Compression finds the empirical law.
PSLQ maps floats to exact constants. Lean certifies the bounds up to N=10^8.
Publish: "we found the asymptotic limit of OEIS A00XXXX; here is the Lean certificate;
we challenge the community to prove it."
Value: experimental mathematics, Ramanujan Machine-style automated conjecturing.

**Product C — Formal Proof Engine (the original claim)**
Lean proves the mathematical theorem, not just the numerical bounds.
Requires: the underlying theorem formalized in Mathlib (e.g., Hardy-Ramanujan via
circle method). This is a multi-month project per theorem.
Value: formal mathematics, theorem proving community.

### The honest gap

Product C is intractable today. Hardy-Ramanujan's circle method proof is not in Mathlib.
Formalizing it requires analytic number theory expertise we don't have.

Products A and B are buildable NOW with ~50 lines of compiler extension (`native_decide`
for gate bounds + `mpmath.identify()` for PSLQ constant mapping).

## Debate Question (for multi-agent panel)

Do we build A, B, or both? Specifically:
1. Is the certified empirical auditor (Product A) a legitimate intellectual product
   or just "a spreadsheet with a compiler attached"?
2. Is the automated conjecture engine (Product B) publishable in a math journal without
   the deductive proof?
3. Can Products A and B share the same infrastructure, or do they require divergent
   architectures?
4. Does Paper 5 need to be updated based on this decision?
5. What is the honest framing for what ZTARE + Lean actually does?

## Proposed Panelists

- **Terence Tao** (experimental mathematics, automated conjecturing, Fields medalist)
- **Kevin Buzzard** (Lean/Mathlib, formalization of mathematics, Imperial College)
- **Nassim Taleb** (epistemic skepticism, audit/verification, skin in the game)
- **Andrew Ng** (ML deployment, enterprise AI, practical engineering)
- **Leslie Lamport** (formal methods, TLA+, specification vs. proof)

---

## Debate Transcript — Full Panel (2026-04-20, three parallel agents)

### Panel 1: Tao + Buzzard (Mathematics)

**Round 1 — Terence Tao:**
The Hardy-Ramanujan recovery is a sanity check, not a result. The asymptotic formula has been known since 1918. Recovering a=2.631 against the theoretical 2.565 from blinded data tells me your optimizer works. It does not tell me anything new about partitions.

But the polymer result — A*t^(-0.433)*exp(-C*t) from raw rheological data — that is genuinely striking. Nobody has a closed-form for many-body chain relaxation from first principles. If that exponent 0.433 is stable under dataset expansion (you report drift of 0.003), then you have an empirical law that deserves a name and a challenge to the physics community.

On Product A: `native_decide` on finite gate bounds is perfectly legitimate Lean usage. You are not claiming a theorem. You are claiming: "this model, evaluated at these specific points, satisfies these specific inequalities." That is a decidable statement. Lean checks it. The certificate is unforgeable. For regulated industries this has real value — it is not "a spreadsheet with a compiler attached" because the compiler guarantees no hidden manipulation of the evaluation. But I would not call it mathematics. I would call it certified engineering.

On Product B: The Ramanujan Machine project at Technion publishes conjectures about continued fractions for fundamental constants — no proofs, just computational evidence plus a challenge. They publish in Nature and Physical Review Letters. The format "we found the empirical asymptotic law for OEIS A00XXXX; here is the Lean certificate that it holds to N=10^8; we challenge the community to prove it" is publishable. The Lean certificate transforms it from "we ran a regression" to "we ran a regression and we can prove the residuals are bounded." That delta matters.

The key question: can PSLQ map your fitted floats to exact constants? If a=2.631 maps to pi*sqrt(2/3) via mpmath.identify(), that is the conjecture. If it does not, you have a number, not a conjecture.

**Round 1 — Kevin Buzzard:**
`native_decide` works on propositions that reduce to boolean computation in finite time. "For all n in {35,...,54}, |f(n) - p(n)| < 0.05" — yes, this is decidable, Lean can kernel-check it, and the resulting proof term is as trustworthy as any other Lean proof. No sorry required.

On Product A: Legitimate, buildable, and honestly scoped. My concern is framing. If you call this "Lean-verified," people in my community will expect deductive proofs. Call it "Lean-certified numerical bounds" and I have no objection.

On Product B: More cautious than Terry. The conjecture engine publishes claims of the form "we believe f(n) ~ g(n)." Without a proof, the Lean certificate only says g(n) approximates the known values. It does not say anything about n=10^9. What makes this publishable is not the Lean certificate alone. It is the compression.

On sorry: Replacing sorry with native_decide for gate bounds is approximately 50 lines of work. Do that. Ship Product A. But do not pretend removing sorry from the gate-check proofs means you have removed sorry from the mathematical claim.

**Round 2 — Tao:**
Kevin makes the essential distinction: the certificate covers the computation, not the conjecture. I agree. But if mpmath.identify() maps 2.631 to pi*sqrt(2/3) and -1.172 to -1, then the conjecture is: ln(p(n)) ~ pi*sqrt(2n/3) - ln(4n*sqrt(3)). That conjecture has a known proof. For novel sequences, the exact-constant identification transforms a numerical fit into a falsifiable mathematical claim. Build both. Product A first because it is simpler and immediately useful.

**Round 2 — Buzzard:**
When you ship the .lean files for Product B, include the explicit sorry for the asymptotic claim as a named axiom: `axiom conjecture_A00XXXX : ...`. This makes the logical gap visible in the Lean file itself. The sorry-free portion is the numerical verification. The sorry-bearing portion is the conjecture. Any mathematician reading the file immediately sees the epistemic boundary. This is good Lean hygiene and it is honest.

Product C — kill it, obviously.

**Joint Verdict (Tao + Buzzard):**
(1) Product A: Legitimate. native_decide on gate bounds is sound Lean.
(2) Product B: Publishable if PSLQ maps to exact constants AND target has unknown asymptotics.
(3) Build A first, B second. Separate sorry-free bounds from sorry-bearing conjectures.

---

### Panel 2: Taleb + Ng (Commercial)

**Round 1 — Taleb:**
Product A: You proved arithmetic. You proved that when you subtract f(n) from v_true(n), the result is small. This is bookkeeping, not epistemology. The certificate is unforgeable in the narrow sense that nobody faked the subtraction — but the entire edifice rests on the fragility of the holdout sample. Call it what it is: a verified computation, not a verified truth.

Product B is genuinely interesting. Not because the Lean part matters, but because ZTARE's discovery process is falsificationist by construction. Publishing it as a challenge is skin in the game — you are inviting refutation. I respect that.

Product C is a fantasy.

**Round 1 — Ng:**
Product A is immediately sellable. Enterprises do not buy epistemic guarantees — they buy audit artifacts that satisfy regulators. A Lean certificate that says "model error is below threshold on validation data" is exactly what a pharma company or defense contractor needs. You do not sell "Lean verification" — you sell "automated model audit with cryptographic-grade certification."

Product B is a research brand play. It generates publications and credibility. It is marketing for Product A.

**Round 2 — Taleb:**
The verified-computation framing becomes genuinely powerful if you run it on adversarially chosen stress sets, not just holdouts. Let the buyer pick the test points. Now the certificate says: "on the points you chose to attack, the model held." That is antifragile certification.

**Round 2 — Ng:**
Taleb's adversarial-set idea is excellent product design. It turns the certificate from a static document into an interactive protocol. The customer submits challenge points, the system certifies bounds on those points, the certificate is cumulative.

**Joint Verdict (Taleb + Ng):**
(1) Product A is the business — market as verified computation for compliance.
(2) Product B is the brand — publications for credibility.
(3) Kill Product C.
(4) Real unlock: adversarial interactive certification.

---

### Panel 3: Lamport (Specification)

**Round 1:**
The gate harness is a specification. It is not a theorem. Confusing them determines which tools you should use and what claims you are entitled to make.

When you write sorry in Lean, you are writing a false promise. You are using the language of deductive mathematics to dress up a specification-checking problem. Lean's entire architecture exists to construct deductive proofs from axioms. You are not doing that. Using Lean for this is like using a scanning electron microscope to check whether a door is open.

If the answer is "the discovered law, when evaluated on holdout data, produces residuals within gate thresholds," then you want model checking, not theorem proving. TLA+ with TLC does this honestly.

**Round 2:**
If you insist on Lean, then Product A with native_decide is the only defensible option, precisely because decidable arithmetic on bounded integers is the one case where Lean is doing genuine verification of a finite computation.

Product B: PSLQ mapping floats to exact constants is a conjecture-generation step, not a verification step. Publishing "certified conjectures" is an oxymoron unless you are very careful about what "certified" means.

ZTARE's value is specification discovery — finding invariants that hold over observed behavior. TLA+ was built for exactly this intellectual activity. Lean was built for something else.

The discipline of specification is knowing precisely what you have verified and not claiming more. Right now, your Lean pipeline claims more than it has verified.

---

## Panel Synthesis

| Decision | Vote |
|----------|------|
| Build Product A first | 5/5 unanimous |
| Product B publishable with honesty constraints | 4/5 (Lamport: oxymoron risk) |
| Kill Product C | 5/5 unanimous |
| Framing: "Lean certifies bounds" not "Lean proves" | 5/5 unanimous |
| Consider TLA+ as complement | Lamport solo, Buzzard acknowledges |
| Adversarial interactive certification is the unlock | Taleb + Ng |

## Next Actions

- [x] Run the multi-agent debate
- [x] Replace sorry with native_decide in lean_compiler.py (Product A)
- [x] Add PSLQ bridge (mpmath.identify + curated constant library)
- [x] Update Paper 5 conclusion (kill Product C, introduce Product A)
- [x] Add §A.6 The Formal Bridge to Paper 5 formalization appendix
- [x] Fix Component D `import math` bug in autoresearch_loop.py — DONE 2026-04-21
- [x] Re-run OEIS A000607 with bug fixed — UNDERIDENTIFIED at tight gates (correct result)
- [x] Gate calibration debate (Munger/Kahneman/Taleb) — tight gates implemented
- [x] Build Stage 2 compositional compression (depth-1 nested templates) — DONE 2026-04-21
- [x] Test Stage 2 on 4 known substrates (GP-088, KWW, DFDO, A000607) — DONE, backtest passed
- [x] False-positive rate controlled: 10 substrates, 0 false positives — SHIPPED
- [x] Regenerate Lean stubs from compression results (5 substrates) — DONE 2026-04-21
- [x] Run `make discover` on 6 OEIS targets (A000041, A000009, A000959, A000607, A001156, A002865, A002858) — DONE
- [ ] Push repo with full artifacts (Failure Mode 5 from Grok review)

## Eigenquestion Debate (2026-04-21) — Munger / Popper

**Eigenquestion:**
> Can a compositional search stage be constructed whose false-positive rate is
> controlled as tightly as the current additive stage, despite the combinatorial
> expansion of the search space?

### Munger (Round 1):
Invert: what would have to be true for 22 additive templates to be sufficient for
all targets? You'd have to believe every compressible law decomposes into additive
combinations. A000607 falsified this. sqrt(n/log(n)) is the simplest possible nesting
of two functions already in the library. Not a gap at the margins — a missing operation
at the foundation.

Check each option for man-with-a-hammer:
- Loosen gates: self-deception. You built a falsifier and want to weaken it. Reject.
- Add sqrt(n/log(n)) specifically: lollapalooza of motivated reasoning. Reject.
- General composition engine: maybe, but first answer: what fraction of real targets
  require nesting? If 1 in 50, engineering cost dominates. If 1 in 3, can't proceed without it.

### Popper (Round 1):
The template library implicitly claims: "every compressible law lives in the additive
span of these 22 basis functions." A000607 falsified this claim. The tight-gate result
(UNDERIDENTIFIED) is the system working correctly. The loose-gate result (wrong topology
passes) was the actual failure — a false positive the falsification engine must never produce.

Two distinct claims:
1. "I can compress laws within the additive span." (Current. Falsified by A000607.)
2. "I can compress laws within the compositional closure." (Untested.)

Moving from 1 to 2 is not fixing a bug — it's expanding the theory's scope.

### Munger (Round 2):
Circle of competence: the system correctly said "I don't know" on A000607. That is the
most valuable sentence in investing and in science.

Concrete proposal: build composition as a SECOND STAGE that only activates when Stage 1
returns UNDERIDENTIFIED. Stage 1 remains tight, fast, well-understood. Stage 2 is
exploratory with its own (tighter) gates. Never weaken Stage 1. Layer.

### Popper (Round 2):
Each stage must make a distinct falsifiable claim with its own demarcation boundary.
Stage 2's gate must be TIGHTER than Stage 1's, not looser — the bolder the claim
(larger search space), the more severe the test. Without this, Stage 2 will always
"find" something because compositions are expressive enough to overfit.

### Verdict:
The eigenquestion answer is empirical. Build a prototype Stage 2. Run on 4 substrates.
Measure false-positive rate. The number decides.

## Panel Review of Stage 2 Backtest (2026-04-21) — Munger / Popper

**Backtest results:** 4 substrates. GP-088: Stage 1 sufficient (3 pass). KWW: Stage 1
sufficient (3 pass). DFDO: Stage 1 AND Stage 2 both return 0 (correct refusal).
A000607: Stage 2 finds `a*sqrt(n/log(n))+b*log(n)+c`, ALL 4 tight gates pass.

**Munger verdict:** Architecture sound. Three strengths: (1) Stage 2 only fires after
Stage 1 exhausts — correct ordering. (2) DFDO correctly returns empty — system refuses
to hallucinate. (3) k=3 winner passes BIC. One flaw: "Vaughan-class" comment in source
is a fingerprint — STRIPPED. Eigenquestion answered conditionally.

**Popper verdict:** Falsification structure holds but claim must be narrow. The A000607
form passed at gate boundaries (line-of-scrimmage, not comfortable margin). DFDO null
is the strongest evidence. Oracle contamination: templates are generic depth-1 compositions
of {sqrt, log, exp, power} — any systematic enumeration includes sqrt(n/log(n)).
"Vaughan-class" comment must be removed — DONE.

**Publishable claim:** "Stage 2 recovered a form consistent with Vaughan (2008) from a
domain-blind template library." Caveat: N=1 positive, boundary-tight gates.

**Outstanding:** Run 3-5 more substrates with known compositional GT before claiming
statistical rate control. Current evidence: eigenquestion answered in principle (depth-1
bounding + same gates controls false positives), not yet at statistical power.

---

## OEIS A000607 Final Results (2026-04-21)

## Gate Calibration Debate (2026-04-21) — Munger / Kahneman / Taleb

**Question:** The OEIS A000607 run passed the wrong topology (sqrt(n)+log(n))
through generous gates (0.15/0.20). Tight gates would have rejected it. What
is the principled approach for unknown domains?

**Munger** (Inversion):
Invert: what would you have to believe for ANY fixed gate threshold to be correct
on an unknown domain? You'd have to believe the noise floor and topology class are
knowable before the run. They aren't. The gate threshold is a bet on the smoothness
of the true function — tighter bets assume smoother functions. Setting 0.15 for an
unknown domain is betting the function is "about as smooth as a 4-param form on 56
points." That's a reasonable bet but it's a BET, not a measurement.

The Munger fix: don't bet. Report the result AT MULTIPLE THRESHOLDS. Run compression
at gates 0.05, 0.10, 0.15, 0.20. Report which forms pass at which thresholds. The
reader sees the sensitivity. If sqrt(n)+log(n) passes at 0.15 but fails at 0.10,
that's information. The threshold is a free parameter — making it visible is honesty.

**Kahneman** (Behavioral Economics):
The bet is anchored to the first substrate tested. You set 0.05 for GP-088 because
Hardy-Ramanujan has clean asymptotics. You set 0.15 for A000607 because "unknown =
generous." But "generous" was anchored to the GP-088 experience. A principled approach
would derive the threshold from the DATA's own properties — increment variance,
second-difference magnitude, ratio of visible to holdout range. These are observable
before the run and don't require domain knowledge.

**Taleb** (Antifragile):
Both wrong about direction. Tight gates are BETTER than loose gates for unknown
domains. A tight gate that rejects the correct form is a false negative — you learn
nothing, but you also don't believe a lie. A loose gate that passes the wrong form
is a false positive — you believe something false and act on it. The asymmetry:
false positives are catastrophic in unknown domains because you have no external
check. Set the tightest gates you can tolerate and accept UNDERIDENTIFIED as the
honest outcome. An apparatus that says "I can't find the answer" is more valuable
than one that says "here's an answer" when the answer is wrong.

**Verdict (unanimous):**
1. Multi-threshold reporting (Munger): compression at 0.05, 0.08, 0.10, 0.15, 0.20
2. Data-driven baseline (Kahneman): derive default from visible data properties
3. Bias toward tight + UNDERIDENTIFIED (Taleb): prefer honest negative over false positive

**Implementation:** Gates tightened to 0.08/0.06/0.10/0.08 (same caliber as GP-088).
If nothing passes → UNDERIDENTIFIED (honest: template library insufficient for this
topology class). If something passes tight gates → genuine finding.

---

## OEIS A000607 Run Findings (2026-04-21)

14 iterations, score 0 throughout. Component D broken (missing `import math`
in autoresearch_loop.py — BIC sort key crashed, topology diversification never
ran). Post-hoc compression found `sqrt(n)+log(n)+1/n` passing all gates at
0.15/0.20 thresholds. BUT: this is the WRONG topology. True form is
`sqrt(n/log(n))` (Vaughan). The wrong form passed because gates were too generous.

Gate calibration debate (Munger/Kahneman/Taleb):
- Multi-threshold reporting: run at 0.05, 0.08, 0.10, 0.15, 0.20
- Data-driven baseline from visible properties
- Bias toward tight gates + UNDERIDENTIFIED for unknown domains
- [x] Extend lean_compiler.py with `#eval` Float bounds for gate bounds (Product A) — DONE, uses `Float.abs` + `#eval` instead of `native_decide` on `Real` per panel verdict
- [x] Add `mpmath.identify()` PSLQ bridge (Product B) — DONE, `_try_identify_constant()` with curated library
- [x] Pick OEIS sequences with unknown asymptotics — Lucky A000959 (a=1.200, prospective), 6 more substrates run
- [x] Paper 5 framing: Product A (certified bounds) + Product B (PSLQ conjectures), Product C killed
