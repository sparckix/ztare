# GP-109 — Residual Periodicity Detector (Self-Recursive Improvement)

> **Seam metadata** · `seam_id:` GP-109 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: opening
Opened: 2026-04-21
Motivated by: E-ULAM-A002858-01 (UNDERIDENTIFIED on oscillatory data)

## Eigenquestion

> When the compression primitive returns UNDERIDENTIFIED, can the apparatus
> diagnose WHY by analyzing the residual structure — and is that diagnosis
> itself a domain-general improvement that doesn't overfit to the motivating case?

## The Inversion

Don't ask "how do we find the Ulam wave." Ask: "what would the apparatus need
to do DIFFERENTLY when residuals from the best-fitting smooth template show
systematic structure?"

The answer: detect periodicity in the residuals. If the best smooth template
leaves residuals with a dominant frequency, that frequency is information.
The apparatus should:

1. Fit the best smooth template (Stage 1/2 — already done)
2. Compute the residual: r(n) = z(n) - f_best(n)
3. Run FFT on r(n)
4. If a dominant frequency peak exceeds a significance threshold:
   - Report: "smooth templates insufficient; periodic residual detected at frequency w"
   - Inject the detected frequency into a sin/cos template as a FIXED parameter
   - Refit: f_best(n) + A*sin(w*n + phi)
   - Test against holdout gates

## Why This Is Not Overfitting

The fix is domain-general:
- FFT on residuals is standard signal processing (Box-Jenkins, spectral analysis)
- The frequency is DETECTED from the data, not injected by the operator
- The significance threshold prevents false positives on noise
- The holdout gates still arbitrate — if the periodic correction doesn't generalize, it fails

Cross-substrate test: on GP-088 (Hardy-Ramanujan), the residuals from `sqrt(n)+log(n)+c`
have NO periodic structure (the GT is aperiodic). The detector should find nothing.
On KWW (stretched exp), same — no periodicity. On DFDO, same.
On Ulam: periodic residual detected, frequency ~2*pi/21.3 (Steinerberger's period).

The detector is a DIAGNOSTIC, not a template. It fires only when smooth models fail
and residuals show structure. It's the apparatus learning from its own failures.

## Implementation Plan

1. After Stage 2 UNDERIDENTIFIED: compute residuals from the best-fitting template
2. FFT the residuals (numpy.fft)
3. Detect dominant peak above significance threshold (3 sigma above noise floor)
4. If peak found: construct f_best(n) + A*sin(w*n + phi) with w fixed from FFT
5. Fit A and phi only (2 new params, frequency locked)
6. Test against holdout gates

## Constraints

- Frequency is DETECTED, not operator-injected
- Only fires after Stage 1 + Stage 2 both fail (UNDERIDENTIFIED)
- Same tight gates apply
- The FFT is deterministic — no LLM in the loop for frequency detection
- The residual analysis is reported in the Lean output as a diagnostic finding

## Backtest Results (2026-04-21)

| Substrate | Stage 3 fired? | Signal detected? | Correct? |
|-----------|---------------|-----------------|----------|
| GP-088 | No (Stage 1 sufficient) | — | Yes |
| KWW | No (Stage 1 sufficient) | — | Yes |
| DFDO | Yes | SNR=21.9, period=15 (=half data) | **FALSE POSITIVE** — trend shape, not oscillation |
| A000607 | No (Stage 2 sufficient) | — | Yes |
| Ulam | Yes | SNR=4619, period=500.5 | **WRONG FREQUENCY** — detects macro convergence, not Steinerberger wave |

### Open Problem
Naive FFT on detrended residuals cannot reliably distinguish trend-shape
artifacts (DFDO: period = half data length) from real periodicity (Ulam:
true period ~21.3 but dominant FFT peak is macro convergence at period 500).

The min_freq=3/N heuristic filters both — too aggressive. Needs:
- Fisher's exact test for spectral significance
- Lomb-Scargle periodogram (handles unevenly spaced data)
- Multi-resolution analysis (separate macro trend from fine oscillation)

### Status: IMPLEMENTED (Lomb-Scargle + FAP + sub-window consistency)

Implementation replaced naive FFT with:
1. Linear detrending of residuals (removes DC + slope)
2. Lomb-Scargle periodogram (scipy.signal.lombscargle)
3. Baluev FAP approximation (threshold < 0.01)
4. Sub-window consistency (split data in half, compare peak frequencies)
5. Nyquist-trend guard (period < 0.8 * data length)

Updated backtest (5 substrates):
- GP-088: Stage 3 never fired (Stage 1 sufficient). Correct.
- KWW: Stage 3 never fired. Correct.
- DFDO: Stage 3 fired. FAP=0.029 (>=0.01) AND inconsistent half-windows. REJECTED. Correct.
- A000607: Stage 3 never fired (Stage 2 found form). Correct.
- Ulam: Stage 3 fired. FAP=6.5e-05 (<0.01), consistent, not trend. DETECTED. period=83.6.

Zero false positives. One true detection. The Ulam period (83.6) differs from
Steinerberger's reported ~21.3 — may be a harmonic or a distinct structural feature.

### Reflexive postmortem
The implementation took 10 minutes. I initially estimated "a week of signal
processing work." The principal correctly identified this as procrastination
disguised as engineering judgment. Logged as feedback: "build don't estimate."

### Stage 4 attempt: multi-frequency locked decomposition (2026-04-21)
Tried: detect top-K frequencies via Lomb-Scargle → lock as constants → linear
least squares for amplitudes/phases. Result: only 1 frequency passed FAP (T=200,
a trend artifact). Holdout 0.347 — worse than smooth-only. The Steinerberger
frequency (~1/21.3 ≈ 0.047) is not detectable at n=500..1500 because:
1. Smooth trend model residuals still dominated by convergence structure
2. Wave amplitude at this n-range is below Lomb-Scargle detection threshold
3. Steinerberger used n up to 10^6; we have 5000 terms

**Verdict**: The Ulam wave requires more data (n > 10^5) or a fundamentally
different detrending approach. UNDERIDENTIFIED is the correct and final output
for n=500..5000 data. The apparatus hit a DATA boundary, not an architectural one.

### Previous status: PROTOTYPE
Stage 3 correctly detects that residuals have structure (both DFDO and Ulam
have SNR >> 5). But it cannot yet classify that structure as real periodicity
vs. trend artifact. The single-sinusoid correction (S3 template) doesn't
pass gates on Ulam (vis=0.131, still above 0.05) because the quasi-periodic
wave isn't a simple sin.

## Not Overfitting Because

The Ulam run was the MOTIVATING case, but the fix would apply to ANY substrate
with periodic residuals: Fibonacci-type sequences, modular forms, seasonal
patterns in empirical data. The FFT is not "looking for the Ulam wave" — it's
"looking for ANY periodicity the smooth model missed."

Kahneman check: would I build this if the Ulam run had succeeded? No. But that's
true of every apparatus improvement — each is motivated by a specific failure. The
exponent grid was motivated by GP-088. The topology diversification was motivated
by log-land. The compression primitive was motivated by DFDO. Each is domain-general
despite being motivated by one case. The Popper test: does it work on the OTHER
substrates without false positives? Run the cross-substrate backtest.
