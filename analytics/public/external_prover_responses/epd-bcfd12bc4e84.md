# External-prover dispatch epd-bcfd12bc4e84

**Model**: gpt-5.5-2026-04-23
**Substrate**: NS-Track-B
**Dispatched**: 2026-05-18T20:32:22.410969+00:00
**Cost**: $0.0000
**Tokens**: 1223 in / 17839 out

## Question

# ADVERSARIAL KILL — tick641 dyadic marginal-coupling beta (cross-field RG transport)

You are a COLD adversary. Your job is to KILL the derivation, not bless it. Be Meta-Darwin.
Artifacts: ztare_proofs/ZtareProofs/ns_tick640_c3_no_complementary_pair_c7lower_nontransfer.lean
and ns_tick641_dyadic_beta_function_identically_zero_marginal.lean (both type-check under Mathlib).

## The claim to falsify
Katz-Pavlovic/Cheskidov dyadic NS adot_n = k_n a_{n-1}^2 - k_{n+1} a_n a_{n+1} (k_n=lambda^n,
lambda>1); inertial fixed-flux balance k_n a_{n-1}^2 = k_{n+1} a_n a_{n+1}; substitute
a_n = lambda^{-n/3} b_n (K41). CLAIM: every lambda-prefactor cancels IDENTICALLY leaving the
scale-FREE recursion b_{n+1} = b_{n-1}^2 / b_n. Logs u_n=log b_n: u_{n+1} = 2 u_{n-1} - u_n.
Char poly x^2 + x - 2 = (x-1)(x+2), roots {1,-2}. CLAIM: distinct roots => no repeated unit
root => NO secular/log-in-n term => the RG marginal-relevance (log-running) lever the
cross-field analogy hoped for provably does NOT exist in the deterministic dyadic surrogate;
only |-2|>1 alternating blow-up-side mode. Hence RG transport CONFIRMS+STRENGTHENS the
route-1 supercritical-enstrophy terminus (tick600/611/640), NOT a lever. Honest residual:
residual_class=new_channel_or_residual_measure_needed; SOLE un-probed object = a
STOCHASTIC/viscous-fluctuation (turbulent-ensemble) beta = NEW object algebra, principal-gated,
NOT a route-1 tick.

## Lived ground-truth attack surface (RUN each, do not vibe-check)
1. PREFACTOR ALGEBRA: recompute independently. LHS lambda-exponent in lambda^{-(n+1)/3} b_{n+1}.
   RHS: lambda^{-1} * (lambda^{-2(n-1)/3} b_{n-1}^2)/(lambda^{-n/3} b_n). Does the RHS
   lambda-exponent REALLY equal -(n+1)/3? Show arithmetic. If not identical-cancel, the
   scale-free recursion is WRONG and the tick falls.
2. WRONG-MODEL RISK: is k_n a_{n-1}^2 = k_{n+1} a_n a_{n+1} the correct stationary inertial
   balance for THIS model, or wrong nonlinear-term structure (Obukhov vs KP vs Cheskidov
   sign/index conventions)? Wrong balance => wrong recursion.
3. tick637 ERROR CLASS (recurring author failure): in tick637 the author wrongly treated a
   LINEAR-in-omega CZ operator as degree-0 => off-by-one. Analogous scaling/degree
   misattribution here (mis-counting k_n powers; multiplicative-vs-quadratic beta)?
4. RG LOGIC: is "distinct char roots => no log-running" the correct RG statement? Log-running
   needs a repeated marginal eigenvalue OR a nonzero nonlinear beta-term. The recursion is
   EXACTLY linear in logs (multiplicative) so no nonlinear beta-term by construction. Is THAT
   legitimate, or does the inertial-balance reduction (dropping time-derivative + viscous term)
   DISCARD exactly the term that would generate a nonzero deterministic beta? If so the
   residual is NOT principal-gated (it is a route-1 lever) and the verdict FLIPS.
5. SCOPE: is the framing (NOT closure, NOT impossibility; residual=stochastic-beta
   principal-gated) accurate, or laundering a settled-negative / over-claiming a terminus?

## Output (split verdict, do not launder)
For each 1-5: PASS / FAIL / PASS-with-must-fix + exact computation or counterexample.
Headline: SOUND | FALSE (name the load-bearing error) | OVERCLAIM (downgrade scope to what).
Give p_success in [0,1].


## Response

## Headline: **OVERCLAIM**  
Downgrade to: **for the positive, nonzero, inviscid, unforced, stationary KP fixed-flux recurrence only**, the K41-rescaled log recursion has no secular \(n\)-term. It does **not** prove a no-go theorem for the full deterministic viscous/time-dependent/statistical dyadic surrogate.

Cites: KP-type dyadic equation as in Katz–Pavlović, *Trans. AMS* 357 (2005), 695–708; Cheskidov–Friedlander–Pavlović, “An inviscid dyadic model of turbulence: the fixed point and Onsager’s conjecture,” *JMP* 48 (2007), 065503, arXiv:math/0610815; viscous Cheskidov model, *Trans. AMS* 360 (2008), 5101–5120, Eq. (1.1).

---

## 1. PREFACTOR ALGEBRA — **PASS**

From the stated balance
\[
k_n a_{n-1}^2=k_{n+1}a_na_{n+1},\qquad k_n=\lambda^n,
\]
\[
a_{n+1}=\lambda^{-1}\frac{a_{n-1}^2}{a_n}.
\]
Substitute \(a_j=\lambda^{-j/3}b_j\):
\[
\lambda^{-(n+1)/3}b_{n+1}
=
\lambda^{-1}
\frac{\lambda^{-2(n-1)/3}b_{n-1}^2}{\lambda^{-n/3}b_n}.
\]
Exponent on RHS:
\[
-1-\frac{2(n-1)}3+\frac n3
=
-1+\frac{-2n+2+n}{3}
=
\frac{-3-n+2}{3}
=
-\frac{n+1}{3}.
\]
So
\[
b_{n+1}=\frac{b_{n-1}^2}{b_n}.
\]
No prefactor error under the stated \(k_n=\lambda^n\) convention.

---

## 2. WRONG-MODEL RISK — **PASS-with-must-fix**

For the **explicitly written KP forward-cascade model**
\[
\dot a_n=k_n a_{n-1}^2-k_{n+1}a_na_{n+1},
\]
the stationary inviscid balance is exactly
\[
k_n a_{n-1}^2=k_{n+1}a_na_{n+1}.
\]

Must-fix scope:

- This is **not** the Obukhov/non-KP dyadic nonlinearity. For Obukhov-type structure
  \[
  \dot a_n=k_na_{n-1}a_n-k_{n+1}a_{n+1}^2,
  \]
  the stationary recursion becomes
  \[
  b_{n+1}^2=b_{n-1}b_n,
  \]
  hence in logs
  \[
  2u_{n+1}=u_{n-1}+u_n,
  \]
  with roots \(1,-1/2\), not \(1,-2\).

- Cheskidov/KP papers often encode the physical shell ratio and nonlinear coefficient differently, e.g. coefficients like \(\lambda_j^{5/2}\). Your algebra is valid only if \(\lambda\) denotes the **nonlinear coefficient ratio** \(k_{n+1}/k_n\), not necessarily the physical wavenumber ratio.

---

## 3. tick637-STYLE DEGREE / SCALING MISATTRIBUTION — **PASS-with-must-fix**

No off-by-one under the literal hypotheses \(k_n=\lambda^n\), \(a_n=\lambda^{-n/3}b_n\).

But there is a real convention trap. If the physical shell ratio is \(q\) and the nonlinear coefficient is
\[
k_n=q^{\theta n},
\]
then using the physical-looking normalization \(a_n=q^{-n/3}b_n\) gives
\[
b_{n+1}=q^{1-\theta}\frac{b_{n-1}^2}{b_n}.
\]
Computation:
\[
q^{-(n+1)/3}b_{n+1}
=
q^{-\theta}\frac{q^{-2(n-1)/3}}{q^{-n/3}}
\frac{b_{n-1}^2}{b_n}
=
q^{-(n+1)/3}q^{1-\theta}\frac{b_{n-1}^2}{b_n}.
\]
Thus for Cheskidov-style \(\theta=5/2\), a leftover \(q^{-3/2}\) appears unless one instead normalizes by \(k_n^{-1/3}=q^{-\theta n/3}\).

So: algebra sound, but only with the declared coefficient-scale K41 normalization.

---

## 4. RG LOGIC — **PASS-with-must-fix**

For the reduced recurrence,
\[
u_{n+1}=2u_{n-1}-u_n,
\]
the characteristic equation is
\[
r^2+r-2=0=(r-1)(r+2).
\]
Thus
\[
u_n=A+B(-2)^n.
\]
The unit root \(r=1\) is simple, so there is no homogeneous secular term \(n\cdot 1^n\). Since the log recursion is exactly linear, there is also no nonlinear beta term inside this reduced algebra.

But the no-log conclusion is only for the already-imposed stationary inviscid fixed-flux constraint. Retaining deterministic discarded terms gives nonzero scale terms. For example, with
\[
\dot a_n=\lambda^n a_{n-1}^2-\lambda^{n+1}a_na_{n+1}
-\nu d_n a_n+f_n,
\]
one obtains
\[
b_{n+1}
=
\frac{b_{n-1}^2}{b_n}
-\nu d_n\lambda^{-2(n+1)/3}
+\lambda^{-(n+2)/3}\frac{f_n-\dot a_n}{b_n}.
\]
If \(d_n=\lambda^{2n}\), the viscous correction is
\[
-\nu\lambda^{(4n-2)/3}.
\]
That is deterministic and scale-dependent. It is mostly a relevant/power correction, not automatically a marginal log, but it falsifies any claim that the only remaining object is stochastic or principal-gated.

So: no log in the reduced fixed-flux map; no full deterministic RG no-go theorem.

---

## 5. SCOPE / TERMINUS CLAIM — **FAIL**

The supported theorem is:

> For positive nonzero solutions of the inviscid stationary KP fixed-flux recurrence, after normalization by \(k_n^{-1/3}\), the log profile is \(A+B(-2)^n\), hence has no \(n\)-secular correction.

Unsupported exports:

- “deterministic dyadic surrogate has no RG lever” — too broad;
- “sole residual is stochastic/viscous-fluctuation beta” — false, deterministic viscous/time-dependent/forced corrections remain;
- “confirms+strengthens route-1 supercritical-enstrophy terminus” — not proved by this algebra;
- “principal-gated residual only” — overclaim.

Standard-form divergence:

- **Precondition proved:** inviscid, unforced, stationary, positive/nonzero, KP-only, coefficient-scale K41.
- **Conclusion claimed:** full deterministic/stochastic dyadic RG transport lacks marginal log lever.
- **Quantifier shift:** from one algebraic fixed-point channel to all relevant dyadic RG channels.
- **Failure:** discarded deterministic terms can generate nonzero beta corrections.

---

## p_success

\[
p_{\mathrm{success}}=0.42.
\]

The cancellation and no-secular-term algebra are correct; the route-level “terminus / sole residual” conclusion is not.

**VERDICT: partially — the fixed-flux KP recurrence has no log-running, but the claimed full RG/no-residual terminus is an overclaim.**
