# Exact global-control Magnus ray pencil

## Claim boundary

This pencil concerns one explicit target-relative connection

\[
K_s=a(s)P^3+b(s)PQ-\frac14Q^2
\]

whose source velocity is polynomial in the spatial variables, rational in
the parameter, and vanishes at \(s=0\).  It can certify an upper-bound gauge
or an obstruction for this gauge.  It cannot prove a minimax lower bound
over all cone-compatible contacts.

## Eigenquestion

For the right-placed source equation

\[
\partial_s\psi_s=D\psi_s\,V_s,
\]

does the exact Magnus logarithm have, for every \(n\geq 6\), a nonzero top
weighted-Hamiltonian ray

\[
\operatorname{top}\Omega_n
=X_{c_n v^{n+7}g^{n+6}},
\qquad g=2t-3v,
\qquad c_n\neq0,
\]

and hence source degree \(2n+10\)?

The exact replay through orders six, seven, and eight gives

\[
c_6=\frac1{1048576},\qquad
c_7=-\frac{619}{1321205760},\qquad
c_8=\frac{343}{6794772480}.
\]

## Structural warning

The spatial degree-15 part of the exact velocity has full weighted
Hamiltonian proportional to

\[
(vg)^9.
\]

Consequently the top degree-15 velocity fields at different parameter
values commute.  Repeated maximal-degree bracketing therefore vanishes.
Any persistent slope-two ray must come from interaction with lower spatial
shells, so neither the earlier source Lie-closure rays nor a static
degree-excess truncation establishes the desired coefficient.

## Discriminating calculation

1. Reconstruct the exact adapted source vector field and the complete
   polynomial Hamiltonian \(H(s,v,g)\) for the density
   \(\rho=(g+2)^2\):

   \[
   H_g=\rho V^v,\qquad H_v=-\rho V^g.
   \]

   Verify both equations exactly before decomposing spatial shells.

2. Determine a multigrading or Newton-face quotient that is closed under
   the induced weighted Poisson bracket.  Derive its bracket law rather
   than dropping terms by an order-dependent degree heuristic.

3. Run the side-typed inverse-`dexp` recursion in that quotient.  Crosscheck
   its orders six through eight against the unfiltered vector-field replay.

4. Compute at least one new exact order \(n\geq9\).  If a candidate scalar
   recurrence appears, reserve later coefficients for held-out checks and
   distinguish a proved bracket recurrence from a fitted numerical pattern.

5. Run the matching target Magnus recursion for \(K_s\).  The tail statistic
   is symmetric in source and target, so a source-only rate does not finish
   the connection analysis.

## Kill conditions

The displayed ray conjecture is killed by any exact order \(n\geq9\) for
which:

- the top source degree is not \(2n+10\);
- the top field is not proportional to
  \(X_{v^{n+7}g^{n+6}}\); or
- the projected coefficient vanishes.

A quotient is rejected if it fails exact bracket closure or disagrees with
the full orders-six-to-eight replay.  An inferred recurrence is rejected by
one held-out exact coefficient.

## Decision consequences

- Persistent nonzero slope two would show that the minimum-cap slope-four
  cascade is avoidable by this exact finite control while this connection's
  source logarithm remains unbounded at rate two.
- Eventual cancellation or bounded logarithmic degree would produce a
  finite-prefix escape candidate requiring symmetric target verification.
- Either outcome leaves open whether another cone-compatible gauge has
  smaller asymptotic maximum degree.

## Exact outcome at the kill order

The slope-two top-ray continuation is false.  In the exact polynomial
Hamiltonian chart

\[
z=g+2=2+2t-3v,\qquad \rho=z^2,
\]

the complete unfiltered right-Magnus replay gives

\[
\boxed{
\operatorname{top}\Omega_9
=X_{-\frac{23}{42278584320}v^{20}z^{17}}.
}
\]

Its source derivation degree is \(34\), rather than the conjectured \(28\).
The former slope-two monomial \(v^{16}z^{15}\) remains present with
coefficient

\[
-\frac{844253}{47563407360},
\]

but it is no longer the top shell.  Orders six through eight agree exactly
with the earlier vector-field replay, and both the source and target
Hamiltonian recursions pass their matching forward-`dexp` round trips.

The finite replay is
[`gauge_controlled_global_magnus_hamiltonian.py`](gauge_controlled_global_magnus_hamiltonian.py).

## Successor grading

For a source Hamiltonian monomial \(v^az^b\) at logarithmic cost \(q\), put

\[
I=a-3q-1,\qquad J=b-2q-3.
\]

The weighted Hamiltonian bracket adds \((q,I,J)\).  Exact support reduction
shows:

- every velocity grade is componentwise nonpositive;
- the order-two radial letter
  \(-3(vz)^7/448\) is the unique velocity grade \((0,0)\); and
- every all-parameter Hamiltonian exponent is at most nine.

Thus the southwest rectangle down to \((-6,-3)\) is a closed quotient, and
parameter costs \(q\geq6\) cannot enter it.  The exact quotient replay
through logarithmic order 81 matches

\[
c_r=
\frac1{2^{20}}
\left(-\frac3{128}\right)^r
(2r-1)!!
\frac{12B_{r+2}}{(r+2)!}
\]

at order \(6+2r\), on the Hamiltonian monomial

\[
v^{13+6r}z^{12+4r}.
\]

Equivalently, after removing the repeated adjoint multiplier, the scalar
generating function is

\[
\frac{12}{x^2}
\left(
\frac{x}{e^x-1}-1+\frac{x}{2}
\right).
\]

The replay is
[`gauge_controlled_global_magnus_graded_ray.py`](gauge_controlled_global_magnus_graded_ray.py).
It finds no formula failure through order 81.  For \(r=2m\), the displayed
coefficient is nonzero because \(B_{2m+2}\neq0\), and its derivation degree
would be

\[
5(6+4m)-8.
\]

This is not yet promoted as an all-order theorem.  The remaining proof
obligation is a symbolic elimination of the complete \((-6,-3)\) rectangle
showing that its projected inverse-`dexp` equation is exactly the displayed
Bernoulli divided difference.  Finite agreement through order 81 does not
discharge that obligation.

## Finite-core proof attack

Let

\[
A=-\frac3{896}(vz)^7
\]

be the zero-grade logarithmic generator.  For the grade-\((-6,-3)\) orbit,
use the base monomial

\[
E_0=vz^4,\qquad E_k=\operatorname{ad}_A^kE_0.
\]

Direct use of the monomial bracket gives

\[
E_k=
\left(-\frac3{128}\right)^k
\prod_{j=0}^{k-1}(2j-3)\,
v^{1+6k}z^{4+4k}.
\]

Writing the even target-grade logarithm as

\[
\sum_{k\ge0}s^{2+2k}d_kE_k,
\]

the observed exact coefficients normalize to

\[
d_0=-\frac{23}{32},\qquad
d_1=-\frac{151}{864},
\]

and

\[
\boxed{
d_k=\frac{B_k}{144\,k!}\quad(k\ge2).
}
\]

Thus its proposed closed generating function is

\[
D(x)
=-\frac{23}{32}
-\frac{151}{864}x
+\frac1{144}
\left(
\frac{x}{e^x-1}-1+\frac{x}{2}
\right).
\]

The all-order proof must establish this identity from the connection, not
from coefficient recognition.  The planned reduction is:

1. tag every occurrence of \(A\);
2. delete the tagged letters from a Lie word and call the remainder its
   negative-grade core;
3. use componentwise negativity and the exponent bound \(a,b\le9\) to show
   that only finitely many core grades and costs can sum to \((-6,-3)\);
4. enumerate those cores exactly in the monomial bracket algebra;
5. sum all insertions of \(A\) by the universal right-response operator; and
6. reduce the resulting finite combination to \(D(x)\).

The attack is killed if an unbounded family of \(A\)-free cores survives,
if a core beyond the enumerated cost contributes, or if the exact response
combination differs from \(D(x)\).  Only after the finite core table and the
formal response identity both pass may the even-Bernoulli nonvanishing
argument be promoted.

## Successor symbolic certificate

The five-core calculation above used the affine coordinate \(v\).  Exact
translation to

\[
u=1+v
\]

preserves polynomial degree and the density \(z^2\,du\wedge dz\), while
turning the complete grade-zero logarithm into the single radial
Hamiltonian

\[
A=-\frac3{896}(uz)^7.
\]

This exposes a smaller prospective certificate.  For a monomial \(u^az^b\)
at parameter cost \(q\), retain the same additive grades

\[
I=a-3q-1,\qquad J=b-2q-3
\]

and project to \(I\ge-6,\ J\ge-3\).  The observed instantaneous quotient has
only eighteen monomials, at costs two, three, and four.  The observed
logarithm outside the terminal grade \((-6,-3)\) also stops at cost four.
These observations are finite evidence; the proposed certificate must
derive the truncation from exact bracket relations.

Write the three finite logarithmic coefficients as

\[
\Omega_{\rm poly}(s)=s^2L_2+s^3L_3+s^4L_4.
\]

The discriminating symbolic test is:

1. prove in the closed southwest quotient that
   \([L_2,L_3]\) and \([L_2,L_4]\) lie entirely in terminal grade
   \((-6,-3)\), while \([L_3,L_4]=0\);
2. prove that, after either terminal core is formed, every further
   nonzero bracket must use the grade-zero part \(A\) of \(L_2\);
3. derive the complete even terminal forcing in forward right-`dexp` as

   \[
   F(x)=\frac1{1536}
   \left(1-\frac{1-e^{-x}}x\right);
   \]

4. for

   \[
   T_{\rm even}
   =\sum_{k\ge0}s^{4+2k}d_kE_k,\qquad
   E_0=u^7z^8,\quad E_{k+1}=[A,E_k],
   \]

   derive, rather than fit, the scalar equation

   \[
   2\left[D+f(D+xD')\right]+F=\frac7{3072},
   \qquad
   f(x)=\frac{1-e^{-x}}x;
   \]

5. verify symbolically that its unique formal solution is

   \[
   D(x)=\frac7{12288}
   +\frac1{2048x}
   \left(
   \frac{x}{e^x-1}-1+\frac{x}{2}
   \right).
   \]

The certificate is rejected if a nonterminal bracket survives, if a second
outer letter can act after the terminal core, if the forcing has any
additional all-order sector, or if substitution leaves a nonzero formal
residual.  If all checks pass, the coefficient at \(k=2m+1\) is a nonzero
multiple of \(B_{2m+2}\), giving logarithmic orders \(6+4m\) and source
derivation degree \(5n-8\).  This would settle unboundedness for this
explicit connection, while leaving the minimax problem over other
cone-compatible gauges open.

## Exact successor outcome

All five symbolic checks pass.  In the translated quotient,

\[
\begin{aligned}
[L_2,L_3]&=-\frac7{32768}u^{10}z^{10},\\
[L_2,L_4]&=-\frac1{131072}u^{13}z^{12},\\
[L_3,L_4]&=0.
\end{aligned}
\]

Both nonzero brackets are already terminal.  Componentwise grade
negativity proves that every later outer bracket is zero unless its letter is

\[
A=-\frac3{896}(uz)^7.
\]

The even core is \(-E_1/1536\) after the factor two from
\([\Omega_{\rm poly},\Omega_{\rm poly}']\) is included.  Forward right-`dexp`
therefore gives exactly the preregistered forcing

\[
F(x)=\frac1{1536}
\left(1-\frac{1-e^{-x}}x\right).
\]

The formal residual of the displayed candidate \(D(x)\) is zero.  The
diagonal coefficient \(2(k+2)\) makes that solution unique.  Thus

\[
d_k=\frac{B_{k+1}}{2048(k+1)!}\qquad(k\ge1)
\]

is derived rather than fitted.  The earlier order-81 calculation is now an
independent convention and chart replay.

For \(k=2m+1\), the previously proved positive-convolution recurrence gives
the nonvanishing of \(B_{2m+2}\), while

\[
\left(-\frac3{128}\right)^k
\prod_{j=0}^{k-1}(2j-1)
\]

is nonzero term by term.  Hence the exact source logarithm of this
connection contains, at every \(n=6+4m\), a nonzero Hamiltonian proportional
to

\[
u^{3n-5}z^{2n},
\]

whose derivation degree is \(5n-8\).

The exact symbolic certificate is
[`gauge_controlled_global_magnus_all_order.py`](gauge_controlled_global_magnus_all_order.py).
The arithmetic transfer compiles in
[`AxiomPackJacobianGlobalControlMagnusEscapeArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianGlobalControlMagnusEscapeArithmetic.lean).
The minimax boundary is unchanged: another cone-compatible moving
connection may have a smaller tail.
