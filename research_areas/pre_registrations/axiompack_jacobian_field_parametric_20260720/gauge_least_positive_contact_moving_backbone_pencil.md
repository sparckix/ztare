# Least positive-contact class over a moving contact-zero backbone

**Status:** preregistered before the exact boundary/parity replay

## Eigenquestion and object identity

Let a coefficientwise-polynomial source/target connection have an arbitrary
contact-zero backbone and let its least nonzero positive-contact target
coefficient have (C)-adic depth (m>0).  First quotient the coefficient
complex by exact inverse-flow pairs: a target prefix together with its own
negative logarithm is the zero class and may only shift the least nonzero
index.

Does the first class remaining after that quotient have a nonzero
opposite-parity source symbol which forces an infinite source or target
response of asymptotic rate at least two, uniformly under shifts of the least
index and fixed rational amplitude specialization?  Or can the complete
moving contact-zero backbone recursively cancel it below rate two?

The governing object is the cohomology of the complete source/target
coefficient complex modulo exact target-flow/source-pullback boundaries.  A
static same-cost cokernel, a chosen canonical normal form, and a syntactically
nonzero prefix are different objects and cannot substitute for this one.

## Recovered parity structure

Put

\[
x=u+\frac12.
\]

At the least (z)-order of the seed pullback,

\[
P_0=zx+O(z^2),\qquad
Q_0=\frac{z^2}{4}\left(x^2-\frac14\right)+O(z^3),\qquad
C(P_0,Q_0)=-\frac{z^2}{4}+O(z^3).
\]

Hence a target pullback with least (z)-order (B) has profile (f(x))
satisfying

\[
f(-x)=(-1)^B f(x).
\]

For density (z^2), the leading Hamiltonian bracket is

\[
[z^Bf,z^Dg]_{z^2}
=z^{B+D-3}\bigl(Bfg'-Df'g\bigr).
\]

The target-parity profiles are Lie closed.  The opposite-parity profiles are
a module under them, while the bracket of two opposite profiles returns to
target parity.  This is the seed-chart form of the parity image and
symmetric-pair laws already proved in
[`gauge_source_connection_lie_closure_pencil.md`](gauge_source_connection_lie_closure_pencil.md)
and
[`gauge_second_transverse_target_quotient_result.md`](gauge_second_transverse_target_quotient_result.md).
It is an input, not the new claim.

The existing canonical recurrence
[`gauge_canonical_top_recurrence_result.md`](gauge_canonical_top_recurrence_result.md)
proves one nonzero all-layer sequence for a chosen completed normal form.
The existing locally finite positive-contact result
[`gauge_positive_contact_locally_finite_obstruction_result.md`](gauge_positive_contact_locally_finite_obstruction_result.md)
controls continuations of the normalized radial background.  Neither result
quantifies over replacement by an arbitrary moving contact-zero backbone in
the symmetric minimax complex.

## Candidate invariant

At each parameter cost, contact depth, least (z)-order, and amplitude
degree, assemble the complete coefficient equation before specializing the
amplitude.  Project source profiles to the opposite-parity quotient only
after:

1. exact target polynomial relations are removed;
2. lower target logarithms are replayed by left forward-`dexp`;
3. their moving source pullbacks are replayed by the right convention; and
4. every target-parity current column at the same or lower filtered level is
   included.

For a residue (z^Bf(x)), record the excess

\[
E=B+\operatorname{ord}_{x=0}f-2q-4
\]

at parameter cost (q), together with the highest (x)-degree pivot.  The
endpoint (E=-1) corresponds to source derivation degree (2q).  The
candidate obstruction is the terminal image of the complete surplus kernel,
computed by `compile_filtered_surplus_projection`, in the opposite-parity
quotient.

The existing compiler lifecycle is homogeneous: it decides

\[
Sx=0,\qquad Tx=t.
\]

The present cancellation question is affine because the seed itself has
nonterminal coordinates:

\[
Sx=s,\qquad Tx=t.
\]

Before the Jacobian replay, extend the same general-purpose lifecycle with an
optional distinguished surplus \(s\).  It must distinguish an unreachable
surplus demand from a reachable surplus demand whose residual terminal lies
outside \(T(\ker S)\), return exact controls when both equations are soluble,
preserve the homogeneous behavior at \(s=0\), and reject bad relation descent
or incomplete maps exactly as before.

## First discriminating replay

1. Verify the three seed minimal-(z) formulas and the target/residue bracket
   routing exactly.
2. Parameterize the full row-one contact-zero target basis through a training
   weight, retain its symbolic coefficients, and insert representative
   positive-contact seeds (P^aQ^bC^m).
3. Use the existing complete cost-three/cost-four current normalizer to
   compute the first odd residue.  Assemble all backbone contributions in
   the same `(cost, amplitude-degree, contact-depth, z-order)` block before
   any rational specialization.
4. Quotient the target-parity image and use the complete surplus kernel,
   rather than a selected coordinate or columnwise test.
5. Repeat at held-out backbone weights, contact depths, and radial slopes.

The first replay is diagnostic.  A stable finite witness is not an all-index
result; it must be replaced by a symbolic triangular law, a rational
generating function, a finite exceptional-divisor classification, or an
explicit cancellation schedule.

## Attack vectors and counterattacks

1. **Exact-boundary absorption.**  The first residue may be the forward image
   of a lower target logarithm.  Counterattack: include inverse-flow pairs
   before taking the parity quotient and keep the frozen-row example as a
   rejecting regression fixture.
2. **Backbone parity breach.**  A normalized contact-zero source residue may
   lie outside the target-parity algebra even when its target control does
   not.  Counterattack: classify source and target letters separately and
   test the complete mixed bracket block.
3. **Fixed-amplitude collision.**  Different amplitude degrees can coincide
   after specialization.  Counterattack: retain amplitude degree as a
   filtration component until the full polynomial matrix is assembled, then
   compute terminal polynomials, gcds, and rational exceptional roots.
4. **Canonical/minimax conflation.**  A nonzero canonical residue can coexist
   with a bounded noncanonical representative.  Counterattack: search the
   full surplus kernel and charge both source and target payments.
5. **Finite-pattern extrapolation.**  New columns can enter at larger weight
   or contact depth.  Counterattack: reserve held-out blocks and require an
   all-weight support or recurrence argument before promotion.

## Success and kill conditions

The obstruction lane advances if the exact-boundary quotient contains a
nonzero opposite-parity seed and its complete moving-backbone transition has
an all-index nonzero terminal or charged-surplus law whose source or target
rate is at least two after every fixed rational specialization.

The lane is killed or redirected if the seed is exact, if a symbolic
contact-zero backbone cancels the complete parity quotient without charged
surplus, if a rational amplitude supports an infinite below-rate-two path,
or if the candidate statistic depends on the canonical representative.

## Intended certificate split

Discovery remains in this pencil.  Exact polynomial and filtered-linear
algebra identities belong in a deterministic replay.  Only after the
all-index statement is isolated will its finite arithmetic spine be offered
to LeanMill.  No finite replay will be described as closing the unrestricted
Jacobian campaign.

## First replay outcome: target-only classes are boundaries

The affine compiler extension and the replay
[`gauge_least_positive_contact_moving_backbone.py`](gauge_least_positive_contact_moving_backbone.py)
pass exactly.  Before the boundary quotient, the row-three opposite-parity
residues for `Q2C`, `Q6C`, and `Q3C2` survive every contact-zero backbone
column through the training and held-out weights.  In all three cases the
complete affine system fails already at its surplus demand.

Those witnesses are rejected by the governing quotient.  For every tested
prefix (H), left Magnus and forward-`dexp` give the exact inverse pair, and
the graph compiler verifies

\[
  (8H(P_0,Q_0),H)=\operatorname{graph}(8F_0^*)(H).
\]

The canonical compression

\[
  (L,H)\longmapsto L-8H(P_0,Q_0)
\]

is zero on each pair.  Thus the finite unpaired cokernels are negative
controls, not classes of the complete coefficient complex.

This changes the next object.  A cancellation of a source residue by a
target coefficient replaces ((L,0)) with
((L-8H(P_0,Q_0),H)); it does not erase the cost.  The minimax problem is a
**budgeted graph quotient** in which the target coordinate remains charged.
The affine surplus compiler is the per-grade feasibility engine for this
costed graph.

## Second-loop eigenquestion: all-order moving-pullback support

In the adapted coordinates

\[
u=v+1,qquad z=2+2t-3v,qquad \gamma=z/2,
\]

inspect the exact rational family (P_s,Q_s), before expanding in (s).
The candidate support theorem is

\[
  P_s,Q_s\in
  \mathbb Q(s)[u^az^b:b\ge a].
\]

If true, coefficientwise substitution of every polynomial target series
preserves the nonnegative normal semigroup.  The transverse source shell
(Z_m) has Hamiltonian monomial

\[
  V^{3m-5}G^{m+2},qquad
  \nu_{G-V}=7-2m<0\quad(m\ge4),
\]

so no **current** target coefficient of any degree can cancel it in the graph
quotient.  This is stronger than a target-degree window but still only one
triangular edge: lower target coefficients may create the same negative
normal through BCH transport.

The discriminating replay will verify the exact rational support, compile
strict-below-rate-two target windows and held-out orders with the graph
compiler, and retain the lower-row BCH route as the sole live counterattack.
It is killed if either exact family coordinate has a monomial (b<a), or if
the compiler finds a graph column at the transverse terminal.

## Exact second-loop outcome

The support theorem holds.  The exact rational (P_s) has nine spatial
monomials, maximum degree six, and minimum normal order zero.  The exact
rational (Q_s) has twelve spatial monomials, maximum degree eight, and the
same minimum normal order.  Their denominators are scalar in (s) and are
units at (s=0).  Therefore every coefficient of every
(H_s(P_s,Q_s)), for (H_s\in\mathbb Q[P,Q][[s]]), has nonnegative normal
order.

The graph compiler independently checks orders five and seven against all
target monomials through ordinary degrees nine and thirteen.  The terminals
(u^{10}z^7) and (u^{16}z^9) survive with the coordinate functionals
supported on those monomials alone.  These windows test the adapter; the
all-order statement follows from semigroup support and applies without a
target-degree cap.

Thus a current target row cannot cancel (Z_m) for any (m\ge4).  The live
edge is now exact: only lower-row transport and its BCH brackets can reach
the negative-normal layer.  The next compiler block must model that
triangular transport rather than enlarge the same-order target window.

## Third-loop candidate: defect-five causality

Write a source Hamiltonian monomial in normal coordinates as

\[
E_{a,n}=r^az^n=u^az^{a+n},qquad r=uz.
\]

For the density (z^2), direct differentiation predicts

\[
[E_{a,m},E_{b,n}]
=(mb-an)E_{a+b-1,m+n-2}.
\]

Suppose a Magnus word uses instantaneous letters at derivative orders
(j_i) and normal orders (n_i).  Its logarithmic order and output normal
order are

\[
q=\sum_i(j_i+1),qquad
n_{\rm out}=\sum_i n_i-2(\ell-1).
\]

Define the nonnegative instantaneous defect

\[
\delta_i=n_i+2j_i.
\]

Then

\[
n_{\rm out}+2q=2+\sum_i\delta_i.
\]

The (Z_q) ray has (n_{\rm out}=7-2q), so every contributing word must
satisfy

\[
\boxed{\sum_i\delta_i=5.}
\]

If the exact source-only Hamiltonian also lies in the nonnegative normal
semigroup, every compatible source connection does: target control changes
it only by a moving pullback already covered by the support theorem.  It
would follow that no instantaneous coefficient with (j\ge3) can enter the
(Z)-ray, for any moving contact-zero backbone or higher-contact schedule.
This would discharge the conditional velocity-filtration hypothesis in the
existing excess-filtered Magnus recurrence.

The test will derive the source-only Hamiltonian from the exact rational
family via (dF_s^{-1}\partial_sF_s), verify its Hamilton equations and
complete support, then replay the bracket and defect formulas symbolically.
The candidate is killed by one negative-normal source-only monomial or by a
word with an order-(j\ge3) input and total defect five.

## Exact third-loop outcome

The source-only Hamiltonian derived from
(dF_s^{-1}\partial_sF_s) has thirty spatial monomials, maximum degree
fourteen, and minimum normal order zero.  Its exact Hamilton equations and
(\det dF_s=-z^2/8) replay.  Since an arbitrary target control changes this
Hamiltonian by (8K_s(P_s,Q_s)), the nonnegative-normal premise holds for
every coefficientwise-polynomial representative, not only the selected
minimum-cap connection.

The bracket and defect identities also replay exactly.  Consequently every
word reaching (Z_q) has total instantaneous defect five, and no derivative
order (j\ge3) can occur.  The negative control (j=3,n=-1) has defect five
and demonstrates why the support theorem is essential.

This discharges the conditional velocity-filtration hypothesis in
[`gauge_moving_cone_excess_filtered_recurrence_pencil.md`](gauge_moving_cone_excess_filtered_recurrence_pencil.md): later projected inputs are zero for every polynomial moving backbone.  It
does not yet make the checked recurrence universal, because its coefficient
can depend on the unrestricted finite velocity rows (j=0,1,2).  The
infinite moving-backbone counterattack has therefore collapsed to a finite
but unbounded-radial two-jet classification.

## Fourth-loop discriminator: finite two-jet dependence

The causal theorem makes the next test finite in parameter order, though not
in radial degree.  Before attempting a universal profile calculation,
compare three exact two-jets:

1. the source-only representative (K_s=0);
2. the bounded cubic/mixed/quadratic target representative whose source
   connection vanishes at (s=0); and
3. the complete minimum-cap affine representative already used by the
   defect-five recurrence.

For each, derive the first three source Hamiltonian velocity coefficients
from the exact rational family, apply the same defect/excess-filtered
right-Magnus recursion, and extract the (Z_q) coefficient through a held-out
order.  The test asks whether the former coefficient sequence is universal,
merely nonzero across these distinct gauges, or absent in one representative.

A common nonzero sequence would motivate a graph-cohomology invariant.  A
different nonzero sequence would require the full finite-profile transfer
operator.  A zero sequence in one representative kills the (Z)-ray as the
universal minimax carrier and redirects the search to the target logarithm
or a different source defect.  No finite comparison will be promoted to an
all-prefix conclusion.

## Exact fourth-loop outcome: the \(Z\)-ray is gauge-dependent

The replay
[`gauge_defect_five_two_jet_comparison.py`](gauge_defect_five_two_jet_comparison.py)
derives the three two-jets independently and applies the same filtered
right-Magnus recursion through logarithmic order ten.  The coefficient
sequences differ.  In particular, the controlled representative whose
source connection vanishes at \(s=0\) has zero \(Z_q\)-coefficient at every
checked order \(5\le q\le10\), while both the source-only and minimum-cap
representatives have nonzero coefficients throughout that window.

The first zero at order five triggers the preregistered kill condition: the
\(Z_q\) coefficient is not a class of the coupled finite two-jet quotient
and cannot serve as the universal minimax carrier.  The defect-five theorem
remains useful—it proves that rows \(j\ge3\) cannot alter this
coordinate—but it does not make the surviving two-jet coefficient
gauge-invariant.

The successor must quotient the complete \(j=0,1,2\) contact fiber before
selecting a terminal.  The controlled connection's existing all-order
bigraded ray is the first candidate, but its known order-one cancellations
mean that its terminal must be compiled against the complete finite fiber,
with any transferred source or target rate retained as a charged surplus.
A selected controlled representative alone is not a minimax lower bound.

## Fifth-loop carrier discovery: quotient a complete high-rate shell

The fourth loop shows that selecting (Z_q) before quotienting finite
backbone motion is unstable.  The next eigenquestion is therefore
coordinate-free at each checked order: does the complete source-Hamiltonian
shell of rate at least two retain a nonzero class under the exact affine
interpolation between the source-only and controlled connections?

Let (lambda) scale the full controlled target Hamiltonian, including its
parameter dependence, and derive the corresponding source velocity from


\[
L_s^{(\lambda)}=L_s^{\rm source-only}
  +8\lambda K_s(P_s,Q_s).
\]

At logarithmic order (q), every coefficient is a polynomial in
(lambda) of degree at most (q).  Evaluate it at (q+1) distinct
rational values, form every difference from (lambda=0), and compile the
entire shell modulo their span.  The basis contains all Hamiltonian
monomials with density-(z^2) derivation degree at least (2q); it is not
chosen around the former (Z_q) coordinate.

The test succeeds as carrier discovery only if the compiler returns a
nonzero annihilator that is unchanged by an additional held-out rational
value and by basis permutation.  It is killed if the quotient is zero, if
the held-out value enlarges the variation span, or if the distinguished
source-only shell was unreachable in the first place.  A surviving finite
class is still only an invariant of this one-parameter subfamily.  The
complete (j=0,1,2) contact fiber and an all-order recurrence remain
separate obligations.

## Exact fifth-loop outcome: no linear shell carrier on the interpolation

The replay
[`gauge_two_jet_high_rate_shell_quotient.py`](gauge_two_jet_high_rate_shell_quotient.py)
keeps the complete source-Hamiltonian grades whose density-(z^2)
derivation degree is at least (2q).  At order five these are the
Hamiltonian degrees from 13 through 29 that occur in the exact logarithm;
at order six they are the occurring degrees from 15 through 37.

Every retained homogeneous grade has zero cokernel after quotienting by the
span of the exact controlled-interpolation differences.  The source-only
grade decomposes in that span in every case.  Adding one held-out rational
value of (lambda) leaves every rank unchanged, and reversing every
monomial basis leaves the verdict unchanged.  The corresponding target
logarithms remain strictly below the rate-two face in both orders.

This kills a broader candidate than the (Z_q) coordinate: there is no
nonzero **linear fixed-grade functional** on either complete checked shell
that is invariant along this controlled subfamily.  The result does not
produce one (lambda) that cancels all grades simultaneously—the compiler
takes their linear variation span grade by grade—and it does not represent
the full contact fiber.  The next invariant must retain nonlinear
compatibility between grades or charge the Newton face created while a
terminal is canceled.  Searching for another isolated coefficient in the
same shells is now a rejected move.

## Sixth-loop compiler contract: shared controls across filtered blocks

The fifth-loop quotient deliberately duplicated interpolation freedom across
homogeneous grades.  An orientation matrix calculation shows why that
relaxation is decisive: when all retained grades share one set of variation
coefficients, the nonconstant interpolation columns have rank four, while
adjoining the source-only bundle raises the rank to five at both orders five
and six.

The reusable object is a **coupled filtered block problem**.  It has one
domain quotient of controls and several codomain quotients, each with its
own homogeneous shift, relations, and distinguished demand.  The compiler
must stack the block relations but insert each control only once across the
direct sum.  It must return either one common cancellation or a normalized
functional on the full block bundle.

The discriminating non-Jacobian regression has two blocks that are
individually cancellable but require inconsistent values of the same
control; their coupled distinguished bundle must survive.  A matched pair
with consistent demands must return an exact common control.  Wrong shifts,
incomplete domains, and failure of a domain relation to descend in any one
block must be rejected.

For the Jacobian adapter, every homogeneous grade remains a separate typed
block, while the rational interpolation samples form the common domain.
The candidate survives only if the exact coupled compiler reproduces the
orientation rank jump, preserves it under a held-out sample and block/basis
permutations, and confirms that every block alone still has zero cokernel.
This would establish cross-grade incompatibility on one controlled
subfamily, not the complete contact fiber or an all-order lower bound.

## Exact sixth-loop outcome: compatibility restores a carrier

The coupled-block compiler passes its alien positive and negative controls;
the focused compiler suite now has 31 passing tests.  Each block validates
its own filtration shift and relation descent, while the direct-sum quotient
contains only one copy of every common control column.

On the Jacobian interpolation, the retained source bundle has ambient
dimensions 30 and 52 at logarithmic orders five and six.  In both cases the
nonconstant interpolation span has rank four and adjoining the source-only
bundle raises the rank to five.  Hence one rate-two-or-higher source grade
survives for every value in the interpolation family, even though the
quotient of each grade separately is zero.  The polynomial dependence on
(lambda) has degree four; an exact Vandermonde rank-four check makes the
sample span complete for every rational specialization.  Held-out values and
simultaneous block/basis reversal preserve the result.

At order five one normalized separator uses only four coordinates:

\[
-\frac{983040}{11}[u^{10}z^{10}]_{20}
-\frac{11796480}{341}[u^{11}z^{10}]_{21}
+\frac{983040}{341}[u^{12}z^{11}]_{23}
+\frac{627507200}{341}[u^{16}z^{13}]_{29},
\]

where the subscript records Hamiltonian total degree.  It annihilates every
common interpolation variation and pairs to one with the source-only bundle.
The separator is a finite cross-grade compatibility certificate, not an
all-order recurrence.  The next test must enlarge the common domain from one
controlled scalar to the complete admissible finite contact fiber; if the
rank jump persists, its support must then be propagated by an all-order
filtered transition law.

## Seventh-loop discriminator: complete low-weight contact-zero tangent

The coupled interpolation has only one scalar direction.  Enlarge its common
domain by the canonical lift-compatible contact-zero symbols

\[
t_{2a}=P^a,qquad t_{2a+3}=P^aQ,
\]

at row-one cusp weights (5\le w\le11).  These are all canonical symbols in
the declared low-weight window.  Insert each as a full target-connection
perturbation, recompute its moving source pullback and right-Magnus logarithm,
and feed the complete rate-two-or-higher grade bundle to the shared-control
compiler.  The controlled connection remains an additional domain column.

This first pass tests the exact finite-difference span of the seven canonical
directions, not the full multivariate nonlinear image.  Repeat with held-out
weights 12 and 13.  For every column, compute the target logarithmic shell;
if it reaches derivation degree (2q), classify that direction as a charged
target exit rather than a free cancellation column.

The candidate advances if the cross-grade source-only bundle survives all
free columns at orders five and six and the held-out columns either preserve
the separator or carry a target payment.  It is killed if the free domain
reaches the complete bundle, if a held-out uncharged direction raises the
control rank, or if block permutation changes the certificate.  Survival
would still be only a finite low-weight tangent result: mixed direction
terms, arbitrary row index, and the all-weight support theorem would remain.

## Exact seventh-loop outcome: the low-weight tangent does not reach

The deterministic replay
[`gauge_contact_zero_low_weight_coupled_shell.py`](gauge_contact_zero_low_weight_coupled_shell.py)
recomputes every column from the exact connection.  The training domain
contains the controlled column and all canonical row-one contact-zero
symbols at weights five through eleven.  Its common-control rank is eight;
adjoining the source-only high-rate bundle raises the rank to nine at both
orders five and six.

Adding held-out weights twelve and thirteen raises the common-control rank
to ten and the augmented rank to eleven, again at both orders.  The full
ambient bundle dimensions are 124 and 164.  Reversing the order of every
block, basis, and domain column preserves the ranks.  Each autonomous
row-one symbol has zero target logarithm at orders five and six, and the
controlled target column has derivation degree three, so none of the ten
columns is discarded as a charged target exit in these windows.

Thus the cross-grade carrier survives the complete declared low-weight
finite-difference tangent.  This remains a finite tangent theorem: mixed
products of direction parameters and independent coefficients at higher
parameter rows are absent.  The next discriminating pass is the quadratic
closure of the low-weight domain.  If mixed columns reach the bundle, the
carrier is killed; if they do not, the finite-degree polynomial dependence
can be compiled by a multivariate monomial domain before attempting an
all-weight support theorem.

## Eighth-loop discriminator: exact quadratic common-domain closure

Replace connection sampling by a coefficient algebra truncated at total
control degree two.  Its basis consists of the constant monomial, every
linear control (c_i), and every product (c_ic_j).  Addition, rational
scaling, and the Hamiltonian bracket act coefficientwise with exact
convolution, discarding only control degree at least three.  Since Magnus is
assembled from those operations, the resulting linear and quadratic Taylor
coefficients are exact.

Use ten controls: the complete controlled connection and the canonical
row-one contact-zero symbols at weights five through thirteen.  Compile the
source bundle first with the training subset through weight eleven, then
with both held-out weights.  Grant every nonconstant control monomial its own
common compiler column.  This is a relaxation of the actual parameter
variety, where quadratic monomials equal products of linear parameters; a
class surviving the relaxed span also survives the nonlinear family through
quadratic order.

The candidate advances if the source-only bundle remains separated after
all linear and quadratic columns, every target Taylor coefficient stays
below the rate-two face, and training/held-out plus block permutations agree.
It is killed if the relaxed quadratic span reaches the bundle.  Survival
would leave cubic control terms at order six, higher parameter rows, and an
all-weight triangular argument as the next obligations.

## Exact eighth-loop outcome: quadratic relaxation survives

The replay
[`gauge_contact_zero_quadratic_coupled_shell.py`](gauge_contact_zero_quadratic_coupled_shell.py)
runs the right- and left-Magnus recursions over the exact degree-two control
algebra.  In the training domain, 44 linear/quadratic monomials have source
ranks 32 and 41 at logarithmic orders five and six; adjoining the source-only
bundle raises those ranks to 33 and 42.  With held-out weights twelve and
thirteen, 65 relaxed control monomials have ranks 42 and 55, while the
augmented ranks are 43 and 56.

Every target Taylor coefficient has derivation degree at most six in both
orders, below the respective rate-two thresholds.  Block/basis reversal
preserves the certificates.  Hence the source bundle survives even after
quadratic monomials are treated as independent controls, a larger domain than
the actual quadratic parameter variety.

For pure row-one directions, control cost is two, so quadratic dependence is
already complete at logarithmic order five and only cubic dependence remains
at order six.  The controlled direction also has cost-one input and can occur
to higher powers.  The next exact pass should therefore use a weighted
control algebra: weight one for the controlled direction, weight two for
every row-one symbol, retaining every monomial of total control cost at most
the logarithmic order.  That closes the full multivariate dependence in the
declared finite direction window rather than adding one polynomial degree at
a time.

## Ninth-loop discriminator: complete weighted dependence at orders five and six

Assign control cost one to the controlled direction because it has a
nonzero instantaneous row zero, and cost two to every canonical row-one
symbol.  Extend the coefficient algebra from total polynomial degree two to
every control monomial whose weighted cost is at most six.  During the
Magnus recursion, discard a product only when its control cost exceeds six;
therefore the coefficients through logarithmic order six are exact, not a
Taylor approximation.

At each logarithmic order (q\in\{5,6\}), compile every nonconstant control
monomial of cost at most (q) as an independent common column.  This again
relaxes the parameter variety.  Use weights five through eleven for training
and twelve/thirteen as held-out directions, keep the full rate-two source
bundle, and audit the complete target bundle with the same coefficient
algebra.

Survival closes all nonlinear dependence in the declared row-one window at
these two orders.  Failure kills the carrier and must return the exact
weighted control monomials in its decomposition.  Either outcome remains
finite in logarithmic order, row index, and cusp weight; the next all-order
step would require a support theorem for the separator or a charged
transition recurrence.

## Exact ninth-loop outcome: the relaxed monomial span reaches

The replay
[`gauge_contact_zero_weighted_complete_coupled_shell.py`](gauge_contact_zero_weighted_complete_coupled_shell.py)
retains every control monomial of weighted cost at most the logarithmic
order.  At order five, the training domain has 89 such monomials and common
rank 36; the held-out weight-thirteen domain has 131 monomials and rank 48.
The source-only bundle belongs to both images, so the augmented ranks remain
36 and 48.  At order six the corresponding counts and ranks are

\[
(209,58)\quad\hbox{and}\quad(351,82),
\]

and the source-only bundle again belongs to both images.  Block and basis
reversal preserves every verdict.  This triggers the preregistered kill:
the cross-grade linear carrier was a quadratic-truncation phenomenon.

The target audit makes the two orders different.  At order five some
weighted columns have target derivation degree ten, exactly on the rate-two
face.  At order six the maximum target derivation degree is ten, strictly
below the rate-two threshold twelve.  Consequently a coupled source/target
budget can still reject the order-five linear cancellation, but cannot
repair the order-six relaxed-span verdict by target charging alone.

The relaxation has deliberately forgotten the Veronese identities among
monomial coefficients: an actual control point has coefficient
\(c_1^{a_1}\cdots c_r^{a_r}\), whereas the compiler allowed every monomial
coefficient to vary independently.  Membership of the distinguished bundle
in that linear span is therefore not an admissible cancellation schedule.
The successor must preserve those polynomial identities.

## Tenth-loop discriminator: filtered polynomial-fiber compiler

Extend the existing filtered-obstruction lifecycle with a polynomial-family
adapter rather than a second Jacobian-specific solver.  The governing object
is a polynomial map from one shared control affine space into a direct sum of
filtered source and target quotient blocks.  The compiler must:

1. validate every block shift and relation descent with the existing symbol
   compiler;
2. quotient block relations and reduce the resulting coordinate equations
   to an exact independent row basis;
3. retain the constant distinguished demand together with the true control
   monomials, rather than linearizing the monomials into independent inputs;
4. return a constant contradiction immediately when present, otherwise
   compute the exact rational Groebner ideal of the coordinate equations;
5. distinguish a unit ideal, which excludes even an algebraic cancellation,
   from a proper ideal, which is only an unresolved algebraic fiber until a
   rational point or a further certificate is supplied.

The alien regression is a two-block family whose monomial relaxation reaches
the distinguished bundle but whose shared polynomial fiber is empty, paired
with a family having an explicit rational root.  The Jacobian adapter will
compile order five with both source and target rate-two faces and order six
with the source face (the target face is empty there), first through weight
eleven and then through held-out weights twelve and thirteen.

A unit ideal advances the obstruction only in this finite row-one window.
A proper ideal kills this candidate unless exact rational-point analysis
excludes its rational locus.  Independent higher parameter rows, unbounded
cusp weight, and all-order propagation remain outside either finite outcome.

## Exact tenth-loop outcome: the true parameter fiber is empty

The reusable compiler now has a polynomial-fiber lifecycle.  It validates a
coupled filtered linearization, projects away block relations, substitutes
one declared monomial map, reduces the coordinate equations by exact
rational row operations, and computes their Groebner ideal.  Its 35 focused
tests include the required alien separation: two blocks are reachable when
\(x\) and \(x^2\) are independent, but the demands \((x,x^2)=(1,2)\)
generate the unit ideal; the compatible demands \((2,4)\) verify the exact
rational point \(x=2\).

The Jacobian replay is
[`gauge_contact_zero_weighted_parameter_fiber.py`](gauge_contact_zero_weighted_parameter_fiber.py).
At order five, the training and held-out systems reduce to 36 and 49
independent quotient equations.  Each has reduced Groebner basis \(\{1\}\).
The source face has 31 homogeneous blocks and the target contributes one
degree-eleven Hamiltonian block on the rate-two face.  At order six the
training and held-out systems have 58 and 82 independent equations, again
with basis \(\{1\}\); there are 34 source blocks and no target block on the
rate-two face.

Thus the weighted linear decompositions do not lift to a shared control
point, even over an algebraic closure.  Their support displays the defect
explicitly: the order-five decomposition assigns independent coefficients
to `controlled`, `controlled*controlled`, and
`controlled*controlled*controlled`, together with mixed row-one monomials.
No amplitude can realize those assignments simultaneously.

This restores a finite obstruction for the full nonlinear dependence of the
declared row-one weight-thirteen window.  It remains incomplete for an
arbitrary contact-zero backbone because coefficients at every parameter row
are independent controls; one full controlled direction plus row-one symbols
does not span that coefficient jet.

## Eleventh-loop discriminator: complete finite parameter-row jet

At logarithmic order \(q\), introduce an independent control
\(c_{j,w}\) for every target-connection coefficient row
\(0\le j<q\) and every canonical contact-zero symbol \(t_w\) in the finite
weight window.  The direction is

\[
s^j t_w(P,Q)
\]

on the target and its exact moving pullback
\(8s^j t_w(P_s,Q_s)\) on the source.  Assign it control cost \(j+1\), retain
every monomial of total cost at most six during both Magnus recursions, and
then compile the true parameter fiber rather than its monomial span.

Use weights five and six for the first complete jet and weight seven as the
held-out extension.  These give 138 and 414 nonconstant weighted monomials
through cost six, respectively.  Include every source and target
Hamiltonian block on or above the rate-two face at orders five and six.
The former special controlled connection is omitted: through a fixed order
its target coefficients are already rational combinations of the independent
weight-five and weight-six row controls.

The candidate advances if all four polynomial fibers have unit ideal.  A
proper ideal is unresolved unless an exact rational point is found; a
verified rational point kills this carrier by giving a below-face finite
cancellation.  Unit ideals remain only finite-row, finite-weight statements.
The next obligation would be a triangular all-weight cutoff at fixed order,
followed by an all-order recurrence or a counter-schedule.

## Exact eleventh-loop outcome: complete weight-seven coefficient jet excluded

The replay
[`gauge_contact_zero_complete_parameter_jet.py`](gauge_contact_zero_complete_parameter_jet.py)
includes every coefficient row below the checked logarithmic order.  In the
weight-five/six training window, order five uses ten controls and 73 weighted
monomials; order six uses twelve controls and 138 monomials.  Their source
rate faces have 16 and 22 homogeneous blocks.  In both cases the source-only
bundle already survives the independent-monomial linearization, and the true
polynomial fiber has unit ideal.

Adding weight seven gives fifteen controls and 193 monomials at order five,
and eighteen controls and 414 monomials at order six.  The corresponding
source faces have 22 and 30 blocks.  The linearized spans now reach the
bundle, but the exact polynomial fibers remain empty over the algebraic
closure.  No target block reaches the rate-two face in any of the four
systems.

The q6 held-out system exposes a triangular reason rather than only a global
rank.  After quotient row reduction it contains

\[
c_{0,7}^4=0,
\]

as well as the redundant powers three and two.  Hence
\(c_{0,7}=0\) in characteristic zero.  Constant-linear elimination and
rational pivots then remove ten more parameters.  A two-equation core in the
remaining seven variables has exact rational Groebner basis \(\{1\}\).

The general compiler now performs three certificate-preserving reductions
before a global basis calculation: constant-linear cokernel elimination,
rational triangular substitution, and pure-power radical forcing.  A modular
unit-core search may select a small equation subset, but the selected core is
recomputed over \(\mathbb Q\); only that rational result determines the
verdict.  The focused suite has 38 passing tests.

This is a complete finite coefficient-jet theorem through logarithmic order
six and cusp weight seven.  It is not an all-weight or all-order theorem.

## Twelfth-loop discriminator: parity-held-out top-weight forcing

The q6 equation \(c_{0,7}^4=0\) suggests a highest-weight triangular edge.
Before stating an induction, replace the odd held-out weight seven by the
nonadjacent even weight eight while retaining weights five and six.  Use the
same complete parameter rows, cost filtration, full source/target rate faces,
and polynomial-fiber compiler.  This keeps the weighted monomial count equal
to the weight-seven run and separates a parity artifact from a weight law.

In parallel, derive the top source support of the canonical symbols

\[
t_{2a}=P^a,\qquad t_{2a+3}=P^aQ
\]

under the exact moving pullback.  The existing associated-grade theorem gives
one nonzero diagonal leader at exponent \((w,w)\) at the seed row; the new
obligation is to identify which pure power of the highest row-zero amplitude
occupies an uncontested top block of the q5/q6 logarithm.

If weight eight is again forced to zero and the symbolic leader coefficient
is nonzero in both parity families, the finite-window computation can be
replaced by a highest-weight descent at these orders.  If the even case has a
proper fiber or a leader collision, the proposed all-weight induction is
killed and that collision becomes the next carrier.  All-order propagation
remains separate in either case.

## Exact twelfth-loop outcome: parity is not the source of the forcing

Replacing weight seven by weight eight leaves the complete fibers empty at
orders five and six.  With weights five, six, and eight, the order-five
preprocessor successively forces the pure powers of the weight-eight row-zero
and row-one amplitudes to vanish, then forces the corresponding weight-five
and weight-six row-zero amplitudes.  At order six it forces the weight-eight
row-zero fourth power and row-one square, followed by the analogous
weight-five and weight-six powers.  No variables remain before the final
constant contradiction.  Thus the odd weight-seven equation was not a
parity accident.

The exact normal-zero parts of the moving family give the all-weight
instantaneous diagonal law.  At the seed,

\[
 [r^2]P_0=-\frac34,
 \qquad [r^3]Q_0=-\frac14,
 \qquad r=uz,
\]

while the first degree-raising parameter coefficients are

\[
 [sr^3]P_s=\frac18,
 \qquad [sr^4]Q_s=\frac3{64}.
\]

Consequently the coefficient of
\(s^k r^{w+k}\) in the canonical moving pullback is

\[
 \left(-\frac34\right)^a
 \binom ak\left(-\frac16\right)^k
\]

for \(t_{2a}=P^a\), and is

\[
 \left(-\frac34\right)^a\left(-\frac14\right)
 [y^k](1-y/6)^a(1-3y/16)
\]

for \(t_{2a+3}=P^aQ\).  Every coefficient in its permitted range is
nonzero: in the odd case the two binomial contributions have the same sign.
This proves an all-weight diagonal support law.  It does not by itself give
the desired induction, because normal-zero radial Hamiltonians commute.

The one-weight nonlinear replay locates the first noncommuting successor.  At
weight seven the pure row-zero amplitude has fourth-power coefficients

\[
 [u^{14}z^{14}]\Omega^{\rm src}_5
 =-\frac{1107}{81920}c_{0,7}^4,
\]

and

\[
 [u^{25}z^{20}]\Omega^{\rm src}_6
 =-\frac{1750329}{5242880}c_{0,7}^4.
\]

These coordinates are uncontested by the other pure powers in the
single-weight connection; the complete weight-five/six/seven fiber confirms
that the order-six equation survives all mixed controls.  This is still a
finite-order receipt, not a formula in the logarithmic order.

## Thirteenth-loop eigenquestion: unconditional triangular induction

The remaining theorem must quantify over every coefficient row and every
cusp weight at once.  The candidate state is the complete least-positive-
contact bundle after three quotients, in this order:

1. exact inverse-flow graph boundaries;
2. the commuting normal-zero radial contact-zero symbol; and
3. every strictly lower source/target slope-two face.

For a source Hamiltonian monomial \(u^az^b\) at logarithmic order \(q\), use
the slope-two surplus

\[
 \rho_{\rm src}=a+b-2q-4.
\]

For a target Hamiltonian of ordinary degree \(d\), use

\[
 \rho_{\rm tgt}=d-2q-2.
\]

The induction claim is the following budgeted dichotomy.  At the least
nonzero positive contact depth and at the largest remaining noncommuting
shell in a finite coefficient row, every complete cancellation equation
must do one of four things:

1. retain a nonzero opposite-normal terminal;
2. create a source coordinate with \(\rho_{\rm src}\ge0\);
3. create a target coordinate with \(\rho_{\rm tgt}\ge0\); or
4. replace the state by one with strictly smaller lexicographic rank
   \((\text{contact depth},\text{normal offset},
   \text{cusp-weight surplus},\text{radial pivot})\).

The ordering directions will be fixed by the actual transition formula, not
by the displayed prose convention.  Coefficientwise polynomiality makes the
radial and weight maxima in each row finite.  The least parameter order is
well ordered.  If every uncharged edge strictly decreases the declared rank,
well-founded induction excludes an infinite below-rate-two cancellation
schedule.

The first symbolic discriminator is the action of an arbitrary canonical
contact-zero leader on the robust odd-normal terminal.  For

\[
 E_{a,n}=r^az^n
\]

one has

\[
 [E_{w,0},E_{a,n}]=-wnE_{a+w-1,n-2}.
\]

Thus an odd normal offset has no radial resonance, and a word of radial
leaders has a nonzero product multiplier.  The live counterattack is a
collision among different weight/row words after the commuting radial
symbol is removed.  The next replay must compile the complete word bundle,
not a selected coordinate, and derive a symbolic pivot or an explicit
same-rank cycle.

The candidate is killed by any uncharged nonzero cycle, by a zero multiplier
on an admissible odd state, by two incomparable maximal words whose complete
bundle cancels without a higher pivot, or by a coefficient row whose finite
support does not provide the declared maximum.  A finite list of unit ideals
cannot substitute for this induction.

The reusable compiler surface selected by this loop is a proof-carrying
filtered transition certificate.  It must validate the local complete
cancellation block with the existing coupled/polynomial-fiber compiler and
separately validate that every uncharged transition strictly decreases an
explicit well-founded rank.  Jacobian contact depth, cusp weight, and normal
offset remain adapter data.

### Exact radial-word outcome

The first symbolic edge is nonresonant at every depth.  For a polynomial
radial Hamiltonian \(f(r)\) and an odd-normal terminal \(z^ng(r)\), direct
Hamiltonian calculation gives

\[
 \operatorname{ad}_f^k(z^ng(r))
 =(-1)^k\prod_{i=0}^{k-1}(n-2i)
 z^{n-2k}(f'(r))^kg(r).
\]

If \(n\) is odd, none of the integral factors vanishes.  Since
\(\mathbb Q[r]\) is a domain, every word is nonzero whenever \(f\) is
nonconstant and \(g\ne0\).  The deterministic replay is
[`gauge_contact_zero_radial_word_induction.py`](gauge_contact_zero_radial_word_induction.py).

The normalized robust/exceptional theorem has also been routed through the
general filtered-induction checker.  Its six states have five exceptional
descent edges, one robust source-charge edge, and maximum uncharged descent
length one.  This mechanizes the existing normalized-background induction;
the adapter-completeness flag remains false by design.

### Full radial-connection discriminator

Wordwise injectivity still permits a sum of distinct words to cancel.  The
radial Hamiltonians themselves commute, so the proposed exact compression is
stronger.  For a time-dependent radial connection \(f_s(r)\), put

\[
 F_s(r)=\int_0^s f_t(r)\,dt.
\]

The predicted transport is

\[
 \mathcal U_s(z^ng)
 =\sum_{k\ge0}\frac{(-1)^k}{k!}
 \prod_{i=0}^{k-1}(n-2i)
 z^{n-2k}(\partial_rF_s)^kg.
\]

The discriminating checks are:

1. differentiate the displayed series and verify the exact connection
   equation \(\partial_s\mathcal U_s=\operatorname{ad}_{f_s}\mathcal U_s\);
2. prove that the highest Newton face of \((\partial_rF_s)^k\) is the
   \(k\)-th power of the highest face of \(\partial_rF_s\), so it cannot
   cancel in characteristic zero;
3. prove that every lower-normal term of a moving contact-zero pullback is
   strictly below this radial face using the unique northeast support law;
4. split the result at source slope two: a critical/supercritical radial
   face is charged, while a strictly subcritical face exponentiates inside
   the complete slope-two Rees group and can be removed without changing the
   robust/exceptional dichotomy.

The route is killed by a noncommuting radial associated symbol, a highest
Newton face with two distinct leading polynomials that cancel after taking a
power, a lower-normal pullback term on the same face, or failure of the
subcritical inverse to remain in the same Rees class.  Passing the first two
checks alone does not close the arbitrary-backbone theorem; the factorization
and lower-normal separation in checks three and four are required.

### Exact full-radial outcome and the moving-divisor leak

The complete radial connection formula passes.  Radial adjoint operators
commute, coefficient differentiation gives

\[
 k c_k=-(n-2k+2)c_{k-1},
\]

and hence the predicted binomial transport solves the exact time-dependent
connection equation.  For the slope-two occurrence grading, the initial
form identity

\[
 \operatorname{in}(F^k)=\operatorname{in}(F)^k
\]

holds even when the face contains several tied monomials.  Its right side is
nonzero over \(\mathbb Q[s,r]\).  Thus collisions among radial words do not
survive after the complete connection is assembled.

The remaining source is not a lower term of the contact-zero connection.  A
fixed positive-contact factor leaks into the radial quotient because the
family moves the divisor.  Exact expansion gives

\[
 [s]\,C(P_s,Q_s)|_{z=0}
 =\ell(r)
 =\frac{r^2(3r-2)^3(3r^2+12r-16)}{384}.
\]

Therefore a depth-\(m\) coefficient first enters the radial quotient after
exactly \(m\) parameter steps, with multiplier \(\ell(r)^m\).

A first restriction-space audit separates classes.  Multiplication by
\(\ell\) sends the seed restrictions of \(P^3\) and \(PQ\) into the
contact-zero restriction space, while the restrictions of \(Q^2\) and
\(Q^3\) remain outside it.  These are orientation examples only.

### Conductor-quotient discriminator

Let

\[
 B=\mathbb Q+operatorname{span}\{t_w(P(r),Q(r)):w\ge5\}
 \subset\mathbb Q[r].
\]

Every \(t_w\) has degree exactly \(w\) with nonzero leader, so the candidate
all-order quotient \(\mathbb Q[r]/B\) has dimension four.  The next exact
calculation will:

1. derive four cutoff-independent functionals defining \(B\);
2. compute the conductor ideal \(\{g:g\mathbb Q[r]\subset B\}\);
3. classify the finite-rank map
   \(M\mapsto\ell^mM\bmod B\) for every \(m>0\);
4. bind every nonzero radial class to terminal survival, and send its kernel
   to the first nonradial remainder rather than declaring it canceled.

If the multiplication map is eventually zero, the radial quotient covers
only a finite exceptional set and the nonradial transition must carry the
induction.  If it has a persistent nonzero class, that class supplies the
arbitrary-weight radial state.  The route is killed by growth of the quotient
dimension with the cutoff, failure of \(B\) to be an algebra, or a kernel
element whose complete moving pullback vanishes without being an exact graph
boundary.

### Exact multiplier outcome: every first radial leak is cancellable

The canonical-symbol span alone is too small for this question.  With the
complete lift ideal

\[
 I=(P^3,PQ,Q^2),
\]

the leak polynomial is a multiplier: \(\ell I\subset I\) after restriction
to the normalized curve.  Exact polynomial representatives are

\[
\begin{aligned}
T(P^3)={}&-\frac1{384}\bigl(
P^3-3888P^2Q^3+8712P^2Q^2+23P^2Q\\
&\qquad-37260PQ^3-2001PQ^2-4PQ
+32076Q^4+4185Q^3-84Q^2\bigr),\\
T(PQ)={}&-\frac Q{96}\bigl(
588P^2Q+P^2-1188PQ^2-126PQ\\
&\qquad-972Q^3-171Q^2-4Q\bigr),\\
T(Q^2)={}&-\frac{Q^2}{24}\bigl(
36P^2Q+P^2+138PQ-459Q^2-36Q\bigr).
\end{aligned}
\]

Substitution into the seed normalization gives

\[
 T(G)(P(r),Q(r))=\ell(r)G(P(r),Q(r))
\]

for each ideal generator.  Ideality then proves the identity for every
\(G\in I\), and iteration handles \(\ell^mG\).  Thus the first radial leak
always descends; it is not the obstruction state.

### First nonradial-remainder discriminator

For depth one define

\[
 R(G)=[s]\bigl(G(P_s,Q_s)C(P_s,Q_s)\bigr)
       -T(G)(P_0,Q_0).
\]

The first nonzero normal layer is \(z^2\).  On the three generators its
radial profiles are

\[
\begin{aligned}
[z^2]R(P^3)
={}&-\frac{r(3r-2)^2}{24576}
 (405r^6-945r^5-207r^4+1893r^3\\
&\qquad-1119r^2-34r-4),\\
[z^2]R(PQ)
={}&\frac{r^2(3r-2)^2}{12288}
 (69r^4-138r^3+60r^2+6r+2),\\
[z^2]R(Q^2)
={}&\frac{r^4(r-1)(3r-2)^2}{6144}
 (9r^2-15r+7).
\end{aligned}
\]

All three profiles have even normal order two.  The radial action formula is

\[
 [f(r),z^2g(r)]=-2f'(r)g(r),
\]

and the next radial adjoint vanishes.  Thus this layer is a finite even pivot,
not the odd all-order terminal.

An object audit rejects the first proposed quotient of these profiles.  The
ideal \(r^2(3r-2)^2\mathbb Q[r]\) computed earlier is the image of an
independent polynomial source field on the scalar contact-lowering row.  The
displayed \(R(G)\) is instead a source Hamiltonian remainder.  Applying that
scalar-action ideal directly to \(R(G)\) mixes two codomains.  No survival
claim is made from that comparison.

For a product \(AG\), the exact Hamiltonian identity remains

\[
 R(AG)=A_0R(G)+A_1G_0C_0.
\]

The next correct compiler block must include the complete source/target
even-layer contact equation, charge the source Hamiltonian degrees
(20,18,20) of the three generator remainders, and then extract its first
odd residual.  A same-category even-layer cancellation with no odd residual
or charged source/target pivot kills this induction edge.

### Exact depth-one odd transition

The complete product-rule calculation has a uniform odd residual.  For the
canonical weight symbols, after the radial correction above,

\[
\begin{aligned}
t_{2a}=P^a:\quad
[z^3r^{2a+1}]R(t_{2a})
&=-\frac{(-3/4)^a(4a+3)(6a+11)}{384},
&&a\ge3,\\
t_{2a+3}=P^aQ:\quad
[z^3r^{2a+4}]R(t_{2a+3})
&=\frac{(-3/4)^a(3a+10)(8a+15)}{1536},
&&a\ge1.
\end{aligned}
\]

Both coefficients are nonzero in characteristic zero, and both top radial
degrees equal (w+1).  Thus the maximum weight in any finite coefficient
row supplies a unique nonzero odd top shell.  Exact replay on weights five
through eighteen, with weights twelve through eighteen held out from the
symbolic derivation, is
[`gauge_moving_divisor_odd_remainder_all_weight.py`](gauge_moving_divisor_odd_remainder_all_weight.py).

This proves the first positive-contact transition over the moving radial
backbone.  It does not justify induction on contact depth: the correction at
depth (m) is (T^m), and intermediate even layers can feed the candidate
odd layer.

### Arbitrary-contact-depth discriminator

For a monomial in the lift ideal, define a fixed linear section by the first
applicable generator,

\[
\mathcal T(P^aQ^b)=
\begin{cases}
 P^{a-3}Q^bT(P^3),&a\ge3,\\
 P^{a-1}Q^{b-1}T(PQ),&a<3, a,b\ge1,\\
 Q^{b-2}T(Q^2),&a=0, b\ge2.
\end{cases}
\]

Extend linearly.  This section preserves the lift ideal and satisfies

\[
 \mathcal T(G)(P(r),Q(r))=\ell(r)G(P(r),Q(r)).
\]

For contact depth (m\ge1), set

\[
 R_m(G)=[s^m]\bigl(G(P_s,Q_s)C(P_s,Q_s)^m\bigr)
          -\mathcal T^m(G)(P_0,Q_0).
\]

The induction candidate is:

1. every normal layer below (2m) vanishes and the normal-(2m) radial
   layer is removed by \(\mathcal T^m\);
2. the first odd layer is normal order (2m+1);
3. for (G=t_w), its largest radial degree is strictly increasing in (w)
   and its coefficient is nonzero for every (m\ge1,w\ge5);
4. hence a finite coefficient row descends by its maximum weight to either
   that odd shell or the already-certified higher even source pivot.

The orientation window will compute (m=1,2,3,4) and weights five through
twelve, then derive a symbolic recurrence in (m) from the exact normal
jets.  We will reserve at least one larger depth and two larger weights as
held-out checks.  A zero top coefficient at any positive integral
((m,w)), an odd layer before (2m+1), a collision with a lower weight at
the same radial degree, or a correction ambiguity that cancels the complete
odd row without exposing the certified even pivot kills this candidate.

Even if the candidate passes, it supplies only the local positive-contact
transition.  Unconditional closure additionally requires a group-level
factorization of an arbitrary coefficientwise-polynomial contact-zero
backbone into the radial section and a positive-contact remainder, with the
rate filtration preserved under conjugation.

### Depth-two falsification and revised transition

The predicted first odd order (2m+1) fails at (m=2).  Exact rows for
weights five through eight all have first even order two and first odd order
three.  Their normal-three radial degrees are respectively

\[
13,14,15,16,
\]

with nonzero top coefficients

\[
-\frac{97713}{524288},\quad
 \frac{589275}{1048576},\quad
 \frac{425007}{2097152},\quad
-\frac{576639}{1048576}.
\]

The error in the proposed depth grading is structural: \(\mathcal T\) is a
section of radial restriction, not of the complete normal jet.  Its off-axis
defect can therefore recur at normal order two after every iteration.

The corrected candidate is stronger for the desired induction.  For every
(m\ge1) and canonical symbol (t_w):

1. the first odd residual of (R_m(t_w)) is always normal order three;
2. its top radial degree is
   \[
   D(m,w)=w+7m-6;
   \]
3. its top coefficient is nonzero for all integral (m\ge1,w\ge5), with a
   parity-dependent closed product recurrence;
4. maximum weight therefore remains a strict triangular pivot at every
   contact depth.

The next discriminating window is depths three and four and weights five
through ten.  Depth four and weights nine and ten are held out from fitting.
The candidate is killed by a missing normal-three layer, a radial degree
different from (D(m,w)), any positive-integral zero of the inferred
coefficient, or a lower weight reaching the same top radial degree.

### Exact arbitrary-depth outcome

The corrected candidate passes, with one finite transient added to the
three-cycle.  On the weighted face

\[
 \operatorname{wt}(r,z,s)=(1,2,-1),\qquad
 \operatorname{wt}(P,Q,C)=(2,3,6),
\]

the top section rules are

\[
 (a,b)\longmapsto(a-1,b+3),\quad\frac{81}{8},qquad a>0,
\]

and

\[
 (0,b)\longmapsto(2,b+1),\quad-\frac32.
\]

Thus the (P)-exponent decreases to zero and then follows
(0\to2\to1\to0).  Let \(\alpha\) be its value after (m) steps.  In
particular (0\le\alpha\le2), and the final (Q)-exponent is

\[
 \beta=\frac{2a+3b+7m-2\alpha}{3}.
\]

For (t_w=P^aQ^b), where (b\in\{0,1\}), exact coefficient extraction gives

\[
\begin{aligned}
 &[z^3r^{w+7m-6}]R_m(t_w)\\
 &\quad=
 \left(-\frac34\right)^a
 \left(-\frac14\right)^b
 \left(\frac{27}{128}\right)^m
 \left[-\frac{
 (6a+9b+21m-10)
 (16am+4a-4\alpha+18bm+37m^2-29m)
 }{324}\right].
\end{aligned}
\]

Lift-ideal admissibility gives either (a\ge1) or (a=0,b\ge2).  The first
parenthesis is therefore at least (17).  Also

\[
\qquad
37m^2-29m\ge8m.
\]

If (a\ge1), the second parenthesis is bounded below by

\[
16am+4a+8m-8>0.
\]

If (a=0,b\ge2), it is bounded below by

\[
18bm+8m-8>0.
\]

Hence the coefficient never vanishes for every lift-admissible monomial at
(m\ge1).  Its radial degree
(w+7m-6) is strictly increasing in (w), so the maximum weight in every
coefficientwise-polynomial row is an unconditional triangular pivot.

The replay
[`gauge_moving_divisor_odd_remainder_all_depth.py`](gauge_moving_divisor_odd_remainder_all_depth.py)
derives the weighted face from the exact rational family, derives the
factorization from its first normal jets, checks depths one through three,
and passes the preregistered held-out cells ((m,w)=(4,9),(4,10)).  It also
routes the two parity classes, their transient regime, and the three cyclic
states through the filtered-induction compiler.  The compiler verifies the
finite transition logic but deliberately leaves adapter completeness to the
displayed all-parameter arithmetic.

This proves the local positive-contact transition for every contact depth.
It still does not establish that an arbitrary moving contact-zero backbone
can be reduced to this radial adapter without changing the rate filtration.

### Group-level rate-grade factorization discriminator

Attach parameter cost (j) to a contact-zero parity symbol (t_w), and
define its rate-two excess grade by

\[
 \gamma(w,j)=2(w-j-5).
\]

The exact parity bracket has weight (w+v-5) and parameter costs add, so

\[
 \gamma(w+v-5,j+k)=\gamma(w,j)+\gamma(v,k).
\]

This is the natural additive grade: the paired source pullback of (t_w)
has derivation degree (2w-3), and the bracket loses seven derivation
degrees, exactly the constant absorbed by the shift five above.

Let (mathfrak b=\bigoplus_g\mathfrak b_g) be the resulting graded
contact-zero parity algebra.  Let (mathfrak p) denote the complete
positive-contact coefficient complex after radial correction.  The proposed
group-level theorem is:

1. every coefficientwise-polynomial logarithm admits a unique recursive
   factorization into a contact-zero parity factor and a corrected
   positive-contact factor;
2. on the associated rate grade, conjugation by the contact-zero factor is
   an invertible graded transport;
3. mixed positive/negative words of total grade zero remain part of that
   invertible grade-zero transport and cannot annihilate a nonzero class;
4. the diagonal block on every contact depth and canonical weight is the
   nonzero normal-three coefficient proved above;
5. therefore the normalized-background locally-finite obstruction transfers
   to every coefficientwise-polynomial contact-zero backbone, unless the
   factorization itself has source or target limsup rate at least two.

The exact discriminator has two layers.  First compile the abstract
block-triangular inverse: a finite coefficient row, ordered by contact depth,
rate grade, and weight, must have nonzero diagonal blocks and every
off-diagonal edge must be strictly triangular or budget-charged.  Then bind
the Jacobian adapter with:

- parity-bracket grade additivity;
- coefficientwise finite support, which supplies maxima in every row;
- the transient-plus-three-cycle section dynamics;
- the all-depth nonzero diagonal formula;
- the existing robust/exceptional positive-contact transition graph.

The candidate is killed if the paired source/target graph action fails to
descend to this complex, if a mixed-grade word produces a nonzero same-grade
nilpotent kernel rather than an automorphism, if factorization requires
infinitely many target weights in one parameter coefficient, or if an
off-diagonal transition returns to the same 
((\text{contact depth},\gamma,\text{weight})) state without a budget
charge.

### Complete-face countercheck and its unique exception

The scalar normal-three coordinate is not by itself the whole diagonal
block.  The complete weight-(W) face uses every monomial (P^aQ^b) with
(2a+3b=W) and retains every normal coefficient.  Exact sparse compilation
through (W=42) and contact depths one through six gives full column rank
except when

\[
 m=1,\qquad W=6k.
\]

There the top face has a one-dimensional kernel.  Normalizing its (P^{3k})
coefficient to one gives

\[
 K_k=\sum_{\ell=0}^k c_{k,\ell}
 P^{3(k-\ell)}Q^{2\ell},
\qquad
\frac{c_{k,\ell+1}}{c_{k,\ell}}
=\frac{9(4(k-\ell)+1)}{4(\ell+1)}.
\]

Equivalently,

\[
 c_{k,\ell}=9^\ell\binom{k+\tfrac14}{\ell}.
\]

This kernel does not produce a same-rank cycle.  On the immediately lower
weighted face, of weight (6k+6) rather than (6k+7), the unique highest
normal term is pure and has coefficient

\[
 [z^{3k+3}]R_1(K_k)=-\frac{3}{2^{3k+4}}\ne0.
\]

The coefficient has an all-(k) explanation.  Under the weighted scaling,
the subleading contact face satisfies

\[
 [\varepsilon^1\partial_y C]_{y=0}
 =-\frac3{64}(x-1)(4x^2-16x+9),
\]

whose leading term is (-3x^3/16).  Only the normalized (P^{3k}) term can
reach (x^{3k+3}), and the seed face has leader (P=x/2).  Their product is
exactly (-3/2^{3k+4}); all (Q)-containing terms have smaller ordinary
degree.  Thus the exceptional kernel strictly descends one weighted face
and terminates.

The rank window is an implementation stress, while the promoted induction
uses the parity/D-adic split.  The identity

\[
P^aQ^{2d+\epsilon}
=\frac{P^aQ^\epsilon}{27^d}
  \sum_{j=0}^d\binom djD^j(-4P^3)^{d-j},
\qquad D=4P^3+27Q^2,
\]

reduces every finite multiplier to one parity term and finitely many
positive-(D) terms.  The parity term has the nonzero all-depth diagonal
above.  Every (D)-positive term is in the already-certified robust or
exceptional transition graph.  The only possible top-face collision is the
displayed (K_k), and its strict one-face exit supplies the missing
transition.

### Asymptotic rate-transfer discriminator

The finite transition graph still needs an asymptotic composition theorem.
The required statement is substrate-neutral.  Let an infinite unbounded
family of parameter orders carry a nonzero terminal recurrence.  At each
such order, suppose exhaustive local cancellation has one of three outcomes:

1. the terminal survives with an affine derivation-excess lower bound;
2. cancellation creates a source payment at the same parameter order; or
3. cancellation creates a target payment at the same parameter order.

Uncharged transitions may occur first, but their length is uniformly bounded
by a well-founded filtered-induction certificate.  If every closing branch
has asymptotic rate at least \(\lambda\), then the symmetric limsup is at
least \(\lambda\).  The same-order requirement is essential: it makes the
occurrence-to-payment map injective, so one finite prefix coefficient cannot
be counted as the payment for infinitely many terminal occurrences.

The next general-purpose compiler layer will therefore bind:

- one existing `FilteredInductionProblem`;
- one infinite-support certificate for the recurrence index set;
- affine occurrence-order and derivation-excess lower bounds;
- one rate witness for every non-descent transition;
- side compatibility (`source_charged` to source and `target_charged` to
  target); and
- identity of occurrence and payment orders.

It must reject a finite support set, a reused constant payment order, a
strictly subcritical closing branch, a missing closing witness, a side
mismatch, or a nondecreasing local transition.  A parameter-index shift may
change only affine intercepts and must leave the certified rate unchanged.

For the Jacobian adapter, the positive-contact orbit supplies an infinite
subsequence with source rate at least \(11/2\).  Every robust cancellation
supplies a same-order source pivot.  The complete moving-backbone induction
adds only the depth-one \(K_k\) face descent, after which the same terminal
or source-payment alternatives apply.  A target factor on or above the
rate-two face is charged directly.  A strictly subcritical factor is an
invertible Rees transport and is retained in the adapter certificate rather
than counted as a payment.

Passing this discriminator closes the least-positive-contact branch only.
The pure contact-zero branch remains separate: when the factorized residual
has no positive contact coefficient, the displayed induction is vacuous and
cannot be used to infer the unrestricted minimax value.
