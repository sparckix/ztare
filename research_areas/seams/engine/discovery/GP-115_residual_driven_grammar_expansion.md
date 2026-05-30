# GP-115 — Residual-Driven Grammar Expansion

> **Seam metadata** · `seam_id:` GP-115 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: opening
Opened: 2026-04-22

## Eigenquestion

> Can the apparatus expand its own grammar from residual structure without
> operator judgment, and if so, for which class of expansions?

## Architecture (from Munger/Number Theorist panel, 2026-04-22)

Three layers, each with a different automation boundary:

### Layer 1: Mechanical (automatable now)

Residual signatures that map deterministically to missing templates:

| Residual signal | Missing template | Detection |
|-----------------|-----------------|-----------|
| 1/n envelope in residuals | reciprocal term `b/n` | amplitude ~ 1/n |
| log-periodic structure | log-power `a*log(n)^b` | Lomb-Scargle on log(n) |
| Monotone-decaying curvature | shifted reciprocal `b/(n+c)` | sign-change analysis |
| Smooth trend in coefficient drift | log^2 correction `e*log(n)^2` | moving-window coefficient slope |

These are pattern-matched, not judgment-based. The residual structure IS
the specification for the missing template.

### Layer 2: LLM-mediated (GP-113)

When Layer 1 finds no match, the diagnosis feeds into the LLM (GP-113).
The LLM proposes forms outside the grammar using structural analogy.
The form passes gates, then earns permanent template status after
confirmation on 3+ substrates.

### Layer 3: Operator judgment (acknowledged boundary)

Domain-specific structural intuitions (sigmoidal saturation for biology,
dimensional constraints for physics) that no residual analyzer can derive.
This is the honest boundary of automation.

## Implementation: Layer 1

```python
# src/ztare/fit/residual_grammar_expander.py

def suggest_templates_from_residuals(
    residuals: np.ndarray,
    x_values: np.ndarray,
    var: str = "n",
) -> list[tuple[str, str, list[str]]]:
    """Analyze residual structure and suggest missing templates.

    Returns a list of (name, expression, param_names) tuples
    in the same format as compress_champion templates.
    """
    suggestions = []

    # 1. Check for 1/n envelope
    if _has_reciprocal_envelope(residuals, x_values):
        suggestions.append(("auto_reciprocal",
            f"a / {var} + b", ["a", "b"]))

    # 2. Check for shifted reciprocal (monotone decay with offset)
    if _has_shifted_reciprocal(residuals, x_values):
        suggestions.append(("auto_shifted_recip",
            f"a / ({var} + b) + c", ["a", "b", "c"]))

    # 3. Check for log-quadratic curvature
    if _has_log_quadratic(residuals, x_values):
        suggestions.append(("auto_log_squared",
            f"a * math.log({var})**2 + b", ["a", "b"]))

    # 4. Check for exponential decay in residuals
    if _has_exp_decay(residuals, x_values):
        suggestions.append(("auto_exp_correction",
            f"a * math.exp(-b * {var}) + c", ["a", "b", "c"]))

    return suggestions
```

## Integration into GP-112

After PERSIST_GRAMMAR_EXHAUSTED and before Phase 2.6 (residual characterization),
Layer 1 analyzes the residuals and suggests templates. These suggested templates
are tried as additional extensions in the remediation loop. If any passes, it
becomes a candidate for permanent template promotion.

## Promotion protocol

A template suggested by Layer 1 or Layer 2 becomes permanent when:
1. It passes holdout gates on the originating substrate
2. It passes regression test on 3+ prior substrates (no false positives)
3. It improves BIC on at least 1 of those substrates

The shifted reciprocal `c/(n+d)` earned permanent status via this protocol
(GP-113 proposed, regression-tested on GP-088, added 2026-04-22).

## Named Grammar Gaps (data-driven, not overfitting)

A grammar gap is "named" when: (1) the residual diagnostic identifies the
missing structural class, (2) the extension would be tested by the same
holdout gates and BIC penalty as any other template, (3) the gap was
discovered from data, not from operator domain knowledge.

| Gap | Discovered from | Status | Overfitting risk |
|-----|-----------------|--------|------------------|
| loglog additive | Lucky 500K coefficient drift | SHIPPED (4 templates added) | Low (BIC at k=3-4) |
| log-power free | Lucky 500K coefficient drift | SHIPPED | Low (BIC at k=3-4) |
| shifted reciprocal c/(n+d) | GP-113 LLM proposal on Lucky | SHIPPED (regression-tested) | Low (k=4) |
| multi-harmonic sin/cos | Ulam Stage 3 periodicity detection | NAMED, NOT IMPLEMENTED | HIGH (k=8-12, panel: don't add) |
| parabolic a*(n-b)^2+c | GP-116 rank curve U-shape | SHIPPED (template added) | Low (k=3) |
| **sigmoid-switched two-regime combinator** | GP-116 rank curve asymmetry | PANEL APPROVED, NOT IMPLEMENTED | Medium (panel: grid search over b, compose any pair from 41 templates) |

Panel debate completed (Fourier/Rademacher/Ramanujan/Munger, 2026-04-22):

Verdict: option (c) — targeted fit with FFT-fixed frequencies, NOT
a permanent grammar addition. Fix frequencies from FFT peaks, fit only
amplitudes and phases (k=5 per harmonic pair). Sequential BIC-delta > 10
required per harmonic.

Implementation result on Ulam (770K checkpoint):
- 1-harmonic (k=6, freq fixed from Lomb-Scargle): holdout 0.124 FAIL
- 2-harmonic (k=8, freqs fixed): holdout 0.101 FAIL, BIC-delta 570 (justified)
- Even with 2 justified harmonics, the model fails holdout by 2x

Conclusion: the Ulam density fluctuation remains UNDERIDENTIFIED.
The periodic signal is real but the modeling tools are insufficient.
The apparatus correctly reports both the detection and the failure.
Multi-harmonic templates are NOT added to the permanent grammar per Munger:
"the grammar should not grow to model every signal the validator detects."

**Default grammar policy (2026-04-22):** The compressor uses `math_exp_only`
templates for all substrates regardless of the rubric grammar. Trig templates
are injected ONLY when Stage 3 detects periodicity from the data. This
removes the operator from the grammar decision for unknown domains. The
grammar expands from the data, not from the operator's prior knowledge.

## Panel Transcript: Multi-Harmonic Grammar Expansion (2026-04-22)

*Panelists are fictitious personas used as adversarial reasoning lenses,
not real individuals. The names evoke intellectual traditions, not endorsements.*

**Panel:** Fourier (spectral analysis), Rademacher (analytic number theory),
Ramanujan (pattern recognition), Munger (overfitting guard).

**Q1 (BIC sufficient at k=7-11?):**
- Fourier: BIC adequate at n=5000 but multi-harmonic is combinatorially
  dangerous — any pair of frequencies absorbs structured residuals. Require
  Lomb-Scargle detection to precede and justify each harmonic independently.
- Rademacher: the real risk is not statistical but semantic — quasi-periodic
  signals in number theory arise from multiplicative interference. Fitting
  sinusoids captures a shadow, not a law. Will pass BIC and mean nothing
  outside the fitting window.

**Q2 (How to constrain harmonics?):**
- Ramanujan: integer-multiple constraint is unmotivated for Ulam (competing
  additive constraints produce incommensurate frequencies). Use sequential
  fitting: dominant frequency first, second only if residual shows a second
  significant peak.
- Fourier: sequential BIC-delta gating — each harmonic must improve BIC
  by at least 10 (Kass-Raftery decisive evidence). Self-pruning, no
  operator choice of 2 vs 3.

**Q3 (Free vs fixed frequencies?):**
- Fourier: fix from FFT peaks. Reduces 2-harmonic from k=7 (nonlinear) to
  k=5 (linear in amplitudes). Free-frequency fitting is a convergence trap
  that finds aliased solutions.
- Rademacher: fixed frequencies are the only defensible choice. Free
  frequencies will absorb finite-sample artifacts.

**Q4 (Man-with-a-hammer?):**
- Munger: option (b) is honest, (c) is pragmatic, (a) is the hammer. The
  apparatus found something real. Report the detection. If you want a
  targeted fit, use FFT-fixed frequencies as a one-off investigation. Do NOT
  add multi-harmonic templates permanently. "The grammar should not grow to
  model every signal the validator detects; the validator's job is detection,
  not compression."

**Consensus:** Option (c) with guardrails. FFT-fixed frequencies, sequential
BIC-delta > 10, one-off investigation, NOT permanent grammar.

**Result:** 1-harmonic holdout 0.124 FAIL, 2-harmonic holdout 0.101 FAIL.
Both fail by 2x despite BIC-delta 570 justifying the second harmonic.
Ulam remains UNDERIDENTIFIED. Detection + modeling gap reported as finding.

## Cross-Substrate Accumulation (Torvalds/Knuth/Karpathy pattern)

The grammar should grow the way Linux grew: each addition earned from a
real failure, not designed in advance. The three-part pattern:

1. **Accumulate** (Karpathy wiki): every UNDERIDENTIFIED verdict writes
   its diagnostic to a cross-substrate log (`workspace/underidentified_log.jsonl`).
   The log records: substrate, residual signature, what was tried, what failed.

2. **Catalog** (Knuth): when the same residual signature (e.g., "quasi-periodic,
   single-harmonic insufficient") appears in 3+ substrates, it becomes a
   named recurring gap. The catalog is the evidence base for grammar expansion.

3. **Promote** (Torvalds): recurring gaps earn new templates. Each template
   is regression-tested on all prior substrates before becoming permanent.
   No speculative additions. No pre-designed grammar expansions.

This replaces the operator's role in grammar expansion for mechanical gaps.
The operator remains essential for structural gaps that require domain
judgment (Layer 3).

**Not yet implemented.** The promotion protocol exists (3+ substrates confirms).
The cross-substrate accumulation log does not. The catalyst: the next
UNDERIDENTIFIED result on a new substrate with a similar residual signature
to Ulam. Until then, Ulam's quasi-periodic gap is a single data point,
not a recurring pattern.

## Relationship to other seams

- GP-112: margin of safety provides the PERSIST signal that triggers expansion
- GP-113: LLM feedback loop is Layer 2 (judgment-mediated expansion)
- GP-115 (this): Layer 1 (mechanical, residual-driven expansion)
- GP-103: the original template library and compression primitive
