# Fixed-gauge all-order degree law

**Status:** exact symbolic family certificate; filtered envelope kernel-checked;
historical priority provisional

## Theorem

Fix the public parameter `s`, quotient coordinates

\[
(v,L),\qquad L=2t-3v,
\]

and the target Hamiltonian gauge

\[
F_s=\exp(sX_H)\circ F_0\circ\psi_s,qquad
X_H(P,Q)=(-Q/2,P^2/12).
\]

Write

\[
\psi_s=(v,t)+\sum_{n\ge2}s^nY_n(v,t).
\]

Then, for every `k>=1`, both components have quotient total degree

\[
\deg Y_{2k}=10k+1,
\qquad
\deg Y_{2k+1}=10k+3.
\]

The linear change `(v,t)<->(v,L)` preserves total degree. Three-variable lift
degree and minimization over target gauges lie outside this statement. We use
`deg(0)=-infinity` when stating filtration bounds.

## Exact target-relative velocity

Freeze the evolution convention by

\[
\partial_s\psi_s=D\psi_s\,V_s.
\]

Differentiating the displayed factorization gives

\[
V_s=(DF_s)^{-1}\bigl(\partial_sF_s-X_H(F_s)\bigr)
   =\sum_{m\ge1}s^mA_m.
\]

The exact normalized family has quotient Jacobian `-gamma^2`. Symbolic
cancellation gives a polynomial vector field in `(v,t)` with scalar
denominators

\[
84934656(s-6)^8(s-4)^2,qquad
28311552(s-6)^8(s-4)^2.
\]

They are nonzero at `s=0`; both spatial numerators have total degree 15.
Consequently

\[
\deg A_1=11,qquad \deg A_2=13,qquad
\deg A_m\le15\quad(m\ge3).
\]

The leading fields are especially rigid. Put

\[
r=vL,qquad
X=\left(-\frac3{128}v^7L^4,
\frac3{128}v^6(t-3v)L^4\right).
\]

The exact replay proves

\[
A_1^{\rm top}=2X,qquad
A_2^{\rm top}=-\frac7{12}rA_1^{\rm top},qquad X(r)=0.
\]

It also gives the full degree-15 velocity as an invariant multiple of `X`:

\[
V_s^{[15]}=
-\frac{243s^3(s-4)^9}{8192(s-6)^6}\,r^2X.
\]

## Degree mechanism

In the time-ordered expansion of `psi_s`, an occurrence of `A_m` costs
parameter weight `m+1` and raises polynomial degree by at most
`deg(A_m)-1`. Relative to five units of degree gain per parameter weight, the
deficits are

\[
0\quad(m=1),\qquad 3\quad(m=2),\qquad
\ge6\quad(m\ge3).
\]

At even weight `2k`, the all-`A_1` index multiset is the sole zero-deficit
type. At odd weight `2k+1`, the sole deficit-three type has one `A_2` and
`k-1` copies of `A_1`. Different placements of `A_2` are distinct
time-ordered words, but their leading parts coalesce because
`A_2_top` is an `X`-invariant scalar multiple of `A_1_top`.

The closed leading flow makes noncancellation explicit. With

\[
B=\frac3{64}v^6L^4,
\]

the `X`-flow is

\[
\Phi_\tau(v,L)=
\left(v(1+B\tau)^{-1/2},L(1+B\tau)^{1/2}\right).
\]

Its binomial coefficients are nonzero in characteristic zero. The even top
coefficient is a nonzero multiple of `X^k/k!`; the odd top coefficient is a
nonzero multiple of `rX^k/(k-1)!`. Their degrees are respectively `10k+1`
and `10k+3`, proving equality in the upper bounds.

## Independent inverse-branch check

The seed in `(W,gamma)` coordinates is

\[
P=\gamma+2W-3W^2,\qquad Q=\gamma W+W^2-2W^3.
\]

Its selected formal inverse branch obeys

\[
W^3-W^2+PW-Q=0.
\]

Writing `g=3W^2-2W+P`, exact elimination gives

\[
g^3+(3P-1)g^2-4P^3+P^2+18PQ-27Q^2-4Q=0
\]

and

\[
W(3g+6P-2)=g+9Q-P.
\]

These two identities are independently checked in Lean. The Newton polygon
of the first equation has a dominant square face. After the exact first-order
cancellation, its selected branch has even top series proportional to
`sqrt(1+B s^2)` and odd top series proportional to
`s^3/sqrt(1+B s^2)`. The recovery identity gives the reciprocal square-root
series for the other source coordinate. This reproduces the same two degree
formulas without using the Magnus expansion.

## Logarithmic formulation

For the substitution automorphism, write its Magnus logarithm as

\[
\Omega_s=\sum_{j\ge2}s^jZ_j.
\]

Each `Z_j` is a Lie polynomial in the `A_m` of total parameter weight `j`.
The same deficit count shows that an even zero-deficit candidate would be a
nested bracket in `A_1` alone and hence vanish. An odd deficit-three candidate
would contain one `A_2` and copies of `A_1`; its highest bracket vanishes
because `[X,rX]=0`. Therefore the preregistered primitive bounds hold:

\[
\Delta_{2k}>0\quad(k\ge2),\qquad
\Delta_{2k+1}>3\quad(k\ge2).
\]

This step uses the Magnus series. Velocity coefficients and logarithm
coefficients agree only at the initial jets; bracket corrections begin at
order five.

## Certificates

The family-specific replay is
[`equivariant_filtered_velocity.py`](equivariant_filtered_velocity.py). It
checks the exact Jacobian, denominator cancellation, uniform degree cap,
leading fields, invariant, and degree-15 factorization. Its component
numerator hashes are

- `5a9df0e99512d0aa1f42c058e6d46bf67c3039ae063b9c7cf313dcb8144e4469`;
- `21513e7a1cc986db92374302890f5c7e715b1c80dcb29c3dbd15e95ad5b0a4cb`.

[`AxiomPackJacobianFilteredFlow.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianFilteredFlow.lean)
checks the leading invariant identities, nonzero field, parameter-cost degree
envelope, and equality cases. Its terminal theorem passed provider-free
LeanMill governance with zero provider calls:

- closure-record SHA-256
  `ef9557ec3a37f2ac7e0f5e6606f5225aba4109829d4f80e125e1f78186e9c58d`;
- kernel-parity SHA-256
  `cd5e3efead016b8ee1fe6b62e150ceaa770d40f02b9caab20a360a3372f5bad0`;
- governed closure
  [`AxiomPackJacobianFilteredFlow.filtered_flow_certificate_3d2bc0b9439e.lean`](../../../ztare_proofs/closures/AxiomPackJacobianFilteredFlow.filtered_flow_certificate_3d2bc0b9439e.lean).

The inverse-branch aggregation passed the same provider-free path:

- closure-record SHA-256
  `0d7203391bdeaa5e84bf49298bef7f6abb55c3f0625494f28d71a5b5225c66c7`;
- kernel-parity SHA-256
  `85e7f8c82dc6bad65abdbb0f3d1d80ca5f9b3922a969fe4d84943f30e2992cf4`;
- governed closure
  [`AxiomPackJacobianFilteredFlow.inverse_branch_coordinate_certificate_3d2bc0b9439e.lean`](../../../ztare_proofs/closures/AxiomPackJacobianFilteredFlow.inverse_branch_coordinate_certificate_3d2bc0b9439e.lean).

## Boundary

The formula belongs to the declared target-Hamiltonian gauge. A higher-order
equivariant volume-preserving target correction can change `V_s`, its degree
cap, and the coefficient sequence. Thus this theorem strengthens the
qualitative unboundedness result in one canonical public gauge, but does not
settle the gauge-minimized degree problem.

The public papers own the counterexample family, its inverse equation,
generic degrees, and the branch entering from infinity. Formal-etale path
lifting is standard. Targeted searches through 2026-07-25 did not find this
all-order filtered degree law, but that is insufficient for a priority claim.

The final 2026-07-25 priority pass searched the exact degree pair, inverse
cubic, Hamiltonian gauge, and Magnus/filtered-flow formulation. The closest
current sources remain the [public counterexample
paper](https://www.ulam.ai/research/jacobian.pdf), [Shaska's grading and
quotient analysis](https://arxiv.org/abs/2607.20210), [Migus's generic-degree
classification](https://arxiv.org/abs/2607.21572), and [Jelonek's component
geometry](https://arxiv.org/abs/2607.20597). None states the displayed
fixed-gauge coefficient-degree law or its invariant-flow mechanism. This
supports treating the theorem as a priority candidate pending expert review,
not as a certified first result.
