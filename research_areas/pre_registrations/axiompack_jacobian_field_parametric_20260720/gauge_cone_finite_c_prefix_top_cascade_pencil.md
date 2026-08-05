# Highest-weight self-cascade of a finite \(C\)-prefix

## Claim boundary

A row-one prefix \(\lambda Q^2C\) creates nonzero quadratic and cubic
source-Magnus shells of degrees \(33\) and \(42\).  This pencil asks whether
that mechanism is triangular in the highest target multiplier, which would
exclude cancellation by adding finitely many lower \(C\)-multiples.  It
does not assume the observed two shells continue indefinitely.

## Eigenquestion

Let

\[
H_{\rm pre}=\sum_{(a,b)\in S}\lambda_{a,b}P^aQ^bC
\]

be a nonzero finite cone-and-target-lift-compatible prefix, with
\(a+3\le2b\).  Does a maximal multiplier in \(S\) force a source-Magnus
shell whose spatial bidegree and amplitude cannot be produced by any lower
multiplier?

## Candidate mechanism

The fixed family has scalar parameter denominators and highest spatial
radial components of degrees three in \(P_s\) and four in \(Q_s\).  A
maximal multiplier should therefore have a unique highest spatial symbol
in the coefficient sequence of

\[
8P_s^aQ_s^bC(P_s,Q_s).
\]

If the first noncommuting pair and triple of those symbols are nonzero,
their Magnus coefficients are homogeneous of degrees two and three in
\(\lambda_{a,b}\).  Lower multipliers have smaller spatial symbols and
cannot cancel the resulting top bidegree.

The counterattack is cancellation between incomparable multipliers: cusp
weight, ordinary target degree, and fixed-chart spatial degree need not
order the finite support identically.  The replay must expose the actual
leading order rather than assume one.

## Discriminating replay

1. Generalize the delayed prefix harness from \(Q^2C\) to
   \(P^aQ^bC\).
2. Test the first independent admissible multipliers
   \(Q^2\), \(PQ^2\), and \(Q^3\), separately.
3. For each, isolate the first nonlinear source-Magnus top shell and its
   amplitude degree by evaluating at \(\lambda=-1,1,2\).
4. Compare top bidegrees under cusp weight, ordinary degree, and spatial
   degree.
5. Test two mixed prefixes whose multipliers are adjacent or incomparable
   in those orders.
6. If the top is triangular, derive the symbolic bidegree and coefficient
   multiplier in \(a,b\); then search for its zeros on
   \(a+3\le2b\).
7. Carry one representative far enough to distinguish an infinite adjoint
   orbit from a finite nilpotent burst.

## Success and kill conditions

The finite-prefix obstruction advances if every tested monomial has a
nonzero amplitude-homogeneous top shell, mixed prefixes are governed by a
single maximal multiplier, and the symbolic coefficient has no admissible
zeros.

It is killed by a nonzero admissible \(C\)-multiple with finite or commuting
source coefficient algebra, by exact mixed-prefix cancellation of the top
shell, or by incompatible maximal orders that prevent a triangular
argument.

Even a triangular quadratic/cubic shell is not an all-order lower bound.
Promotion requires a nonzero infinite recurrence or a finite-dimensional
classification showing that every nonzero top prefix has an unbounded
source Lie orbit.

## Exact finite outcome

For a monomial multiplier of cusp weight \(w=2a+3b\), the first three
tests give the coupled logarithmic tops

\[
\begin{array}{c|c|c}
(a,b)&\operatorname{top}\Omega^{\rm src}_6&
\operatorname{top}\Omega^{\rm src}_7\\ \hline
(0,2)&
\frac{33}{16384}u^{15}z^{18}&
-\frac{1377}{9175040}u^{19}z^{23}\\
(1,2)&
\frac{945}{524288}u^{19}z^{22}&
\frac{28431}{587202560}u^{25}z^{29}\\
(0,3)&
\frac{1023}{4194304}u^{21}z^{24}&
\frac{729}{146800640}u^{28}z^{32}.
\end{array}
\]

The bidegrees are

\[
(2w+3,2w+6),\qquad(3w+1,3w+5),
\]

and amplitudes \(-1,1,2\) verify exact quadratic and cubic homogeneity.
Mixed prefixes of unequal weights are governed by the higher weight in the
two tested adjacent pairs.

### Equal-weight countercheck

Cusp weight is not a total leading order.  The first collision is

\[
P^3Q^3,\quad Q^5,\qquad w=15,
\]

and the combination

\[
P^3Q^3+\frac{27}{4}Q^5
=\frac14Q^3(4P^3+27Q^2)
\]

cancels the naive cusp-leading symbol.  The complete coupled replay still
has nonzero tops

\[
\operatorname{top}\Omega^{\rm src}_6
=\frac{50301}{134217728}u^{31}z^{34},
\]

\[
\operatorname{top}\Omega^{\rm src}_7
=-\frac{129140163}{153931627888640}u^{44}z^{48}.
\]

Their degrees \(65,92\) are four below the monomial predictions.  Thus one
discriminant factor lowers the associated symbol but does not cancel the
finite cascade.  Any triangular statement must use the
\((4P^3+27Q^2)\)-adic leading class inside a fixed cusp weight, not cusp
weight alone.

### The prefix-only algebra is not the coupled quotient

The sparse replay
[`gauge_cone_finite_c_prefix_top_cascade.py`](gauge_cone_finite_c_prefix_top_cascade.py)
isolates the row-one prefix.  If its first three source-velocity
coefficients are \(A,B,C\), then

\[
\bigl(\Omega_6\bigr)_{\rm quadratic}=\frac1{48}[A,C],
\qquad
\bigl(\Omega_7\bigr)_{\rm cubic}
=-\frac1{5040}[A,[A,B]].
\]

For \(Q^2C\) alone these have degrees \(42,54\), not \(33,42\).
The radial and current-\(C\) normalizers cancel the larger shells.
Consequently a prefix-only Lie-algebra argument does not certify the
coupled normal form.

### First longer carry and the candidate terminal ray

For the smallest prefix \(Q^2C\), the complete logarithmic degrees through
order nine are

\[
(\varnothing,18,20,20,28,33,42,44,56).
\]

The order-nine top is

\[
\operatorname{top}\Omega^{\rm src}_9
=\frac{24057}{587202560}u^{26}z^{30}.
\]

Replacing the prefix amplitude \(1\) by \(2\) multiplies this coefficient
by \(16\), so it is exactly quartic in the prefix.  The useful additive
bigrading is

\[
G_w(a,b;q)=
\bigl(2a-(w+1)q-2,\ 2b-(w+1)q-6\bigr).
\]

At \(w=6\), the row-one top

\[
A=-\frac9{64}u^8z^{10}
\]

in logarithmic cost two is the unique grade-zero letter in the checked
rectangle.  After the finite nonterminal costs two and three, the
logarithm has one terminal ray at costs \(5,7,9\):

\[
\begin{array}{c|c|c}
q&\text{Hamiltonian exponent}&\text{coefficient}\\ \hline
5&(12,16)&189/81920\\
7&(19,23)&-1377/9175040\\
9&(26,30)&24057/587202560.
\end{array}
\]

Every row has grade \((-13,-9)\), and the exponent shift \((7,7)\)
is exactly the monomial shift under \(\operatorname{ad}_A\).  The bracket
multiplier is nonzero at every formal depth.  The cost-five coefficient is
quadratic, the cost-seven coefficient cubic, and the cost-nine coefficient
quartic in the prefix amplitude.

This identifies the correct candidate infinite orbit
\(\operatorname{ad}_A^kE_0\) at costs \(5+2k\).  It is not yet an
all-order result: coefficient survival after every later logarithm-first
normalization row still needs a closed scalar response equation.  The
finite data specifically refute extrapolation from orders six and seven:
order eight has degree only \(44\), while the next orbit term appears at
order nine.

## Projected-recurrence discriminator

The next replay will work directly in the rectangle

\[
G_6\ge(-13,-9)
\]

and carry an amplitude variable for the \(Q^2C\) prefix.  It must reproduce
the unfiltered coefficients through cost eleven before extending farther.
At the highest amplitude in cost \(5+2k\), the proposed basis is

\[
E_k=\operatorname{ad}_A^k(u^{12}z^{16}).
\]

The experiment succeeds only if:

1. all retained instantaneous and logarithmic grades are componentwise
   nonpositive;
2. after the finite costs two and three, every nonterminal logarithmic
   coefficient vanishes in the rectangle;
3. the highest-amplitude cost-\((5+2k)\) coefficient lies on \(E_k\);
4. an exact scalar recurrence or generating function has a certified
   nonzero infinite subsequence.

It is killed by a later nonterminal source, a second zero-grade letter,
failure to reproduce the unfiltered cost-eleven coefficient

\[
-\frac{111537}{1291845632}u^{33}z^{37},
\]

or a scalar response compatible with eventual termination.  Even success
for \(Q^2C\) disposes only the smallest one-\(C\) prefix; arbitrary
discriminant-adic leading classes and higher powers of \(C\) remain
separate quantifiers.

### Projected replay through cost twenty-one

The cost-aware projected Magnus recursion reproduces the unfiltered
coefficients through cost eleven exactly.  It then gives

\[
\begin{array}{c|c|c}
q&(a,b)&[u^az^b]\Omega_q^{\rm src}\\ \hline
13&(40,44)&-1644101307/24567212933120\\
15&(47,51)&43844413941/171970490531840\\
17&(54,58)&-6314193478629/19439365579079680\\
19&(61,65)&-79703784304860483/490039490203950776320\\
21&(68,72)&28509067563827533659/18532402538622138449920.
\end{array}
\]

Thus the candidate ray is nonzero for nine consecutive depths
\(k=0,\ldots,8\).  Standard rational-generating-function,
hypergeometric-ratio, and low-order polynomial-coefficient recurrence
guesses do not fit the normalized coefficients.

With a symbolic prefix amplitude \(\lambda\), the entire retained
logarithmic ray is homogeneous:

\[
[E_k]\Omega_{5+2k}^{\rm src}
=d_k\lambda^{k+2}.
\]

The leading-amplitude controls have fixed width.  At even target row \(2k\)
the \(C\)-multipliers occupy only cusp weights

\[
7k-2,\quad 7k-1,\quad 7k,
\]

and at the following odd row they occupy only radial weights

\[
7k+6,\quad7k+7.
\]

The first missing semigroup columns are simply absent; no extra source
grade enters.  This converts the remaining all-order problem into a
finite-width weight recurrence with a periodic canonical-monomial basis.
The first proposed \(3\)-adic law does not survive a held-out depth.  At
depth ten its predicted valuation is \(23\), while the exact valuation is
\(22\).  The useful invariant is instead the finite-width response itself.

## Closed finite-width reduction for \(Q^2C\)

Let \(T_k,C_k,E_k\) be the three coefficients of
\(\operatorname{ad}_{L_2}^{k-1}L_3\) that can reach the terminal quotient.
Their grades are respectively

\[
(-13,-9),\qquad(-9,-7),\qquad(-5,-5).
\]

The only pieces of \(L_2\) that connect these states have grades
\((0,0)\), \((-4,-2)\), and \((-8,-4)\).  Direct monomial bracketing gives

\[
\begin{pmatrix}T_{k+1}\\ C_{k+1}\\ E_{k+1}\end{pmatrix}
=
\begin{pmatrix}
-9(7k-18)/32&39(7k-6)/32&-175k/16\\
0&-9(7k-12)/32&39(7k-2)/32\\
0&0&-9(7k-6)/32
\end{pmatrix}
\begin{pmatrix}T_k\\ C_k\\ E_k\end{pmatrix}.
\]

This three-state reduction is exact in the quotient, rather than a support
guess.  Every connection grade is componentwise nonpositive.  The other
two \(L_3\) grades would require an \(L_2\) increment with second component
zero to reach \((-13,-9)\), and no such negative grade occurs.  A terminal
logarithmic term bracketed with any negative grade leaves the rectangle,
while two terminal terms do so as well.  Consequently only the zero-grade
letter acts on earlier terminal terms, and the terminal feedback is
linear.  The two lower current seed columns have zero \(T,C\) coordinates;
the highest column is annihilated by the functional below.  These support
facts hold at every amplitude index.

For

\[
(\tau_k,\kappa_k,\epsilon_k)
=\frac{(-1)^{k-1}}{k!}(T_k,-C_k,E_k),
\]

the corresponding transition matrix is entrywise positive for \(k\ge3\).
Moreover,

\[
\kappa_k=\frac{21k+8}{9}\epsilon_k.
\]

The current \(C\)-seed column has canonical multiplier

\[
(p,q)=
\begin{cases}
(0,7k/3),&k\equiv0\pmod3,\\
(2,(7k-4)/3),&k\equiv1\pmod3,\\
(1,(7k-2)/3),&k\equiv2\pmod3.
\end{cases}
\]

In the normalized product \(P^pQ^qC\), its relevant coefficients are

\[
a_{2,1}=-\frac{21k+8}{9},
\qquad
a_{4,2}
=\frac{147k^2+49k+\delta_{k\bmod3}}{54},
\]

where

\[
(\delta_0,\delta_1,\delta_2)=(0,12,6).
\]

Thus the exact seed cokernel is

\[
\ell_k(V)
=V_{(-13,-9)}+\chi_kV_{(-9,-7)},
\qquad
\chi_k=
\frac{147k^2+49k+\delta_{k\bmod3}}
{6(21k+8)}.
\]

Put

\[
D_k=\tau_k-\chi_k\kappa_k.
\]

Symbolic reduction in the three residue classes gives

\[
D_{k+1}=a_kD_k+\gamma_k\kappa_k,
\qquad
a_k=\frac{9(7k-18)}{32(k+1)},
\]

with

\[
\gamma_k=
\begin{cases}
0,&k\equiv0\pmod3,\\[2mm]
\dfrac{189(k-2)}{32(k+1)(21k+8)},
&k\equiv1\pmod3,\\[3mm]
\dfrac{27(7k-10)}{32(k+1)(21k+8)},
&k\equiv2\pmod3.
\end{cases}
\]

Since

\[
D_3=\frac{81}{16384}>0,
\]

the finite-core forcing is nonzero at every later amplitude.

## Closed scalar response

Let \(n=k-2\) be terminal-ray depth, let

\[
p_0=1,\qquad
p_n=\frac98\left(-\frac{63}{32}\right)^{n-1}
\left(\frac37\right)_{n-1}\quad(n\ge1)
\]

be the coefficient in
\(\operatorname{ad}_A^n(u^{12}z^{16})\), and normalize the terminal
logarithmic coefficient by \(p_n\).  If

\[
E(x)=\sum_{n\ge0}e_nx^n,
\qquad
H_n=-\frac{D_{n+2}}{p_n},
\qquad
H(x)=\sum_{n\ge0}H_nx^n,
\]

then the exact forward-right-`dexp` feedback kernel is

\[
R_{n,j}
=(-1)^{n-j+1}
\frac{2j+3}{(2n+5)(n-j+1)!}.
\]

Equivalently, with \(f(x)=(1-e^{-x})/x\),

\[
\boxed{
2xf(x)E'(x)+(2+3f(x))E(x)=H(x).
}
\]

The regular solution is

\[
\boxed{
E(x)=\frac{xJ(x)}{e^x-1},
\qquad
J(x)=
\frac1{2x^{5/2}}
\int_0^x e^t t^{3/2}H(t)\,dt.
}
\]

This identity reproduces every coefficient of the full projected replay
through the declared finite depth.

## Nontermination by a certified response pole

The positive three-state system also supplies an elementary growth bound.
For \(k\ge3\),

\[
0<D_k\le\tau_k\le10k^2\epsilon_k,
\]

and

\[
\epsilon_k=
\frac9{256}
\left(\frac{63}{32}\right)^{k-1}
\frac{(1/7)_{k-1}}{k!}.
\]

Pairing the factors in
\((1/7)_{k-1}/(3/7)_{k-3}\) leaves only two unpaired factors, each less
than \(k\).  Hence

\[
\boxed{
|H_n|
\le
\frac{2(n+2)^4}{(n+2)!}.
}
\]

Therefore \(H\) and \(J\) are entire.  It remains to decide whether \(J\)
cancels every nonzero zero of \(e^x-1\).

The replay now includes a rational interval certificate at \(x=2\pi i\).
It encloses \(\pi\) with Machin's formula

\[
\pi=16\arctan(1/5)-4\arctan(1/239)
\]

and alternating-series remainders.  The first one hundred exact
coefficients of \(J\), together with the displayed all-order majorant,
give

\[
\boxed{\operatorname{Im}J(2\pi i)>\frac1{200}.}
\]

For the omitted tail the coefficient bound is

\[
M_N=
\frac{8\,14^N(N+2)^4}{(2N+5)(N+2)!},
\]

and at \(N=100\) its successive ratio is less than \(1/6\).  Thus the
interval statement includes the infinite tail rather than relying on a
floating-point evaluation.

It follows that \(E\) has a nonremovable pole at \(2\pi i\).  In
particular, \(E\) is not a polynomial, so infinitely many \(e_n\) are
nonzero.  Since every \(p_n\) is nonzero in characteristic zero, the
complete moving connection with the row-one \(Q^2C\) prefix has infinitely
many nonzero terminal Hamiltonians

\[
u^{12+7n}z^{16+7n}
\]

at costs \(5+2n\).  This closes the \(Q^2C\) escape candidate and yields a
limiting spatial rate seven on its leading-amplitude ray.

The conclusion still does not quantify over arbitrary finite
discriminant-adic \(C\)-prefixes or prefixes involving higher powers of
\(C\).  Those are the remaining finite-prefix escape classes.

## First monomial counterattack to the weight-six mechanism

The strongest weight-only extrapolation is false.  The exact coupled
cost-three normalizer sends

\[
Q^4C
\]

to zero: its entire prefix-dependent cost-three logarithmic coefficient
vanishes, not merely its proposed terminal monomial.  The same calculation
vanishes for pure \(Q^bC\) through every tested \(b\ge4\).  Target-side,
the first covariant derivative under the seed Hamiltonian remains inside
the cone and can be supplied by the current row.  Thus the \(Q^2C\)
three-state forcing is not universal across cusp weights.

The deeper quotient nevertheless excludes \(Q^4C\).  With

\[
G(a,b;q)=(2a-13q-2,\ 2b-13q-6),
\]

the zero-grade letter is

\[
A=-\frac9{1024}u^{14}z^{16}
\]

at cost two, while the first surviving terminal velocity is

\[
\frac5{1024}u^{14}z^{17}
\]

at cost four and grade \((-26,-24)\).  The complete projected replay has
no later terminal velocity input at the first nonlinear row and gives

\[
[u^{27}z^{30}]\Omega^{\rm src}_6
=\frac{105}{4194304}.
\]

In this quotient every negative-grade outer letter exits, and the current
normalizer has no highest-amplitude nonterminal shell.  The terminal
response is therefore

\[
\phi_3(x)
=\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt.
\]

For positive depth \(k\),

\[
[x^k]\phi_3(x)=\frac{B_{k+1}}{2(k+1)!},
\]

and

\[
[A,E_k]
=\frac{9(7-13k)}{512}E_{k+1},
\qquad
E_k=u^{14+13k}z^{17+13k}.
\]

Every odd \(k\) is consequently nonzero, giving an infinite subsequence
at costs \(6+4m\) with limiting spatial rate thirteen.  The replay is
[`gauge_cone_q4c_terminal_response.py`](gauge_cone_q4c_terminal_response.py),
and the theorem boundary is
[`gauge_cone_q4c_terminal_response_result.md`](gauge_cone_q4c_terminal_response_result.md).

The successor invariant is now the first covariant derivative that exits
the target cone, together with the first surviving source grade.  Raw cusp
weight and the cost-three seed are each insufficient.

### Exact pure-\(Q\) cone-exit depth

The target half of that invariant closes for every

\[
G_b=Q^bC,\qquad b\ge2.
\]

Let

\[
H_0=-\frac1{36}P^3-\frac14Q^2.
\]

On a monomial, the \(P^3\) branch of
\(\operatorname{ad}_{H_0}\) is

\[
P^aQ^q\longmapsto
\frac q{12}P^{a+2}Q^{q-1}.
\]

The unique largest-\(P\) monomial of \(G_b\) is \(4P^3Q^b\).
After \(n\) consecutive \(P^3\) branches it becomes

\[
\frac{4(b)_n}{12^n}P^{3+2n}Q^{b-n}.
\]

Its cone margin is

\[
2(b-n)-(3+2n)=2b-3-4n.
\]

Every \(Q^2\) branch raises this margin by three, and every other initial
monomial has larger margin.  Hence all terms remain in the cone for
\(n<\lfloor b/2\rfloor\), while the displayed nonzero monomial leaves it
at

\[
\boxed{n=\lfloor b/2\rfloor.}
\]

This is replayed by
[`gauge_cone_qb_c_covariant_exit.py`](gauge_cone_qb_c_covariant_exit.py).
It explains why \(Q^2C\) produces an immediate cost-three core and why
\(Q^4C\) is transported through one current row before its deeper
cost-four seed appears.

The first depth-three countercheck prevents a stronger extrapolation.
For \(Q^6C\), the target cone-exit depth is three, but the canonical
radial plus one-\(C\) normalizer already leaves the prefix-dependent
cost-four velocity

\[
\frac{29}{65536}u^{20}z^{23}
\]

and logarithmic coefficient \(29u^{20}z^{23}/262144\), at grade
\((-38,-36)\) for the slope-nineteen grading.  Thus target cone-exit depth
does not alone determine the first source seed.  The intervening source
transport and the restricted current normalization matter.  A richer
covariantly transported target prefix may still cancel this earlier class.

The remaining source-side task is therefore a coupled quotient: compare
the full covariant target continuation with the source normalizer up to
the target exit depth, then prove that the first surviving class has a
nonterminating Magnus response.  Only after that step can the argument
advance to mixed discriminant classes.

### Covariant-continuation discriminator

For the controlled target background

\[
K_s=a(s)P^3+b(s)PQ-\frac14Q^2,
\]

let \(G_s=\sum s^jG_j\) solve the formal target equation

\[
\partial_sG_s+\{K_s,G_s\}=0,
\qquad
G_0=Q^6C.
\]

The target cone-exit theorem predicts that \(G_1,G_2\) are cone-valued,
while \(G_3\) has a nonzero class outside the cone.  The next replay will:

1. derive \(G_1,G_2,G_3\) exactly from \(a(s),b(s)\);
2. insert \(G_1,G_2\) as prescribed later target rows, in addition to the
   row-one \(Q^6C\) prefix;
3. rerun the logarithm-first radial and one-\(C\) normalizer;
4. test whether the cost-four class
   \(29u^{20}z^{23}/65536\) vanishes;
5. locate the first surviving prefix-dependent source grade.

If the cost-four class vanishes, the target cone-exit depth is the correct
clock only after covariant completion.  If it survives, it represents a
source-transport cokernel invisible to the target cone quotient.  Either
outcome replaces the current ambiguity with a coupled invariant.

### Pre-registered cost-six response test

Suppose the covariantly completed replay leaves the cost-four velocity

\[
B=\frac{29}{65536}u^{20}z^{23}
\]

in terminal grade \((-38,-36)\).  The cost-two grade-zero logarithmic
letter is

\[
A=-\frac9{16384}u^{20}z^{22}.
\]

On the prospective terminal orbit

\[
E_k=u^{20+19k}z^{23+19k}
\]

the exact source bracket gives

\[
[A,E_k]=\frac{9(10-19k)}{8192}E_{k+1}.
\]

If the completed connection has no later instantaneous input in this
terminal quotient, the right-Magnus response must again be

\[
\phi_3(x)=
\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt.
\]

It predicts the cost-four logarithmic seed

\[
\frac{29}{262144}u^{20}z^{23}
\]

and the cost-six coefficient

\[
\boxed{
\frac{435}{2147483648}u^{39}z^{42}}.
\]

The next full projected replay will include the exact cone-valued
\(G_1,G_2\) continuation and extract both the cost-six instantaneous and
logarithmic terminal rows.  A nonzero later instantaneous term kills the
one-input \(\phi_3\) model and requires a larger finite core.  A zero
instantaneous term with a different logarithmic coefficient kills the
claimed quotient projection.  Agreement establishes the first two rows
of the proposed all-order odd-depth response, but the infinite
subsequence will still require the exact orbit recurrence.

### Covariant-continuation outcome

The exact replay agrees with every pre-registered coefficient.  The
covariant target supports at depths zero through three have sizes

\[
(5,7,12,16).
\]

The first two transported rows are cone-valued, whereas

\[
\operatorname{bad}(G_3)
=-\frac5{108}P^9Q^3+\frac5{432}P^8Q^3.
\]

After inserting all terms of \(G_1\) and \(G_2\), the terminal source
rows are

\[
\begin{aligned}
\operatorname{term}V_4
&=\frac{29\lambda}{65536}u^{20}z^{23},\\
\operatorname{term}V_6&=0,\\
\operatorname{term}\Omega_4
&=\frac{29\lambda}{262144}u^{20}z^{23},\\
\operatorname{term}\Omega_6
&=\frac{435\lambda^2}{2147483648}u^{39}z^{42}.
\end{aligned}
\]

Thus the cost-four class survives the complete cone-valued covariant
runway and the one-input response passes its first nonlinear test.  The
exact orbit multiplier is nonzero at every integral depth, while
\([x^k]\phi_3=B_{k+1}/(2(k+1)!)\) for \(k\ge1\).  Every odd depth
therefore survives, giving exponents

\[
(39+38m,42+38m)
\]

at costs \(6+4m\), with limiting source rate nineteen.  The executable
certificate and theorem boundary are
[`gauge_cone_q6c_covariant_source_cokernel.py`](gauge_cone_q6c_covariant_source_cokernel.py)
and
[`gauge_cone_q6c_covariant_source_cokernel_result.md`](gauge_cone_q6c_covariant_source_cokernel_result.md).

This closes the \(Q^6C\) monomial counterattack.  Uniform transfer in
\(b\), cancellation among mixed one-\(C\) leading terms, and higher
\(C\)-adic powers remain separate questions.

### Uniform pure-\(Q\) cost-four transfer test

For

\[
G_b=Q^bC
\]

the zero-grade letter has the parity-sensitive uniform candidate

\[
A_b=\frac{(-1)^{b+1}9}{2^{2b+2}}
u^{3b+2}z^{3b+4}.
\]

The first common delayed terminal slot for \(b\ge4\) is

\[
B_b\,u^{3b+2}z^{3b+5}
\]

at cost four and grade

\[
(-6b-2,-6b)
\]

for the slope-\((3b+1)\) grading.  Direct bracketing would then give

\[
[A_b,E_{b,k}]
=\frac{(-1)^b9
\bigl(3b+2-2(3b+1)k\bigr)}
{2^{2b+2}}E_{b,k+1},
\]

where

\[
E_{b,k}
=u^{3b+2+(3b+1)k}z^{3b+5+(3b+1)k}.
\]

The multiplier cannot vanish at an integral \(k\ge0\).  Thus a uniform
nonzero formula for \(B_b\) would close every pure-\(Q\) prefix with
\(b\ge4\) by the same odd Bernoulli response.

The discriminating calculation will replay exact \(b\)-values with every
covariant coefficient available through target order three.  It will
extract \(B_b\), normalize away the evident power of two, and seek a
low-degree or residue-class formula.  A sampled zero kills cost four as
the uniform transfer slot and redirects that exponent to its later
target-exit class.  A fitted formula is not a theorem: promotion requires
derivation from the symbolic pullback and current-normalizer equations,
plus a proof that its numerator has no integral zero for \(b\ge4\).

The symbolic quotient has now produced the candidate identity

\[
B_b=\frac{(-1)^b(9b+4)}{2^{2b+5}}
\qquad (b\ge6).
\]

It remains to close the exceptional \(b=5\) response, since its second
covariant coefficient is already outside the target cone and is
therefore omitted.  With

\[
A_5=\frac9{4096}u^{17}z^{19},
\qquad
B_5=-\frac{49}{32768}u^{17}z^{20},
\]

the one-input response predicts zero cost-six terminal velocity and

\[
\boxed{
[u^{33}z^{36}]\Omega^{\rm src}_6
=\frac{2499}{1073741824}}.
\]

Failure of either assertion separates \(b=5\) from the uniform
cost-four response.  Agreement joins it to the already certified
\(b=4\) case and the symbolic \(b\ge6\) quotient.

### Missing immediate-exit exponent \(b=3\)

The cost-four theorem begins at \(b=4\), so the pure-\(Q\) family still
requires \(Q^3C\).  Its complete coupled cost-three row is nonzero, with
top term

\[
-\frac{27}{2048}u^{12}z^{14}.
\]

For the slope-ten grading, the zero-grade letter and terminal velocity
candidate are

\[
A_3=\frac9{256}u^{11}z^{13},
\qquad
V_{\rm term}=-\frac{81}{2048}u^{12}z^{14},
\]

at costs two and three.  If no later instantaneous terminal input enters
the quotient, the response is

\[
\phi_2(x)=
\frac{x}{e^x-1}\int_0^1t^2e^{t^2x}\,dt.
\]

Since

\[
[A_3,E_k]=\frac{9(1+10k)}{128}E_{k+1},
\qquad
E_k=u^{12+10k}z^{14+10k},
\]

the first nonlinear prediction is zero terminal velocity at cost five
and

\[
\boxed{
[u^{22}z^{24}]\Omega^{\rm src}_5
=-\frac{243}{2621440}}.
\]

A disagreement requires a coupled finite core analogous to \(Q^2C\).
Agreement reduces all-order nontermination to the analytic behavior of
\(\phi_2\).

The first nonlinear replay disagrees in the strongest possible way.  It
finds

\[
\operatorname{term}V_5
=\frac{243}{524288}u^{22}z^{24},
\qquad
\operatorname{term}\Omega_5=0.
\]

This is exactly the right-forward-`dexp` coefficient generated by the
finite terminal logarithm

\[
\Omega_{\rm trial}
=\frac9{256}s^2u^{11}z^{13}
-\frac{27}{2048}s^3u^{12}z^{14}.
\]

The next discriminator is therefore reversal rather than pole analysis.
Forward `dexp` predicts

\[
\operatorname{term}V_7
=-\frac{8019}{67108864}u^{32}z^{34},
\qquad
\operatorname{term}\Omega_7=0.
\]

Agreement through cost seven would identify a finite-logarithm candidate
in the terminal quotient.  It would not yet construct a bounded full
source logarithm: every other retained grade and the freedom in later
cone rows would still require an exact all-order comparison.

The cost-seven replay agrees exactly:

\[
\operatorname{term}V_7
=-\frac{8019}{67108864}u^{32}z^{34},
\qquad
\operatorname{term}\Omega_7=0.
\]

The next forward-`dexp` coefficient is

\[
\operatorname{term}V_9
=\frac{1515591}{34359738368}u^{42}z^{44},
\qquad
\operatorname{term}\Omega_9=0.
\]

This is the third nonlinear discriminator.  Agreement would justify
promoting the finite terminal-log model as a recurrence candidate;
failure would locate the first delayed feedback state.  Neither outcome
settles lower source grades.

The cost-nine row also agrees exactly.  The terminal velocity is

\[
\frac{1515591}{34359738368}u^{42}z^{44},
\]

and the terminal logarithm is zero.  The four matched costs
\(3,5,7,9\) are recorded by
[`gauge_cone_q3c_finite_terminal_log.py`](gauge_cone_q3c_finite_terminal_log.py)
and
[`gauge_cone_q3c_finite_terminal_log_result.md`](gauge_cone_q3c_finite_terminal_log_result.md).

The next counterattack descends within the same projected grade window.
It will inspect every prefix-dependent logarithmic row retained above
\((-8,-8)\), not only the terminal monomial.  If all rows beyond cost
three vanish, the finite model controls this entire quotient through the
computed cap.  Any surviving nonterminal grade becomes the successor
obstruction and must be replayed with its own adjoint orbit.  Grades
strictly below the window remain outside either conclusion.

The widened readout finds no such survivor.  Every prefix-dependent
logarithmic row in the componentwise window

\[
\Gamma\ge(-8,-8)
\]

vanishes after cost three through cost nine.  The complete retained
logarithm consists of nine cost-two monomials and the single cost-three
terminal monomial, and its forward `dexp` reproduces every retained
velocity row.

The next descent is the additive window

\[
\Gamma\ge(-16,-16),
\]

which contains one bracket of the lowest cost-two grade with the
cost-three terminal class.  The finite-log model again predicts no
prefix-dependent logarithmic rows after cost three.  A replay through
cost seven will either confirm the first lower layer or expose the first
new grade, exponent, and coefficient.  This descent is necessary before
the finite-prefix candidate can be compared with the all-order
obstructions in the other \(Q^bC\) classes.

The first lower layer kills the finite-log escape.  The enlarged replay
has a new prefix-dependent logarithmic orbit at grade
\((-16,-12)\):

\[
\begin{aligned}
\operatorname{term}_{(-16,-12)}\Omega_5
&=\frac{729}{2621440}u^{18}z^{22},\\
\operatorname{term}_{(-16,-12)}\Omega_7
&=\frac{729}{146800640}u^{28}z^{32}.
\end{aligned}
\]

The zero-grade letter acts on

\[
F_k=u^{18+10k}z^{22+10k}
\]

by

\[
[A_3,F_k]=\frac{9(5k-2)}{64}F_{k+1},
\]

which never vanishes at integral depth.  Thus the leading-window
cancellation postponed rather than removed the source obstruction.

The next replay will extract cost nine in the same grade.  A nonzero
coefficient supplies a third point for the scalar response and tests
whether the ratio is governed only by the zero-grade adjoint.  A zero
coefficient would reopen a periodic-support possibility, but would not
restore a finite logarithm because costs five and seven are already
nonzero.

The cost-nine coefficient is

\[
\frac{190269}{300647710720}u^{38}z^{42},
\]

so the orbit continues.  The reduced quotient has five current
\(C\)-columns but two affine control directions; its terminal
coefficient is independent of both.  The exact cokernel coefficient is

\[
\chi_k
=-\frac{150k^2+635k+673+\delta_{k\bmod3}}{27},
\qquad
(\delta_0,\delta_1,\delta_2)=(0,-3,3).
\]

Only three adjoint states feed this cokernel.  Their triangular
recurrence yields the forcing bound

\[
|H_k|\le
\frac{130(k+2)^4}{(k+2)!}.
\]

After orbit division, the scalar response again satisfies

\[
2xfE'+(2+3f)E=H,
\qquad
f=\frac{1-e^{-x}}x,
\qquad
E=\frac{xJ}{e^x-1}.
\]

An exact one-hundred-coefficient rational interval calculation proves

\[
\operatorname{Im}J(2\pi i)>\frac1{4000}.
\]

Therefore the lower-grade \(Q^3C\) response has infinite support and
limiting rate ten.  The replay and theorem boundary are
[`gauge_cone_q3c_lower_terminal_recurrence.py`](gauge_cone_q3c_lower_terminal_recurrence.py)
and
[`gauge_cone_q3c_lower_terminal_recurrence_result.md`](gauge_cone_q3c_lower_terminal_recurrence_result.md).

Together with \(Q^2C\) and the uniform cost-four theorem for
\(Q^bC,\ b\ge4\), this completes the pure-\(Q\) one-\(C\) monomial
family.  The live one-\(C\) problem is cancellation among mixed leading
terms.

## Mixed leading quotient modulo the cusp discriminant

At a fixed cusp weight, put

\[
D=4P^3+27Q^2.
\]

The first equal-weight cancellation is exactly

\[
P^3Q^3+\frac{27}{4}Q^5=\frac14Q^3D.
\]

Thus arbitrary weighted-homogeneous multipliers should first be divided
by their maximal power of \(D\).  Modulo \(D\), every class has a unique
representative whose \(P\)-exponent lies in

\[
a\in\{0,1,2\}.
\]

The \(a=0\) representatives are the pure-\(Q\) family just completed.
The next discriminating replay will classify the \(a=1,2\) monomials

\[
P^aQ^bC,\qquad a+3\le2b,
\]

under the complete cost-three current normalizer.

The first test asks whether their coupled cost-three rows ever vanish as
\(b\) grows.  If they remain nonzero, the replay will extract the
uniform grade, adjoint multiplier, and response coefficient.  If a
kernel appears, that residue class must be followed to its first deeper
source grade as in the pure-\(Q\) \(b\ge4\) and \(b=3\) cases.  A theorem
modulo \(D\) still will not handle multipliers divisible by \(D\);
finite \(D\)-adic depth is the successor layer.

The exact cost-three scan finds no kernel.  In the stable ranges,

\[
\begin{aligned}
[u^{3b+1}z^{3b+5}]\Omega_3(PQ^bC)
&=\frac{(-1)^{b+1}9b}{2^{2b+7}},
&&b\ge4,\\
[u^{3b+3}z^{3b+7}]\Omega_3(P^2Q^bC)
&=\frac{(-1)^b27b}{2^{2b+9}},
&&b\ge3.
\end{aligned}
\]

The low \(PQ^2C,PQ^3C\) cases are also nonzero but occupy the earlier
normal-two slot.

A nonzero cost-three row can still be a finite leading cancellation, as
\(Q^3C\) showed.  The next held-out test therefore uses \(PQ^4C\) and
\(P^2Q^3C\).  Their finite-log forward-`dexp` predictions are,
respectively,

\[
\begin{aligned}
[u^{28}z^{32}]V_5&=-\frac{4617}{33554432},
&[u^{28}z^{32}]\Omega_5&=0,\\
[u^{26}z^{30}]V_5&=-\frac{59049}{67108864},
&[u^{26}z^{30}]\Omega_5&=0.
\end{aligned}
\]

Agreement places the residue class in a finite leading window and
requires a lower-grade descent.  A nonzero logarithmic remainder gives
the first response seed directly.

Both replays take the second branch.  Their cost-five terminal velocities
are zero, while

\[
\begin{aligned}
[u^{28}z^{32}]\Omega_5(PQ^4C)
&=\frac{4617}{167772160},\\
[u^{26}z^{30}]\Omega_5(P^2Q^3C)
&=\frac{59049}{335544320}.
\end{aligned}
\]

These are exactly the first positive-depth coefficients of

\[
\phi_2(x)
=\frac{x}{e^x-1}\int_0^1t^2e^{t^2x}\,dt.
\]

Since \([x^2]\phi_2=-1/1260\), the next predictions are zero terminal
velocity at cost seven and

\[
\begin{aligned}
[u^{43}z^{47}]\Omega_7(PQ^4C)
&=\frac{41553}{1202590842880},\\
[u^{40}z^{44}]\Omega_7(P^2Q^3C)
&=\frac{1594323}{2405181685760}.
\end{aligned}
\]

Agreement will identify the stable mixed residue response.  The
all-order step must additionally show that the adjoint multiplier never
vanishes and that \(\phi_2\) is not a polynomial.

Both cost-seven coefficients agree.  The stable \(a=1,2\) residue
classes therefore have the exact \(\phi_2\) response through two
positive depths.  Symbolic reduction gives the zero-grade adjoint
multipliers

\[
\begin{aligned}
[A,F_k(PQ^bC)]&=
c_{1,b}\,2\{3(b+1)k-(3b+7)\}F_{k+1},\\
[A,F_k(P^2Q^bC)]&=
c_{2,b}\,2\{(3b+5)k-3(b+3)\}F_{k+1}.
\end{aligned}
\]

Their only roots are

\[
\frac{3b+7}{3(b+1)},\qquad
\frac{3(b+3)}{3b+5},
\]

both strictly between one and two.  No integral adjoint depth is
killed.  Moreover,

\[
I_2(x)=\int_0^1t^2e^{t^2x}\,dt
=\frac{e^x-I_0(x)}{2x}.
\]

At \(x=2\pi i\), \(\operatorname{Re}I_0(x)<1\), so \(I_2(x)\ne0\);
the apparent pole of \(\phi_2\) is not removable.  Thus both stable
mixed residue responses have infinite support, with limiting rates
\(3b+3\) and \(3b+5\).  The executable certificate and theorem boundary
are
[`gauge_cone_mixed_residue_phi2.py`](gauge_cone_mixed_residue_phi2.py)
and
[`gauge_cone_mixed_residue_phi2_result.md`](gauge_cone_mixed_residue_phi2_result.md).

The remaining mixed representatives are the low normal-two cases
\(PQ^2C\) and \(PQ^3C\).  Their first nonlinear discriminator compares
the finite-log and inverse-response branches:

\[
\begin{array}{c|c|c}
&\text{finite-log }V_5&\text{zero-}V_5\text{ logarithm}\\ \hline
PQ^2C&
243/262144&
-243/1310720\\
PQ^3C&
729/8388608&
-729/41943040.
\end{array}
\]

Any third outcome creates a new coupled core.  These two checks are
required before the mixed quotient modulo \(D\) is complete.

Both low cases take the finite-log branch:

\[
\begin{aligned}
\operatorname{term}V_5(PQ^2C)&=\frac{243}{262144},&
\operatorname{term}\Omega_5(PQ^2C)&=0,\\
\operatorname{term}V_5(PQ^3C)&=\frac{729}{8388608},&
\operatorname{term}\Omega_5(PQ^3C)&=0.
\end{aligned}
\]

Their leading windows therefore repeat the \(Q^3C\) cancellation.  The
next discriminating replay descends from grades \((-11,-11)\) and
\((-14,-14)\) to the additive windows \((-22,-22)\) and
\((-28,-28)\).  A nonzero logarithmic row after cost three kills the
low-residue escape; a second finite window requires another descent.

The descent takes the first branch.  The first surviving rows occur
already at cost four, at the slightly sharper terminal grades
\((-22,-20)\) and \((-28,-26)\):

\[
\begin{aligned}
[u^8z^{11}]\Omega_4(PQ^2C)&=-\frac{1067}{6144},\\
[u^{11}z^{14}]\Omega_4(PQ^3C)&=\frac{2177}{24576}.
\end{aligned}
\]

At cost six, the same grade orbits contain

\[
\begin{aligned}
[u^{17}z^{20}]\Omega_6(PQ^2C)&=\frac{56385}{524288},\\
[u^{23}z^{26}]\Omega_6(PQ^3C)&=\frac{1081251}{67108864}.
\end{aligned}
\]

This rules out a second finite leading window, but is not yet an
all-order certificate: delayed radial and \(C\)-normalizer columns both
feed these wider quotients.  The required successor is a finite-width
recurrence retaining those delayed current states.

## Positive discriminant depth

After the two low residue recurrences, the next identity question is
whether divisibility by

\[
D=4P^3+27Q^2
\]

can erase the terminal transfer.  Before constructing an all-depth
recurrence, scan the exact first coupled quotient for

\[
D^dP^aQ^bC,\qquad d=1,2,\quad a\in\{0,1,2\},
\]

using binomially expanded prefix terms and the complete cost-three
normalizer.  The discriminating outcomes are:

1. a nonzero row at the old coupled cost, which suggests a symbolic
   \(D\)-adic transfer law;
2. exact cancellation followed by a new fixed lower grade, which
   requires a triangular \(D\)-depth recurrence; or
3. cancellation through every retained grade, which is evidence for a
   finite-prefix escape but remains bounded until an exact identity is
   found.

The scan is diagnostic only.  No result at \(d=1,2\) will be promoted
as an all-depth statement.

The local generalized-binomial quotient improves this finite scan.  For
every \(d\ge2\), it gives

\[
\boxed{
[u^Rz^{R+4}]\Omega_3
=
\left(-\frac14\right)^b
\left(-\frac34\right)^a
\frac3{64}\binom d2
\left(\frac{27}{8}\right)^d},
\qquad
R=3b+2a+5d+1.
\]

All nine \((a,d\bmod3)\) canonical-control classes reduce to the same
normalized coefficient \(-\binom d2/12\).  Depth one has the separate
identity

\[
[u^Rz^{R+4}]\Omega_3
=
\left(-\frac14\right)^b
\left(-\frac34\right)^a
\frac{-9(9b+26a-6a^2)}{512},
\qquad
R=3b+2a+5.
\]

Both formulas are nonzero throughout their cone ranges.  They certify
the first quotient at every positive \(D\)-adic depth, but not its
Magnus tail.

The first tail discriminator uses \(D^2Q^5C\).  Its zero-grade letter and
cost-three seed are

\[
A=\frac{6561}{262144}u^{27}z^{29},
\qquad
F=-\frac{2187}{4194304}u^{26}z^{30}.
\]

If all later terminal instantaneous rows vanish, the right-Magnus
response is again

\[
\phi_2(x)=
\frac{x}{e^x-1}\int_0^1t^2e^{t^2x}\,dt,
\]

with adjoint multiplier

\[
[A,F_k]
=\frac{6561(13k-14)}{65536}F_{k+1}.
\]

The held-out cost-five and cost-seven predictions are therefore

\[
\begin{aligned}
[u^{52}z^{56}]\Omega_5
&=\frac{100442349}{1374389534720},\\
[u^{78}z^{82}]\Omega_7
&=\frac{31381059609}{180143985094819840},
\end{aligned}
\]

with zero terminal velocity at both costs.  Agreement would prove the
all-order tail for this representative, not yet uniformly in
\((a,b,d)\).  Any nonzero terminal velocity requires a new response
core.

Both descents expose logarithmic rows.  The sparsest persistent
candidates are

\[
\begin{aligned}
\Omega_{5+2n}(PQ^2C)
&=d^{(2)}_n u^{16+9n}z^{20+9n},
&&\Gamma=(-15,-11),\\
\Omega_{5+2n}(PQ^3C)
&=d^{(3)}_n u^{22+12n}z^{26+12n},
&&\Gamma=(-18,-14).
\end{aligned}
\]

Their first two coefficients are

\[
\begin{array}{c|cc}
&d_0&d_1\\ \hline
PQ^2C&
3159/1310720&
28431/587202560\\
PQ^3C&
729/2621440&
-6561/4697620480.
\end{array}
\]

After division by the respective adjoint multipliers

\[
\alpha^{(2)}_n=\frac{27(9n-4)}{128},
\qquad
\alpha^{(3)}_n=\frac{27(1-3n)}{128},
\]

both depth-one ratios equal \(-1/42\).  An exploratory exact prefix
through depth ten suggests a stronger common quotient.  If \(q_2\) and
\(q_3\) denote

\[
q_2=\frac{3159}{131072},
\qquad
q_3=\frac{729}{262144},
\]

the candidate normalized forcing is

\[
H_n^{(j)}=\frac{(-1)^nq_j}{(n+2)!}.
\]

The corresponding right-`dexp` response must satisfy

\[
2xfE'+(2+3f)E=H,\qquad f=\frac{1-e^{-x}}x,
\]

and hence

\[
E(x)=\frac{xJ(x)}{e^x-1},
\qquad
[x^n]J(x)
=q_j\frac{n+1}{(2n+5)(n+2)!}.
\]

This candidate will be tested against the complete five-column current
solve, including both affine directions.  The held-out depth-twelve
predictions are

\[
\begin{aligned}
d^{(2)}_{12}
&=-\frac{
55615691736622684675837754865
}{
18380933703309326321702196477952
},\\
d^{(3)}_{12}
&=-\frac{
16884595808465322118653
}{
22183885503994014526192306094080
}.
\end{aligned}
\]

Success requires exact agreement, symbolic nonvanishing of every
\(\alpha_n^{(j)}\), terminal independence from the two affine current
directions, and a rational certificate that
\(\operatorname{Im}(J/q_j)(2\pi i)>1/200\).  Failure of any one
condition reopens the low mixed representatives rather than completing
the quotient modulo \(D\).

All four conditions pass.  The complete recurrence matches through
depth forty, including both held-out depth-twelve coefficients.  The
two algebraic multiplier zeros are \(4/9\) and \(1/3\), so neither is
an integer depth.  The exact five-column solve retains two affine
parameters at every row while leaving the terminal coefficient fixed.
The Machin interval gives the strict bound

\[
\operatorname{Im}(J/q_j)(2\pi i)>\frac1{200}.
\]

Hence both exceptional representatives have infinitely supported
lower rays, with limiting source rates nine and twelve.  Since the
fixed-weight quotient by \(D\) has exactly one representative
\(P^aQ^b\), \(a\in\{0,1,2\}\), the pure and mixed results together
classify every admissible nonzero one-\(C\) class modulo \(D\).

The replay and result are
[`gauge_cone_low_mixed_lower_terminal_recurrence.py`](gauge_cone_low_mixed_lower_terminal_recurrence.py)
and
[`gauge_cone_low_mixed_lower_terminal_recurrence_result.md`](gauge_cone_low_mixed_lower_terminal_recurrence_result.md).
The successor question is whether multiplication by \(D\) can move a
class into the kernel of every such quotient.

## Positive \(D\)-adic depth: the first layer

### Eigenquestion and attack vectors

The smallest cone-compatible depth-one multiplier is \(Q^3D\).  In the
fixed source chart,

\[
\operatorname{top}P_0=-\frac34u^2z^2,\qquad
\operatorname{top}Q_0=-\frac14u^3z^3,
\]

while the nominal weight-six top of \(D_0\) cancels and

\[
\operatorname{top}D_0=\frac{27}{8}u^5z^5.
\]

Thus one \(D\)-factor increases the effective source weight by five,
not six.  The three live attack vectors are:

1. the leading \(D_0\)-symbol may transfer the depth-zero obstruction
   into a grade shifted by \((-2,-2)\);
2. the cancellation may create extra current columns at that grade,
   allowing the transferred terminal coefficient to disappear;
3. parameter derivatives of \(D_s\) may couple into the same shell and
   turn the apparent adjoint ray into another finite logarithm.

The respective counterchecks are an exact projected replay with the
complete equal-weight prefix, a full current-column rank solve, and a
right-forward-`dexp` comparison beyond the already observed cubic row.

Normalize the first prefix as

\[
H_{\rm pre}
=\frac14Q^3DC
=P^3Q^3C+\frac{27}{4}Q^5C.
\]

Its cost-two zero-grade top is

\[
A=\frac{243}{4096}u^{16}z^{18}.
\]

The existing finite replay gives

\[
\Omega_7
=-\frac{129140163}{153931627888640}u^{44}z^{48}.
\]

The candidate terminal grade and ray are

\[
\Gamma=(-19,-15),\qquad
F_n=u^{44+15n}z^{48+15n}
\quad\text{at cost }7+2n.
\]

On this ray,

\[
\operatorname{ad}_A F_n
=\frac{729(5n+4)}{2048}F_{n+1},
\]

which has no nonnegative integral zero.

### Discriminating test

The first held-out row is cost nine.  If the cost-seven term is a finite
logarithmic insertion, its forward-`dexp` image accounts for the entire
cost-nine terminal velocity and \(\Omega_9\) vanishes.  A nonzero
\(\Omega_9\) selects a new scalar response.  Any extra logarithmic state
in \(\Gamma\ge(-19,-15)\) selects a wider finite core instead.

The replay succeeds only if it:

1. accepts the two equal-weight monomials as one projected prefix;
2. reproduces the cost-seven coefficient above;
3. solves every available current column rather than fixing a preferred
   representative;
4. exposes either a certified infinite response or a precise deeper
   quotient after the cost-nine branch.

A finite cost-seven logarithm, a zero adjoint multiplier, or terminal
dependence on an affine current parameter kills transfer from depth zero.
Even success at \(D^1\) will not by itself prove induction in the
\(D\)-adic exponent.

### Exact depth-one outcome

The cost-nine discriminator takes the non-finite branch.  In fact the
persistent grade begins at cost three:

\[
\begin{array}{c|c|c}
q&(u,z)\text{-exponent}&[u^az^b]\Omega_q\\ \hline
3&(14,18)&243/131072\\
5&(29,33)&-531441/2684354560\\
7&(44,48)&-129140163/153931627888640\\
9&(59,63)&-31381059609/78812993478983680.
\end{array}
\]

After division by the adjoint orbit

\[
\alpha_n=\frac{729(5n-6)}{4096},
\]

the four coefficients have ratios

\[
1,\quad\frac1{10},\quad-\frac1{420},\quad-\frac1{630}.
\]

These are exactly the first four ratios of \(\phi_2\).  The current
columns at each positive depth have three invisible affine directions;
the remaining two have higher pivots and are forced to zero.  No current
column reaches the terminal monomial.

The symbolic cost-three transfer for the entire depth-one layer is also
nonzero.  After factoring the common \((-1/4)^b\) source scale, it is

\[
\begin{array}{c|c|c}
a&[r^{2a+5}z^4]\Omega_3(P^aQ^bDC)&
\text{cone range}\\ \hline
0&-81b/512&b\ge3\\
1&27(9b+20)/2048&b\ge4\\
2&-81(9b+28)/8192&b\ge4.
\end{array}
\]

For all three residues, put

\[
\sigma=2a+3b+6.
\]

The zero-grade letter has exponent \((\sigma+1,\sigma+3)\), the
terminal seed has exponent \((\sigma-1,\sigma+3)\), and the terminal
adjoint multiplier has its only algebraic zero at

\[
n=1+\frac3{\sigma},
\]

strictly between one and two.  Thus every admissible nonzero class at
\(D\)-adic depth one has the same nonpolynomial \(\phi_2\) response and
limiting source rate \(\sigma\).

This closes \(D^1\).  It does not yet justify replacing \(D\) by
\(D^r\): at depth two the leading cost-three exponent shifts again, so
the induction must retain the \(D\)-adic index rather than treating
\(D_0\) as a passive scalar.

## Depth-two discriminator and the exceptional-depth warning

Use the smallest convenient depth-two representative

\[
H_{\rm pre}=\frac1{16}Q^6D^2C.
\]

Its exact cost-two top and cost-three terminal seed are

\[
A=-\frac{6561}{16777216}u^{30}z^{32},
\qquad
B=\frac{2187}{268435456}u^{29}z^{33}.
\]

Thus the effective slope and terminal grade are

\[
\sigma=29,\qquad \Gamma=(-31,-27),
\]

and the candidate ray is

\[
F_n=u^{29+29n}z^{33+29n}
\quad\text{at cost }3+2n.
\]

Its adjoint factors are

\[
\alpha_n
=2A\bigl(29(n-1)-2\bigr).
\]

If the depth-one \(\phi_2\) response persists, the first held-out
coefficient must be

\[
[u^{58}z^{62}]\Omega_5
=\frac{444816117}{22517998136852480}.
\]

Zero terminal velocity at cost five and exact agreement select the
same scalar response.  A nonzero terminal velocity, a different
logarithmic coefficient, or an extra state in
\(\Gamma\ge(-31,-27)\) forces a depth-dependent recurrence.

More generally, the associated terminal exponent suggested by the
first two depths is

\[
F^{(r)}_n
=u^{\sigma+r-2+\sigma n}
 z^{\sigma+r+2+\sigma n}.
\]

The corresponding formal adjoint multiplier is

\[
\alpha^{(r)}_n
=2A_r\bigl(\sigma(n-1)+r-4\bigr).
\]

This has an integral zero precisely at \(r=4,n=1\).  Therefore even a
successful depth-two replay cannot support an unqualified induction:
depth four is a predeclared exceptional layer that must be descended
to a lower grade, as in the \(Q^3C\) and low mixed cases.

The depth-two held-out coefficient agrees exactly, and its terminal
velocity is zero.  Thus \(D^2\) again carries the \(\phi_2\) response.

For the normalized representatives

\[
H_r=4^{-r}Q^{3r}D^rC,
\]

the first two depths suggest the exact leading data

\[
\begin{aligned}
\sigma_r&=14r+1,\\
A_r&=\frac{(-1)^{r+1}3^{3r+2}}{2^{11r+2}},\\
B_r&=\frac{3^{2r+3}}{2^{11r+6}},\\
F^{(r)}_n
&=u^{15r-1+(14r+1)n}
  z^{15r+3+(14r+1)n}.
\end{aligned}
\]

The next discriminating checks are \(r=3\) and the resonant \(r=4\).
For \(r=3\), the predicted cost-three seed and cost-five logarithm are

\[
B_3=\frac{19683}{549755813888},
\qquad
d^{(3)}_1
=-\frac{38354628411}{23611832414348226068480}.
\]

For \(r=4\), they are

\[
B_4=\frac{177147}{1125899906842624},
\qquad
d^{(4)}_1
=\frac{48295450738251}{
396140812571321687967719751680}.
\]

The same formula predicts \(d^{(4)}_2=0\) because
\(\alpha^{(4)}_1=0\).  Cost three tests the seed law; cost five tests
\(\phi_2\); cost seven at \(r=4\) is the resonance discriminator.  A
nonzero cost-seven coefficient must come from a wider core or a lower
grade, whereas zero confirms termination of this particular terminal
ray without resolving the whole \(D^4\) layer.

### Symbolic correction and all-depth outcome

The generalized-multinomial calculation falsifies the extrapolated
\(15r-1\) seed exponent at \(r=3\).  The first two normalized examples
had hidden the depth-one offset exception.  The exact split is:

- at \(d=1\), the terminal seed is
  \((\sigma-1,\sigma+3)\) with
  \(\sigma=2a+3b+6\);
- at every \(d\ge2\), it is
  \((\sigma,\sigma+4)\) with
  \(\sigma=2a+3b+5d+1\).

For \(d\ge2\), the restored coefficient is

\[
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(\frac{27}{8}\right)^d
\frac3{64}\binom d2.
\]

All nine \((a,d\bmod3)\) normalizer classes reduce to
\(-\binom d2/12\) after their leading scales are removed.  In
particular, the earlier proposed \(r=3,4\) seed coefficients and the
claimed \(r=4\) resonance are false.

The correct zero-grade letter has exponent
\((\sigma+1,\sigma+3)\), and on

\[
F_n=u^{\sigma(n+1)}z^{\sigma(n+1)+4}
\]

its adjoint multiplier is

\[
\alpha_n=2A\{\sigma(n-1)-2\}.
\]

The only algebraic zero is \(1+2/\sigma\), strictly between one and
two.  There is no exceptional integral depth.

The current-column support is also uniform.  Offsets
\(-4,-3,-2,-1\) fall below the terminal projection.  Offset zero has a
nonzero higher normal-two pivot and contains no terminal monomial, so
it is forced to zero.  Thus the terminal equation is independent of
four affine current directions and has the same nonpolynomial
\(\phi_2\) response at every \(d\ge2\).

The held-out full replay for \(D^2Q^5C\) gives zero terminal velocity
at costs five and seven and

\[
\begin{aligned}
[u^{52}z^{56}]\Omega_5
&=\frac{100442349}{1374389534720},\\
[u^{78}z^{82}]\Omega_7
&=\frac{31381059609}{180143985094819840},
\end{aligned}
\]

exactly as predicted.  Together with the separate \(d=1\) theorem,
this completes every positive \(D\)-adic one-\(C\) layer.  The
certificates are
[`gauge_cone_discriminant_depth_symbolic.py`](gauge_cone_discriminant_depth_symbolic.py),
[`gauge_cone_discriminant_positive_depth_phi2.py`](gauge_cone_discriminant_positive_depth_phi2.py),
and
[`gauge_cone_discriminant_positive_depth_phi2_result.md`](gauge_cone_discriminant_positive_depth_phi2_result.md).

The remaining finite-prefix frontier is no longer one-\(C\)
discriminant cancellation.  It is the higher contact filtration
\(C^m,\ m\ge2\).

The \(r=3\) cost-three prediction is false.  The predicted
\((44,48)\) slot vanishes.  One diagonal step lower, the exact first
terminal is

\[
\Omega_3
=-\frac{177147}{549755813888}u^{43}z^{47},
\qquad
\Gamma=(-45,-41).
\]

Thus the depth index does not enter the terminal exponent by the naive
\((r-2,r+2)\) shift.  The corrected \(r=3\) ray candidate is

\[
F_n=u^{43+43n}z^{47+43n}.
\]

Its first adjoint factors are

\[
\alpha_0=-\frac{7971615}{17179869184},
\qquad
\alpha_1=-\frac{177147}{8589934592}.
\]

If this descended ray again has the \(\phi_2\) response, the held-out
cost-five coefficient is

\[
[u^{86}z^{90}]\Omega_5
=\frac{282429536481}{
18889465931478580854784}.
\]

This replacement also invalidates the proposed \(r=4\) resonance
location until its actual cost-three quotient is computed.  The
adjoint-zero warning remains an attack vector, not a theorem.

The corrected \(r=3\) cost-five coefficient agrees exactly and has
zero terminal velocity.  Its descended ray therefore has the
\(\phi_2\) response.

At \(r=4\), the actual first terminal also lies at the saturated
relative exponent \((0,4)\):

\[
\Omega_3
=\frac{4782969}{562949953421312}u^{57}z^{61},
\qquad
\Gamma=(-59,-55).
\]

The zero-grade coefficient is

\[
A_4=-\frac{4782969}{70368744177664},
\]

and the terminal adjoint factor is now

\[
\alpha_n=2A_4\bigl(57(n-1)-2\bigr).
\]

Its zero is \(1+2/57\), not an integer.  The predeclared resonance was
therefore an artifact of the killed exponent formula.  If the saturated
ray has the same \(\phi_2\) response, the held-out cost-five coefficient
must be

\[
[u^{114}z^{118}]\Omega_5
=\frac{1349730754842699}{
198070406285660843983859875840}.
\]

Agreement removes the apparent \(r=4\) exception but still leaves the
all-\(r\) seed nonvanishing problem: a higher \(D\)-adic layer could
cancel its cost-three saturated terminal before the adjoint recurrence
starts.

The \(r=4\) cost-five coefficient agrees exactly and has zero terminal
velocity.  Thus the apparent resonance is removed.

For the normalized representatives \(H_r\), the saturated seeds at
\(r=2,3,4\) are

\[
\frac{3^7}{2^{28}},\qquad
-\frac{3^{11}}{2^{39}},\qquad
\frac{3^{14}}{2^{49}}.
\]

They fit the parity-sensitive candidate

\[
B_r
=\frac{(-1)^r3^{\lceil7r/2\rceil}}
{2^{\lceil(21r+14)/2\rceil}},
\qquad r\ge2.
\]

The first held-out parity check is \(r=5\):

\[
\sigma_5=71,\qquad
F_0=u^{71}z^{75},\qquad
\Gamma=(-73,-69),
\]

\[
B_5=-\frac{387420489}{1152921504606846976}.
\]

If the saturated \(\phi_2\) module persists, then

\[
[u^{142}z^{146}]\Omega_5
=\frac{3652302792226978611}{
830767497365572420564879412675215360}.
\]

Agreement would validate the first odd-parity seed beyond its discovery
point, but an all-\(r\) theorem still requires deriving the ceiling
formula rather than interpolating it.

The \(r=5\) parity prediction is false by the factor \(5/9\).  The exact
seed is

\[
B_5=-\frac{215233605}{1152921504606846976}.
\]

Together with \(r=2,3,4\), the corrected invariant is the much simpler
ratio

\[
\boxed{\frac{B_r}{A_r}=-\frac{\binom r2}{48}
=-\frac{r(r-1)}{96}},
\qquad r\ge2.
\]

It matches

\[
-\frac1{48},\quad-\frac3{48},\quad
-\frac6{48},\quad-\frac{10}{48}
\]

at \(r=2,3,4,5\).  This is the pair-of-\(D\)-factors signature that the
ceiling fit obscured.  For a general multiplier \(P^aQ^bD^rC\),

\[
A_{a,b,r}
=\frac{(-1)^{a+b+1}3^{a+3r+2}}
{2^{2a+2b+3r+2}},
\]

so the candidate saturated cost-three seed

\[
B_{a,b,r}
=-\frac{r(r-1)}{96}A_{a,b,r}
\]

is nonzero for every \(r\ge2\) in characteristic zero.

The corrected \(r=5\) cost-five prediction is

\[
[u^{142}z^{146}]\Omega_5
=\frac{405811421358553179}{
166153499473114484112975882535043072}.
\]

The next replay tests this coefficient.  Promotion beyond the checked
representatives additionally requires an exact derivation of the
\(\binom r2\) coefficient in the saturated source quotient.

The \(r=5\) coefficient agrees exactly and its terminal velocity is
zero.  The all-\(r\) derivation is the ordered-pair calculation

\[
\frac{[D_1]_{(7,0)}}{[D_0]_{(5,0)}}=\frac1{16},
\qquad
\frac{[D_0]_{(2,2)}}{[D_0]_{(5,0)}}=-\frac16.
\]

One marked factor supplies the parameter-raising term and one distinct
factor supplies the radial-deficit/normal-two term.  Their product is
\(-1/96\), and there are \(r(r-1)\) ordered choices.  This proves

\[
B_{a,b,r}=-\frac{r(r-1)}{96}A_{a,b,r}
\]

for every \(r\ge2\), rather than fitting it from the four fixed depths.
The saturated current quotient leaves the terminal independent, its
adjoint zero is \(1+2/\sigma\), and the common response is
nonpolynomial \(\phi_2\).

The replay and theorem are
[`gauge_cone_discriminant_finite_depth_phi2.py`](gauge_cone_discriminant_finite_depth_phi2.py)
and
[`gauge_cone_discriminant_finite_depth_phi2_result.md`](gauge_cone_discriminant_finite_depth_phi2_result.md).
Together with the depth-zero and depth-one results, they exclude every
nonzero finite one-\(C\) multiplier.  The remaining finite-prefix class
is higher \(C\)-adic order \(C^m,\ m\ge2\).
