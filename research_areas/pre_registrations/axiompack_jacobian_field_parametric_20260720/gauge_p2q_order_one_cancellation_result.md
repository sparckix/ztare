# Minimum-weight \(P^2Q\) cancellation

## Current result

The order-one target perturbation

\[
K_s^{P^2Q}=K_s-\frac{s}{168}P^2Q
\]

cancels the original rate-five source generator.  Its source Hamiltonian
perturbation is

\[
-\frac{s}{21}P_s^2Q_s.
\]

For this exact connection, every source logarithmic Hamiltonian satisfies

\[
\boxed{\deg\Omega_n^{\rm src}\le4n+4}.
\]

Every target logarithmic Hamiltonian satisfies

\[
\boxed{\deg\Omega_n^{\rm tgt}\le n+2}.
\]

Hence the symmetric logarithmic rate of this connection is at most four.

The first persistent triangular quotient, at excess

\[
G_4=a+b-4q-4=-7,
\]

has an exact Bernoulli ray of source derivation degree \(4n-6\).  Therefore

\[
\boxed{
\text{source rate}
=\text{symmetric rate}
=4
}
\]

for this connection.

## Newton upper bound

The largest source Hamiltonian degrees at costs two through six are

\[
(12,16,18,20,20).
\]

The perturbation has uniform total Hamiltonian degree at most twenty, so
costs seven and above lie below every earlier slope-four face.  The grading
\(G_4\) is nonpositive on the complete instantaneous connection and is
additive under the density-\(z^2\) Hamiltonian bracket.  This proves the
displayed all-order upper bound.

For the target density one, Hamiltonian brackets subtract two from total
degree.  Every instantaneous target term obeys
\(\deg H-q-2\le0\), including the cost-two cubic \(P^2Q\).  Additivity gives
the target bound.

## Finite-core rank-two residual

The zero-excess logarithmic generators are

\[
A=-\frac{325}{5376}u^6z^6,\qquad
B=-\frac1{43008}u^8z^8.
\]

They commute.  Removing both leaves a finite excess-\(-7\) core supported
only through cost eleven.  All later terms in the quotient arise from the
two shifts

\[
(q,d)\mapsto(q+2,d+2),\qquad
(q,d)\mapsto(q+3,d+2),
\qquad d=a-b.
\]

The first scalar boundary projection couples to a neighboring orbit at
adjoint depth three.  Passing instead to the triangular grading

\[
h=q-(a-b)
\]

isolates the first persistent boundary.  The minimum \(h=4\) boundary
terminates, while \(h=5\) is closed under \(A\) and cannot receive feedback
from higher \(h\).

With

\[
E_0=uz^4,\qquad E_{k+1}=[A,E_k],
\]

the normalized right-`dexp` equation is

\[
2D+2(1-e^{-x})D'
+\frac{227}{23400}(e^{-x}-1+x)
-\left(-\frac1{336}+\frac{779}{23400}x\right)=0.
\]

Its regular solution is

\[
D(x)=
-\frac{221}{26208}
+\frac{23}{1950}x
+\frac{13}{1872}\frac{x}{e^x-1}.
\]

Thus, for \(m\ge1\), the coefficient at orbit depth \(2m\) is a nonzero
multiple of \(B_{2m}/(2m)!\).  It occurs at logarithmic order
\(n=2+4m\), on Hamiltonian exponent \((1+10m,4+6m)\), and has source
derivation degree \(4n-6\).

## Verification and boundary

The exact replay
[`gauge_p2q_source_newton_modules.py`](gauge_p2q_source_newton_modules.py)
reconstructs the family, proves the support cutoff, enumerates the
radial-free core, checks the closed scalar equation, and carries the
complete \(G_4\ge-8\) quotient through order thirty-six.
The arithmetic endpoint
[`AxiomPackJacobianP2QMagnusRateArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianP2QMagnusRateArithmetic.lean)
kernel-checks radial noncancellation, even-coefficient nonvanishing, and
the degree formula.

This result classifies one exact connection and proves that the symmetric
minimax statistic is at most four.  It does not prove a universal lower
bound over the full cone-compatible connection space.
