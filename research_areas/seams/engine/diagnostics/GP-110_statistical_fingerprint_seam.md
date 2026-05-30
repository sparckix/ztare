# GP-110 — Statistical Fingerprint Result Class

> **Seam metadata** · `seam_id:` GP-110 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: active (spec complete, implementation pending)
Opened: 2026-04-21
Motivated by: E-ULAM-A002858-01 (UNDERIDENTIFIED on fractal noise data)

## Eigenquestion

> When the compression primitive returns UNDERIDENTIFIED, can the apparatus emit
> a typed statistical characterization that is domain-general, deterministic, and
> useful to a downstream consumer?

## Prior Debate: Is the Ulam 1/f Finding Nature-Level? (2026-04-21)

### Tao (Analytic Number Theory):
Not Nature-level. Interesting observation, not a theorem. The specific claim
"Steinerberger's period 21.3 is a spectral peak of a broad 1/f spectrum, not
a single frequency" IS citable and genuinely reframes the 2015 result. But the
characterization at n=5000 is methodologically thin — the community has computed
to 10^12. Publishable in Experimental Mathematics IF replicated at n≥10^6.

### Steinerberger (Domain Expert):
ADDS to, does not contradict his 2015 work. The anti-persistence (H=0.072) is
interesting — the Ulam construction rule creates natural anti-correlation (dense
regions deplete unique-sum candidates). The "only 30% arithmetic" Ramanujan test
and the Hilbert phase nonlinearity suggest richer structure than a single
trigonometric mode, consistent with his own unpublished explorations. Verdict:
run at n=10^6 — if it holds, co-publishable.

### Mandelbrot (Fractal Geometry):
1/f noise in a PURELY DETERMINISTIC integer sequence defined by an additive
uniqueness constraint is genuinely surprising — no external noise source. Connects
additive number theory to fractal geometry with no known precedent. BUT: spectral
slope -0.94 and Hurst H=0.072 are INCONSISTENT for standard self-similar
processes (beta = 2H-1 gives -0.856, not -0.94). Either H is biased by the
short series, or the process is not self-similar. Must resolve before publication.

### Kahneman (Skeptic):
Multiple red flags: (1) 4500 points is tiny for spectral analysis. (2) Detrending
window W=21 chosen from known dominant scale — circular. (3) Hurst/slope
inconsistency. (4) Motivated reasoning — dressing up a null result. (5) Amplitude
envelope ~1/n is just convergence, not a discovery. Verdict: replicate at n=10^6
with multiple detrending windows. If it survives, interesting. If not, artifact.

### Joint Publication Assessment:
- Nature: No.
- Experimental Mathematics: Yes, IF replicated at n≥10^6.
- Most citable claim: "Steinerberger's hidden signal is a spectral mode, not a frequency."
- Novel: Yes. 1/f characterization, Hurst exponent, Hilbert phase, Ramanujan
  arithmetic decomposition of the Ulam wave are NOT in any published paper.
- Methodologically premature: Yes, at n=5000.

## Prior Debate: Cracking the Ulam Wave (2026-04-21)

### Panel (Ramanujan / Fourier / Mandelbrot):

**Ramanujan**: The oscillation has an arithmetic component — compute U(n)/n by
residue class mod 21. If wave is arithmetic, conditional densities separate cleanly.
Result: spread 0.006 at mod 21, only 30% of wave energy. Wave is NOT purely
arithmetic.

**Fourier**: Standard Fourier/Lomb-Scargle fails because the signal is non-stationary.
Use Hilbert transform for instantaneous amplitude/phase. Key insight: fit trend
and oscillation SEPARATELY (trend on moving-average smoothed signal, wave on
residual). Joint optimization entangles them.

**Mandelbrot**: Challenged single-frequency assumption. The "period 21.3" may be
dominant scale of a cascade, not the only scale. Proposed: check power spectrum
for 1/f slope (CONFIRMED: slope = -0.94). Proposed Weierstrass function for
self-similar oscillation.

## Prior Gate Calibration Debate (2026-04-21)

### Panel (Munger / Kahneman / Taleb):
- Munger: report at MULTIPLE thresholds, don't bet on one
- Kahneman: derive threshold from data properties, not domain knowledge
- Taleb: tight gates + UNDERIDENTIFIED > loose gates + false positives

## Architectural Spec: GP-110 Statistical Fingerprint

### New result type: CHARACTERIZED_BUT_UNMODELED

Sits between IDENTIFIED (formula found) and UNDERIDENTIFIED (nothing found).
Means: "I cannot write f(n), but I can describe the statistical structure."

### StatisticalFingerprint dataclass fields:
- spectral_slope (float): beta in S(f) ~ f^(-beta)
- spectral_slope_r2 (float): goodness of log-log fit
- dominant_period (float|None): if FAP < 0.01
- spectral_bandwidth (float): peak/total power ratio
- hurst_exponent (float): DFA estimate
- phase_linearity_residual (float): Hilbert phase residual (rad)
- is_quasiperiodic (bool): True if phase residual < pi
- envelope_exponent (float): gamma in A(n) ~ C*n^(-gamma)
- envelope_prefactor (float): C
- arithmetic_energy_fraction (float): fraction in residue classes mod dominant_period
- detrend_method (str)
- n_points, n_range

### Trigger: fires after Stage 1 + 2 + 3 all fail
### Gate: spectral_slope_r2 > 0.7 (structure is real, not white noise)
### Consistency warning: |beta - (2H-1)| > 0.3 → log warning

### Backtest prediction:
- GP-088, KWW, DFDO: None (smooth models succeed)
- A000607: None (Stage 2 finds form)
- Ulam: CHARACTERIZED (1/f, H≈0.07, period≈20.5, non-linear phase)

## Implementation Files:
1. `src/ztare/fit/statistical_fingerprint.py` (new, ~120 lines)
2. Extend `compress_champion.py` Stage 3 exit path
3. Extend Lean output with fingerprint comment block
4. Backtest on 5 substrates

## Additional Debate Logs (2026-04-21)

### Popper/Munger: Is log(U(n))=1.07*log(n)+2.01 overfitting?
Verdict: YES. Power laws trivially fit count sequences. The 1.07 exponent is
finite-window bias (same GP-088 failure mode — O(log(n)) corrections absorbed
into exponent). Munger: "man-with-a-hammer — you switched to the observable
that gave a result." Popper: "the experiment has one falsifiable path: the
correction term. But the gates don't distinguish 'found correction' from
'fit log(cn) well enough.'" The panel was RIGHT to recommend U(n)/n.

Counter-panel (Tao/Hardy/Steinerberger) reconciled: the Popper/Munger panel
reached the right operational recommendation (change observable) via an
intellectually sloppy dismissal (calling a holdout-validated measurement
"trivially correct"). The 1.07 exponent is real but biased — it's 1.0 +
logarithmic correction, not super-linear growth.

### Ramanujan/Fourier/Mandelbrot: Crack the Ulam wave
1. Ramanujan: compute density by residue class mod 21. Result: spread 0.006
   (30% of wave energy). Wave is NOT purely arithmetic.
2. Fourier: use Hilbert transform for instantaneous amplitude/phase. Key
   insight: fit trend and oscillation SEPARATELY. Joint optimization entangles.
3. Mandelbrot: check for 1/f slope. CONFIRMED: slope=-0.94. Proposed
   Weierstrass function for self-similar oscillation.

Joint recommendation: (1) arithmetic decomposition (done, negative), (2) Hilbert
analytic signal (done, phase non-linear), (3) DFA for Hurst (done, H=0.072 on
W=21 detrend, H=0.377 on linear detrend — method-dependent, Kahneman's objection).

## Regression + Overfitting Verification (2026-04-21)

| Check | Result |
|-------|--------|
| R4 fixture regression | 13/13 PASS |
| GP-088 compression | 3 gate-passing, no fingerprint (correct) |
| KWW compression | 3 gate-passing, no fingerprint (correct) |
| DFDO compression | 0 gate-passing, no fingerprint (correct refusal) |
| A000607 compression | 1 gate-passing Stage 2 (correct) |
| Ulam compression | 0 gate-passing, fingerprint FIRES (correct) |
| All 6 source files AST | OK |
| False positives | 0 across 5 substrates |

Overfitting assessment: the fingerprint MEASURES statistical properties (spectral
slope via OLS, Hurst via DFA, phase via Hilbert). It does not optimize against
holdout gates. There is no parameter fitting against holdout data. These are
descriptive statistics — they cannot overfit by construction.

## Gate Normalization Fix (2026-04-21, Panel-Approved)

**Problem:** Absolute gate thresholds (e.g., 0.05) conflate structural failure with
calibration imprecision on large-scale observables. A001156 (z to 106) and A002865
(z to 556) had correct topologies rejected because tiny relative errors (0.16%, 0.04%)
exceeded absolute thresholds. GP-088 (z to 13) passed because 0.05 absolute is 0.4%
relative at that scale — coincidentally reasonable.

**Fix:** `src/ztare/gates/residual_norm.py` — shared utility: normalized_max_residual
divides by max(|obs|). Relative threshold 0.005 (0.5%) is scale-invariant.

**Backtest (4 substrates, compression champions):**
- Hardy-Ramanujan: 0.0019 normalized (PASS @0.005)
- Lucky numbers: 0.0016 normalized (PASS @0.005)
- Square partitions: 0.0016 normalized (PASS @0.005) — was FAIL with absolute gates
- No-1 partitions: 0.0004 normalized (PASS @0.005) — was FAIL with absolute gates

**Protocol:** Applied to FUTURE substrates only. A001156 and A002865 results stand
as topology identifications (not retroactively upgraded to gate passes).

## Next Actions:
- [ ] Implement statistical_fingerprint.py
- [ ] Wire into compress_champion.py
- [ ] Backtest on 5 substrates
- [ ] Extend Lean output
- [ ] Run on Ulam at n=10^6 (requires computing 10^6 Ulam numbers — ~hours)
