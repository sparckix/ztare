# Pure contact-zero parity collisions and the Euler resonance

## Scope

This note resolves attack vector C in
[`gauge_pure_contact_zero_tail_induction_pencil.md`](gauge_pure_contact_zero_tail_induction_pencil.md).
It classifies all word depths in the target parity section and tests the
claim that every finite critical or supercritical contact-zero prefix must
generate an infinite rate-two cascade.

The conclusion is mixed.  Away from two monomial resonances there is an
exact lowest-exponent occurrence pivot at every word depth, including after
fixed rational amplitude specialization.  There is also an exact mixed
Euler resonance which cancels a radial descendant after one bracket and
creates no tail.  Thus a blanket finite-prefix charging lemma is false.  The
resonant family has to be removed as a finite boundary before the complete
radial/normal induction is applied.

## Exact parity algebra

Put

\[
E_c=P^c,\qquad O_a=P^aQ.
\]

In the target Poisson convention used by the moving-backbone adapter,

\[
\boxed{
\begin{aligned}
[E_c,E_e]&=0,\\
[O_a,E_c]&=-cE_{a+c-1},\\
[O_a,O_c]&=(a-c)O_{a+c-1}.
\end{aligned}}
\]

The lift-compatible parity section is

\[
\mathbb Q\oplus
\bigoplus_{c\ge3}\mathbb QE_c\oplus
\bigoplus_{a\ge1}\mathbb QO_a.
\]

The even span is an abelian ideal.  The odd span is the polynomial-vector-
field algebra: \(O_a\) acts on \(\mathbb Q[P]\) as
\(-P^a\partial_P\), with the displayed sign convention.  Consequently:

1. a nonzero word applied to an even terminal contains only odd letters;
2. a nonzero word applied to an odd terminal contains at most one even
   letter;
3. an even insertion changes an odd output to an even output, after which a
   second even insertion kills the word.

Parity therefore prevents cancellation between the zero-even-insertion and
one-even-insertion blocks.

If the odd word has letters \(O_{a_1},\ldots,O_{a_k}\), parameter costs
\(j_1,\ldots,j_k\), and

\[
A=\sum_{i=1}^k(a_i-1),\qquad J=\sum_{i=1}^k j_i,
\]

then its occurrence identity on either parity block has parameter-order
increment \(J\) and cusp-weight increment \(2A\).  On an even terminal,

\[
\operatorname{ad}_{O_{a_1}}\cdots
\operatorname{ad}_{O_{a_k}}E_c
=(-1)^k
\prod_{i=1}^k
\left(c+\sum_{h=i+1}^k(a_h-1)\right)
E_{c+A}.
\]

Every factor is positive for \(c\ge1\) and \(a_i\ge1\).  Thus individual
odd words on an even radial terminal never resonate.

## Fixed-rational-face collision theorem

The preceding word formula alone does not control collisions among words
with the same \((J,A)\).  The collision can be settled without treating the
amplitudes as generic.

Let the specialized odd face be

\[
F(P)Q,\qquad
F(P)=\sum_{u\in S}f_uP^u\in\mathbb Q[P],
\]

where every displayed \(f_u\) is nonzero, and put
\(a=\min S\).  Parameter monomials may be retained in the coefficient
ring: on a tied rate face the least \(P\)-exponent has a unique parameter
cost, so the same least-exponent arguments also distinguish the occurrence
order.

### Even terminal

For every \(c\ge1\) and \(k\ge1\), the least \(P\)-exponent in
\(\operatorname{ad}_{FQ}^kE_c\) is

\[
c+k(a-1),
\]

and its coefficient is

\[
\boxed{
(-1)^k f_a^k
\prod_{i=0}^{k-1}\bigl(c+i(a-1)\bigr)\ne0.}
\]

No higher exponent of \(F\) can reach this pivot.  It therefore survives
every fixed rational specialization with \(f_a\ne0\).

### Odd terminal

For a monomial face \(F=f_aP^a\),

\[
\boxed{
\operatorname{ad}_{f_aO_a}^{k}O_c
=f_a^k
\prod_{i=0}^{k-1}
\bigl(a-c-i(a-1)\bigr)
O_{c+k(a-1)}.}
\]

For \(a\ge2\), the complete exceptional set is

\[
\boxed{c=a\quad\text{or}\quad c=1.}
\]

If \(c=a\), the first bracket is zero.  If \(c=1\), the first bracket is
\((a-1)f_aO_a\) and every bracket of depth at least two is zero.  In every
other case the displayed product is nonzero for all \(k\).

These exceptions disappear as soon as the specialized face has at least
two exponents.  Let \(b>a\) be its next exponent.

If \(c=a\), the least pivot at depth \(k\ge1\) uses one \(b\)-letter and
\(k-1\) \(a\)-letters.  Its exponent is

\[
a+b-1+(k-1)(a-1),
\]

and its coefficient is

\[
\boxed{
f_b(b-a)f_a^{k-1}
\prod_{i=0}^{k-2}
\bigl(1-b-i(a-1)\bigr)\ne0,}
\]

with the empty product interpreted as one.

If \(c=1\), the depth-one pivot is
\(f_a(a-1)O_a\).  At every depth \(k\ge2\), the first pivot which sees both
least exponents has exponent

\[
b+(k-1)(a-1)
\]

and coefficient

\[
\boxed{
-f_a^{k-1}f_b(a-b)^2
\prod_{i=0}^{k-3}
\bigl(1-b-i(a-1)\bigr)\ne0.}
\]

These are lowest-\(P\)-exponent identities in \(\mathbb Q[P]\), not generic
amplitude statements.  Other words cannot cancel them after any fixed
rational specialization.  They give the all-index classification:

- every nonzero specialized odd face with at least two monomials has a
  nonzero orbit at every depth on every odd monomial terminal;
- a one-monomial odd face has an all-depth orbit except on \(O_a\) and
  \(O_1\);
- even terminals have an all-depth orbit for every nonzero odd face.

For a repeated least letter of positive cost \(j_a\), the occurrence orders
are \(q_0+kj_a\).  In the two broken-resonance formulas they are
\(q_0+(k-1)j_a+j_b\).  Both maps are injective.  Hence the surviving pivots
can be attached to same-order payments without rebilling one prefix order.

The paired source top face of a parity symbol of cusp weight \(w\) has
derivation degree \(2w-3\).  The repeated odd occurrence therefore has
source-degree increment \(4A\) at parameter-order increment \(J\).  It is
on or above rate two precisely when

\[
\boxed{2A\ge J.}
\]

Equivalently, the additive letter excess is
\(2(a-1)-j\), one half of the previously compiled parity grade
\(\gamma(2a+3,j)\).

## Decisive zero-payment cycle

The two monomial exceptions extend to a finite conjugation law.  The Euler
terminal \(O_1=PQ\) supports a lift-compatible mixed resonance.

For every \(d\ge3\), set

\[
H_d=\lambda O_{d+1}+\mu E_d
=\lambda P^{d+1}Q+\mu P^d,
\qquad \lambda,\mu\in\mathbb Q.
\]

Both nonconstant monomials lie in the exact target-lift algebra.  They have
the same eigenvalue under the Euler terminal, and the brackets are

\[
\boxed{
[H_d,O_1]=dH_d,\qquad
[H_d,[H_d,O_1]]=0.}
\]

Thus, at any positive parameter cost \(j\),

\[
\boxed{
\exp\!\bigl(\tau s^j\operatorname{ad}_{H_d}\bigr)O_1
=O_1+\tau d s^jH_d.}
\]

More strongly,

\[
\exp\!\bigl(\tau s^j\operatorname{ad}_{H_d}\bigr)
\left(O_1+\nu s^jH_d\right)
=O_1+(\nu+\tau d)s^jH_d.
\]

For rational \(\nu\), choosing \(\tau=-\nu/d\) cancels the descendant
exactly, with no brackets at larger parameter orders.  Taking both
\(\lambda\) and \(\mu\) nonzero makes this a mixed even/odd prefix.

The odd component \(O_{d+1}\) has weight \(2d+5\), so at cost \(j\) its
rate-two grade is

\[
\gamma(2d+5,j)=2(2d-j).
\]

It may therefore be critical or supercritical, \(j\le2d\), while the
complete orbit above remains finite.  A finite coefficient is not an
asymptotic payment.  This is a decisive counterexample to the proposed rule
that every nonzero finite critical/supercritical parity prefix supplies its
own infinite charged cascade.

The correct interpretation is a removable finite boundary: conjugation is
still invertible and the coefficient of \(O_1\) never vanishes.  What fails
is the inference from a high prefix to infinitely many paid descendants.

## What the moving pullback preserves

The target parity section is a Lie subalgebra, so the word and collision
classification above is exact before pullback.  It is also exact for the
radial associated target face, where there is one parity representative at
every cusp weight \(w\ge5\).

Literal source normal parity is not preserved by the complete moving
pullback.  With

\[
P_s=A_s(r)+a_sz,\qquad
Q_s=B_s(r)+b_srz,
\]

one has

\[
E_c(P_s)=
\sum_{h=0}^c\binom ch A_s^{c-h}(a_sz)^h,
\]

and \(O_a(P_s,Q_s)\) likewise contains both even and odd powers of \(z\).
The radial and first-normal layers are

\[
\begin{aligned}
R(E_c)&=A_s^c,
&N(E_c)&=cA_s^{c-1}a_s,\\
R(O_a)&=A_s^aB_s,
&N(O_a)&=aA_s^{a-1}a_sB_s+A_s^ab_sr,
\end{aligned}
\]

and obey the common tangency identity \(R'=L_sN\).  Higher normal layers
are controlled only by the loss-two Rees estimate.

Nor is the positive-\(D\) complement a parity module.  For
\(D=4P^3+27Q^2\),

\[
\{P^3,D\}=162P^2Q
\]

is not divisible by \(D\).  Hence the parity projection is a linear
section and its image is bracket-closed, but its kernel is not preserved by
the full contact-zero action.

The Euler cancellation is an exact target-polynomial identity and survives
substitution as such.  Its off-radial source consequences, however, belong
to the first-normal and higher-normal blocks; parity alone cannot certify
their rate.

## Source normal-filtration collision audit

The source density-\(z^2\) Hamiltonian basis

\[
\mathcal E_{a,n}=r^az^n=u^az^{a+n}
\]

has bracket

\[
\boxed{
[\mathcal E_{a,m},\mathcal E_{b,n}]
=(mb-an)\mathcal E_{a+b-1,m+n-2}.}
\]

Thus normal orders add and then lose two.  Since the exact source-only
Hamiltonian and every moving target pullback have normal order at least
zero, a word of fixed length with a selected normal-one seed appears at
first to be minimized by taking every other letter radial.

That selected-layer argument misses a complete coupled collision already at
row zero.  Write the row-zero source-only Hamiltonian as

\[
H_0^{\rm so}=R_0(r)+zN_0(r)+O(z^2).
\]

Exact extraction gives

\[
\begin{aligned}
R_0(r)
&=\frac{r^3(9r^3+36r^2-108r+64)}{288},\\
N_0(r)
&=-\frac{r^2(3r^2+12r-16)}{48}.
\end{aligned}
\]

For every polynomial target Hamiltonian \(K\), write its seed pullback

\[
K(P_0,Q_0)=R(r)+zN(r)+O(z^2).
\]

Both pairs lie on the same first-normal tangency graph:

\[
\boxed{
R_0'=(2-3r)N_0,\qquad R'=(2-3r)N.}
\]

The normal-minus-one part of their source bracket is consequently

\[
\boxed{
[H_0^{\rm so},K(P_0,Q_0)]_{n=-1}
=z^{-1}\bigl(N_0R'-R_0'N\bigr)=0.}
\]

This is a polynomial identity for the complete first two layers.  It is
stronger than cancellation of one chosen top monomial.

The top collision makes the occurrence ambiguity explicit.  If

\[
R(r)=\kappa r^w+\text{lower radial degree},
\]

then

\[
N(r)=-\frac{w\kappa}{3}r^{w-2}
     +\text{lower radial degree},
\]

while

\[
[r^6]R_0=\frac1{32},\qquad
[r^4]N_0=-\frac1{16}.
\]

The two paths to \(\mathcal E_{w+3,-1}\) are

\[
\begin{aligned}
\left[-\frac1{16}\mathcal E_{4,1},
      \kappa\mathcal E_{w,0}\right]
&=-\frac{w\kappa}{16}\mathcal E_{w+3,-1},\\
\left[\frac1{32}\mathcal E_{6,0},
      -\frac{w\kappa}{3}\mathcal E_{w-2,1}\right]
&=\frac{w\kappa}{16}\mathcal E_{w+3,-1}.
\end{aligned}
\]

They have the same parameter order, normal order, and radial Newton
coordinate, and cancel exactly.  Lower radial terms cancel by the same
\(N_0R'-R_0'N\) identity.

This collision is exhaustive on the proposed minimal ray.  If a Magnus word
has derivative orders \(j_i\), normal orders \(n_i\), length \(\ell\), and
logarithmic order \(q=\sum_i(j_i+1)\), put

\[
\delta_i=n_i+2j_i.
\]

Then

\[
n_{\rm out}+2q=2+\sum_i\delta_i.
\]

At total defect one, nonnegative normal support forces exactly one row-zero
normal-one layer and makes every other letter row-zero radial.  No
normal-two or normal-three seed layer, positive derivative row, or higher
normal target pullback can share that coefficient.  Summing over which
row-zero letter supplies the normal-one layer gives the tangent-graph
cancellation above.  Equivalently, the row-zero tangent graph is abelian
through normal order minus one: radial-radial brackets vanish, and the
complete one-normal bracket also vanishes.

Therefore the isolated row-zero normal-one source layer is not an odd
survivor in the coupled coefficient complex.  The radial-word formula on a
freely supplied odd terminal remains correct, but the actual defect-one
terminal needed by the finite-prefix attack is zero before any radial
cascade begins.  Parameter rows \(j\ge1\) start at defect at least two and
belong to the next radial/normal block rather than repairing this terminal.

## Coordinate-covariant two-layer law and the next face

The first attempted full-\(s\) calculation paired the fixed coordinate
\(r=uz\) with the multiplier from the moving coordinate
\(r=U_sz\).  The resulting nonzero row-one defect was a coordinate
mismatch and is discarded.  Keeping every object in the fixed
\((u,z)\)-chart gives the following exact law.

Write

\[
P_s=R_P(s,r)+zN_P(s,r)+O(z^2),\qquad
Q_s=R_Q(s,r)+zN_Q(s,r)+O(z^2),
\qquad r=uz.
\]

The common fixed-chart tangency multiplier is

\[
\boxed{
\Lambda_s(r)
=\frac{\partial_rR_P}{N_P}
=\frac{\partial_rR_Q}{N_Q}
=-3(s-4)\frac{\mathcal A_s(r)}{\mathcal B_s(r)},}
\]

where

\[
\begin{aligned}
\mathcal A_s(r)={}&
27r^2s^3-216r^2s^2+432r^2s
-36rs^3+288rs^2-144rs-1728r\\
&+8s^3-64s^2-96s+1152,
\\
\mathcal B_s(r)={}&
27r^2s^4-216r^2s^3+432r^2s^2
-36rs^4+288rs^3-144rs^2-1728rs\\
&+8s^4-96s^3+480s^2-2304s+6912.
\end{aligned}
\]

Let the exact source-only Hamiltonian have two-layer expansion

\[
S_s=R_S(s,r)+zN_S(s,r)+O(z^2).
\]

The coordinate-consistent covariant defect vanishes identically:

\[
\boxed{
D_S^{\rm fix}
:=R_S'-\Lambda_sN_S=0.}
\]

Every target pullback satisfies the same identity.  Hence, for

\[
T_s=8K_s(P_s,Q_s),\qquad W_s=S_s+T_s,
\]

one has

\[
\boxed{R_W'=\Lambda_sN_W}
\]

for every coefficientwise-polynomial compatible target schedule.

Write

\[
\Lambda_s=\sum_{h\ge0}s^h\Lambda_h,\qquad
R_W=\sum_{n\ge0}s^nR_{W,n},\qquad
N_W=\sum_{n\ge0}s^nN_{W,n}.
\]

The all-row law is the convolution

\[
\boxed{
R_{W,n}'=\sum_{h=0}^n\Lambda_hN_{W,n-h}.}
\]

The first multiplier coefficients are

\[
\boxed{
\Lambda_0=2-3r,\qquad
\Lambda_1=0,\qquad
\Lambda_2=\frac{9r^3-36r^2+39r-10}{48}\ne0.}
\]

Thus row one still lies on the row-zero tangent graph:

\[
R_{W,1}'=\Lambda_0N_{W,1}.
\]

The complete normal-minus-one faces at defects one and three both vanish:

\[
\boxed{
[W_0,W_0]_{n=-1}=0,\qquad
[W_0,W_1]_{n=-1}=0.}
\]

There is no covariant defect-two or defect-three payment.

### First graph-curvature face

At row two,

\[
R_{W,2}'=\Lambda_0N_{W,2}+\Lambda_2N_{W,0}.
\]

The first cross-row normal-minus-one face is therefore

\[
\boxed{
[W_0,W_2]_{n=-1}
=z^{-1}g(r),\qquad
g=\Lambda_2N_{W,0}^2.}
\]

It has total instantaneous defect five: the row-two radial contribution has
defect four and the row-zero first-normal contribution has defect one.  Over
\(\mathbb Q[r]\),

\[
\boxed{g=0\quad\Longleftrightarrow\quad N_{W,0}=0.}
\]

When \(N_{W,0}=0\), row-zero tangency makes \(R_{W,0}\) constant.  The
controlled source-zero two-jet belongs to this branch.

When \(g\ne0\), put \(f=R_{W,0}\).  Then
\(f'=\Lambda_0N_{W,0}\ne0\).  Every nonconstant row-zero radial restriction
in the exact lift category is divisible by \(r^3\), so

\[
d=\deg f\ge3.
\]

The selected radial adjoint is nonresonant at every depth:

\[
\boxed{
\operatorname{ad}_{f}^{\,k}\bigl(z^{-1}g\bigr)
=(2k-1)!!\,
z^{-1-2k}(f')^kg\ne0
\qquad(k\ge0),}
\]

with \((-1)!!=1\).

The corresponding free-Lie word also has a nonzero coefficient at every
depth in the right-Magnus logarithm of the selected affine connection
\(W_0+s^2W_2\).  If \(c_k\) is the coefficient of
\(\operatorname{ad}_{W_0}^{\,k}W_2\) at logarithmic order \(q=k+3\), then

\[
c_k=[x^k]\,
\frac{e^x(x^2-2x+2)-2}{x^2(e^x-1)}.
\]

Equivalently,

\[
\begin{aligned}
c_0&=\frac13,\\
c_k&=\frac{B_{k+1}}{(k+1)!}
&& (k\ge1\text{ odd}),\\
c_k&=-\frac{2B_{k+2}}{(k+2)!}
&& (k\ge2\text{ even}).
\end{aligned}
\]

Every Bernoulli number displayed here has positive even index, so
\(c_k\ne0\) for all \(k\).

If \(h=\deg g\), the selected radial face has limiting source derivation
rate

\[
\boxed{2(d-2)\ge2.}
\]

This proves all-depth wordwise nonresonance of the first graph-curvature
face.  It does not yet compute the complete defect-five class.  The exact
defect identity shows that the missing block has four, rather than two,
row-count types.  If \(e\) and \(c\) count row-one and row-two letters and
\(N\) is the sum of their chosen normal orders, then

\[
N+2e+4c=5.
\]

Hence the possibilities are

\[
\boxed{
(c,e,N)=(1,0,1),(0,2,1),(0,1,3),(0,0,5).}
\]

The last block is zero because a word containing only \(W_0\) brackets
\(W_0\) with itself.  First-normal tangency kills the symbol of the
two-\(W_1\) block.  The one-\(W_1\), total-normal-three block is different:
it uses the normal-two/normal-three compatibility coordinate and is not
controlled by the two-layer graph.  A direct truncated test which retains
only radial and first-normal pieces already detects this block through words
with one \(W_1\) and three selected first-normal occurrences.

Thus the two-layer calculation isolates a nonzero summand but cannot
promote it to the complete defect-five quotient.  The existing exact
two-jet replay shows the consequence: the full selected ray vanishes in the
controlled-source-zero representative while surviving in other
representatives.

The corrected implication is therefore:

- the coordinate-consistent covariant defect is zero at every parameter;
- graph motion begins with \(\Lambda_2\), so defects below five supply no
  negative-normal carrier;
- the selected defect-five radial word is nonzero at every adjoint and
  Magnus depth when \(N_{W,0}\ne0\);
- the complete quotient must also retain the one-\(W_1\), normal-three
  compatibility block.  First-normal tangency removes the two-\(W_1\)
  symbol but does not remove that block.

## Delayed action of a same-row cusp-kernel column

The remaining critical induction has a second temporal ambiguity.  At
\(s=0\), put

\[
C=4P^3-P^2-18PQ+27Q^2+4Q,
\qquad L=2-3r.
\]

In the fixed \(r=uz\) chart,

\[
C(P_0,Q_0)=-\frac{z^2}{16}(L^2-8z).
\]

Consequently every current column \(C(P_0,Q_0)G(P_0,Q_0)\) has zero
radial restriction and

\[
\Delta(H):=L^2[z^3]H-L\partial_r[z^2]H+2[z^2]H=0.
\]

It is therefore a same-row kernel after radial normalization, while its
later moving coefficients remain nonzero.

The first fixed-chart family coefficients are

\[
\begin{aligned}
P_0&=\frac{-3r^2+4r+2z}{4},
&P_1&=-\frac{r(-r^2+r+z)}8,\\
Q_0&=\frac{r(-r^2+r+z)}4,
&Q_1&=\frac{(-3r^2+4r+2z)^2}{192}.
\end{aligned}
\]

Take \(G=P^aQ^b\), put \(n=2a+3b\), and let

\[
H_1=[s^1]\bigl(P_s^aQ_s^bC(P_s,Q_s)\bigr).
\]

Its delayed radial leader is

\[
\boxed{
[r^{n+7}]R(H_1)
=\frac{27}{128}
\left(-\frac34\right)^a
\left(-\frac14\right)^b\ne0.}
\]

Thus the kernel column does move one row later.  However, the critical
\(\Delta\)-leader carries no new freedom.  If \(M_{n+7}\) is the canonical
contact-zero monomial of weight \(n+7\), and \(\alpha\) is chosen to cancel
the displayed radial leader, then the universal radial-to-compatibility
symbol gives

\[
\boxed{
[r^{n+3}]\Delta(H_1+\alpha M_{n+7}(P_0,Q_0))=0.}
\]

Indeed both terms have the same radial leader \(\kappa r^{n+7}\), and both
have compatibility leader

\[
\frac{(n+7)(n+5)(n+4)}9\,\kappa r^{n+3}.
\]

So a same-row \(CG\) kernel cannot recursively prescribe the next critical
\(\Delta\)-diagonal.  Its first possible action is strictly below that
diagonal.  Direct generalized-binomial reduction modulo
\(D=4P^3+27Q^2\), with \(a\in\{0,1,2\}\), makes the first descended
coefficient explicit.  After only the leading radial normalization,

\[
\boxed{
[r^{n+2}]\Delta(H_1+\alpha M_{n+7}(P_0,Q_0))
=\left(-\frac34\right)^a\left(-\frac14\right)^b
\frac{\kappa_a(n+3)(n+4)(n+6)}{128},}
\]

where

\[
\kappa_0=17,
\qquad
\kappa_1=\kappa_2=11.
\]

This coefficient is nonzero in every admissible residue, but it is one
critical grade lower and may be changed by lower radial normalizers.  Its
role is to certify strict descent, not to serve as the critical payment.

The right-Magnus convention does not change the first delayed critical
verdict.  In the normalized pure branch the row-zero source Hamiltonian is
zero.  A target column \(\lambda C G\) inserted at velocity row \(n\)
therefore contributes \(8\lambda H_0/(n+1)\) to the same-row source
logarithm and \(8\lambda H_1/(n+2)\) at the first delayed logarithmic row;
the possible row-zero bracket is absent.  The radial normalizer receives the
same integration factor, so the boxed critical cancellation remains exact.

After this same-row quotient, finite kernel logarithms act on later
compatibility rows through the already identified split semidirect algebra.
If

\[
\Omega_{\rm crit}=rz^2A(x)+\frac{z^3}{r}B(x),
\qquad x=sr,
\]

and

\[
J=B+\frac{3xA'+5A}{9},
\qquad \Delta(\Omega_{\rm crit})=9J,
\]

then the exact action is

\[
\boxed{
\rho(A)J=2xAJ'-3xA'J-5AJ.}
\]

For monomials this is the all-index delay symbol

\[
\boxed{
\rho(\alpha x^m)(\beta x^q)
=\alpha\beta(2q-3m-5)x^{m+q}.}
\]

It has at most one resonance for a fixed \(m\), namely
\(q=(3m+5)/2\), and is nonzero at every other coefficient.  This removes
the possibility of treating a \(CG\) current kernel as free at its next
critical row.  It does not by itself prove that the exponential of an
arbitrary finite polynomial \(A\) cannot turn the complete nonkernel series
\(J\) into a polynomial; that is the remaining finite-prefix module
question.

## Implication for the unconditional induction

This lane supplies five transitions for the root proof.

1. **Nonresonant finite face.**  Use the least-exponent formulas above as an
   injective occurrence-to-payment map.  There is no rational-amplitude
   exceptional set.  If \(2A\ge J\), its paired source radial face has rate
   at least two.
2. **Euler-homogeneous resonance.**  Do not charge the finite prefix.  Remove
   its exact finite conjugation as a boundary and restart the radial/normal
   row.  Any off-radial remainder must be routed by \(R'=L_sN\) and the
   loss-two higher-normal transition, not by parity-word nonvanishing.
3. **Defect-one seed terminal.**  Reject it as a carrier.  Its complete
   source/target coefficient is zero by the common tangency graph, including
   the tied radial Newton face.  The fixed-chart multiplier then removes
   every negative-normal face below total defect five.
4. **Defect-five graph curvature.**  Retain
   \(\Lambda_2N_{W,0}^2\) as an all-depth nonresonant candidate when
   \(N_{W,0}\ne0\), but charge it only after compiling the complete
   normal-three compatibility block.  If \(N_{W,0}=0\), descend directly
   to the successor face.
5. **Same-row kernel delay.**  A \(CG\) column has \(R=\Delta=0\) at its
   insertion row.  One row later it has a nonzero radial leader, but radial
   normalization removes its entire critical \(\Delta\)-leader.  Its first
   residue is strictly subcritical.  Any later effect on the critical
   sequence is governed by the explicit tensor-density action
   \(2xAJ'-3xA'J-5AJ\), not by a new same-row scalar control.

The parity lane leaves the pure contact-zero lower bound open.  It eliminates
generic mixed-word cancellation as a loophole and isolates an exact
zero-payment family, a coupled seed-face cancellation, the missing
normal-three part of the defect-five block, and the exact temporal action of
finite critical kernel logarithms.  Unconditional induction now reduces to
the finite-polynomial tensor-density orbit question for \(J\), rather than a
same-row \(CG\) cancellation.
