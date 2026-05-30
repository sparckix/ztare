# GP-117 — Why Does the Pipeline Kill But Never Discover?

> **Seam metadata** · `seam_id:` GP-117 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: answered (two panel rounds)

*All panelist names are fictitious personas used as adversarial reasoning
lenses, not real individuals or endorsements.*
Opened: 2026-04-22

*All panelist names are fictitious personas used as adversarial reasoning
lenses, not real individuals or endorsements.*

## Eigenquestion

> The apparatus has run on 12 substrates. It confirmed known results,
> measured boundaries, and killed 5 false claims. It has never produced
> a result where a mathematician said "I didn't know that." Why?

## Panel Verdict (Munger / Popper / VC, 2026-04-22)

### Q1: Fundamental limitation or wrong targets?

70% target selection, 30% grammar ceiling. The 12 substrates all have
known or conjectured asymptotics. The apparatus confirms because the
answers exist in the literature and the templates contain them. The
grammar ceiling (41 pre-authored templates) means the apparatus cannot
discover forms it cannot express. Both are addressable.

### Q2: Lucky log-quadratic — discovery or careful regression?

Methodology, not mathematics. The stabilized parameters are a real
measurement, but "the finite-n correction to a known asymptotic, which
any sufficiently careful regression would find" is exactly right. The
apparatus provided the discipline to find it reliably. The probability
DAG (Node D at p=0.52) is the apparatus itself saying "I cannot
distinguish this from careful regression."

### Q3: What targets would produce genuine discovery?

Three specific classes:
1. OEIS sequences where the entry says "No formula known" and the
   growth rate is empirically accessible
2. Experimental physics where two groups disagree on the functional
   form (the apparatus adjudicates)
3. Emergent scaling in systems with no theoretical prediction
   (biological allometry, network growth, materials science)

Additionally: choose targets where the apparatus's NEGATIVE result
("no template passes") is itself publishable. Where the community
believes a simple form should exist and the apparatus proves it doesn't.

### Q4: Is epistemic insurance viable?

The product is not "an apparatus that never discovers." The product is
"structured epistemic audit with calibrated confidence decomposition."
The probability DAG (score 87, but Node D at p=0.52) is the product.
No existing tool produces this decomposition.

TAM for "prevents false mathematical discoveries": tiny.
TAM for "auditable decomposed confidence assessments for any
quantitative claim": enormous (pharma, finance, materials, AI labs).

The inability to discover is a FEATURE in the audit framing: an audit
that discovers has lost its independence.

## Operator Correction: The Panel Missed the Recursive Loop

The panel evaluated ZTARE as a static apparatus: templates in, results
out. They missed what was built in this session:

GP-112 detects margin problems → GP-113 feeds diagnosis to the LLM →
LLM proposes novel forms OUTSIDE the grammar → gates verify →
GP-115 promotes surviving forms into the template library permanently →
observable rotation tries new representations when the grammar exhausts →
the grammar GROWS from its own failures.

The Lucky shifted reciprocal was DISCOVERED by this loop and is now a
permanent template (42nd). The grammar expanded through the apparatus's
own operation, not through operator judgment. An auditor doesn't change
what it looks for based on what it found. This loop does.

The DAGs are the mechanism: Node D at p=0.52 doesn't just say "we're
not sure." It says "here is the specific assumption that is decisive
and unverified." That diagnosis IS the input to GP-113. The DAG tells
the LLM exactly WHERE the current best form is weak. The LLM proposes
a fix. The gates verify. The grammar expands.

**Revised claim:** The apparatus is BOTH an auditor AND a discovery
engine. The discovery mechanism is not template enumeration (Phase 2).
It is the recursive loop: audit → diagnose → propose → verify → promote.
The loop has one live demonstration (Lucky 500K, score 0 → 77). It needs
more demonstrations before the claim is general.

## Implication for the project

Three products, not two:
1. **ZTARE as Auditor** — the probability DAG, the margin-of-safety
   gate, the validity horizon detector. Product ready now.
2. **ZTARE as Recursive Discovery Engine** — the GP-112 → GP-113 →
   GP-115 loop. One live demonstration. Needs more substrates.
3. **ZTARE as Architecture Probe** (GP-116) — compress transformer
   observables (effective rank, attention entropy, spectral structure)
   to measure where the transformer is wasteful.

The methodology IS the product. The findings are evidence the
methodology works.

## Panel Round 2: Re-evaluation with the Loop (2026-04-22)

The operator resubmitted, challenging the panel to evaluate the
recursive loop, not the static apparatus.

**Munger:** "I was wrong about the static verdict. The loop is real
architecture. But your own experiment record tags the sole demonstration
CAUSAL_CLAIM_UNCONTROLLED. Your apparatus is more honest than your prompt."

**Popper:** "A system that changes its hypothesis space based on
falsification is a progressive research program. I was wrong to dismiss
the recursive capacity. But one demonstration is not a test."

**VC:** "I was wrong to call it only a verification engine. The DAG
feeding Node D weakness into the LLM prompt is a product differentiator
no competitor has. But 40 templates and one uncontrolled demonstration
do not justify 'discovery engine' in any investor-facing document."

**Three overclaims corrected:**
1. Template count is 40, not 42 (verified by grep)
2. A001156 and A002865 rotation results were inline-only (artifacts
   now saved via post_underidentified.py)
3. Causal attribution of GP-113 remains uncontrolled (per our own
   experiment record)

**Strongest defensible claim (panel consensus):**
"ZTARE is an epistemic audit engine with a demonstrated grammar-expansion
loop. The audit product (probability DAG, margin-of-safety gate, validity
horizon) is defensible now. The recursive discovery claim is an existence
proof with one uncontrolled demonstration. It needs controlled replication
on genuinely unknown targets."

## Reflexive Primitive

This seam documents the same failure pattern at the META level: the
operator (and the agent) overclaimed the loop's capability before the
evidence supported it. The panel caught the overclaim. This is the
apparatus's own methodology (adversarial review → correction) applied
to the apparatus's own claims about itself. The fractal Goodhart
prediction (the same pattern recurs at every layer) is confirmed again:
the apparatus that catches LLM gaming was caught gaming its own
capabilities by its own adversarial review panel.

## Update: GP-116 Evidence (2026-04-22)

GP-116 (transformer architecture probe) produced 6 insights
(INS-036 through INS-041). Of these, the apparatus (`make discover`)
produced TWO:
- sqrt(log) compression of residual magnitude decay (gates pass, BIC=-80.5)
- Score 88 champion thesis with constraint injection (GP-113 feedback)

The other four (BOS contamination, orthogonal residuals, cancellation
invariant, SSMs-learn-alignment) were produced by OPERATOR-DIRECTED
EXPLORATION using ZTARE's measurement tools as instruments, not by
the automated loop. The operator's inversions ("what if BOS is the
problem?", "run the null model", "test Mamba") drove the discoveries.
The apparatus provided infrastructure (SVD extraction, residual
decomposition, cross-architecture diagnostic suite) but not the
hypotheses.

### Revised Assessment

The automated loop has THREE demonstrations, not six:
1. Lucky shifted reciprocal (GP-115 grammar expansion)
2. sqrt(log) residual magnitude decay (GP-116 compression)
3. Score 88 champion with constraint injection (GP-113 feedback)

The headline findings (BOS artifact, cancellation invariant, SSM
alignment asymmetry) came from the HUMAN operating the apparatus,
not from the apparatus operating itself. This is consistent with
the Kepler/Newton framework: ZTARE is Kepler (discovers functional
forms from data). Newton (the mechanism, the inversion, the "why")
requires the operator.

### Implication for Product #3 (Architecture Probe)

GP-116 demonstrates that ZTARE's measurement tools (residual
decomposition, null model comparison, cross-architecture diagnostics)
are powerful instruments for architecture research. But the DISCOVERY
came from the human-agent conversation loop, not from `make discover`.
The product is: "ZTARE as a measurement instrument for architecture
research, operated by a domain expert." Not: "ZTARE autonomously
discovers architectural laws."

This is the honest framing. An auditor that discovers has lost its
independence — but an instrument that measures precisely is valuable
regardless of who points it.
