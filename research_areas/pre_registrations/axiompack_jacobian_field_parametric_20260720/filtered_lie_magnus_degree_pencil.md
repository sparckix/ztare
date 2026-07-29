# Filtered Lie/Magnus degree transfer

**Status:** pencil theorem; the general upper bound is settled, while the
family-specific slope-two premise remains open

## Eigenquestion

Does a coefficient bound

\[
e(V_m)\leq 2m+4
\]

for a time-dependent polynomial source field imply

\[
\deg Y_n\leq 2n+1
\]

for the logarithm of its flow?

The answer is **no without an additional structural cancellation**.  The
parameter indexing contributes one integration order for every occurrence of
a velocity coefficient, while polynomial derivation excess adds under Lie
brackets.

## Conventions

Work over a characteristic-zero field.  For a polynomial vector field \(Z\),
put

\[
e(Z)=\deg Z-1,\qquad e(0)=-\infty,
\]

where \(\deg Z\) is the maximum total degree of its components.  Polynomial
derivations satisfy

\[
e([Z,W])\leq e(Z)+e(W).
\]

Use the current source-flow convention

\[
\partial_s\psi_s=D\psi_s\,V(s),\qquad \psi_0=\mathrm{id},
\]

with ordinary parameter coefficients

\[
V(s)=\sum_{m\geq1}s^mV_m.
\]

The velocity therefore starts at parameter order one.  Write the Magnus
logarithm as

\[
\Omega(s)=\log\psi_s=\sum_{n\geq2}s^nY_n.
\]

Using \(s^m/m!\) and \(s^n/n!\) instead changes rational scalars, not the
support or any degree bound.  Reversing the left/right logarithmic derivative
changes bracket signs, not parameter weights or excesses.

If instead “starting at order one” is encoded by
\(V(s)=\sum_{m\geq0}s^m\widehat V_m\), then the logarithm starts at order
one.  The same argument gives

\[
e(\widehat Y_1)\leq4,\qquad
e(\widehat Y_n)\leq4n-2\quad(n\geq2).
\]

That is a different indexing convention and must not be mixed with the
current \(m\geq1,\ n\geq2\) convention.

## Magnus support lemma

More generally, assign velocity coefficient \(V_i\) a positive logarithmic
weight \(w_i\), meaning that one occurrence contributes \(w_i\) parameter
powers after integration.  If

\[
e(V_i)\leq a\,w_i+b,
\]

then every length-\(k\), order-\(n\) Magnus word satisfies

\[
n=\sum_i w_i,\qquad
e(\text{word})\leq a n+b k.
\]

This is the general filtered Lie/Magnus transfer rule.  A useful bound must
therefore control both total parameter weight and word length.  In the
present indexing \(w_m=m+1\), \(a=2\), and \(b=2\).

Every length-\(k\) Lie monomial contributing to \(Y_n\) has the form

\[
[V_{m_1},[V_{m_2},\ldots,V_{m_k}]\ldots],
\qquad m_i\geq1,
\]

up to a permutation and bracketing, with

\[
n=\sum_{i=1}^k(m_i+1)=\sum_{i=1}^k m_i+k.
\]

The reason for the extra \(k\) is that each of the \(k\) time integrations
adds one parameter power.  Consequently, under
\(e(V_m)\leq2m+4\),

\[
\begin{aligned}
e(\text{monomial})
&\leq\sum_{i=1}^k(2m_i+4)\\
&=2(n-k)+4k\\
&=2n+2k.
\end{aligned}
\]

Since \(m_i\geq1\), one has \(k\leq\lfloor n/2\rfloor\).  When \(n\geq4\)
is even, equality \(k=n/2\) forces every \(m_i=1\); any Lie word of length
greater than one in the single element \(V_1\) vanishes.  Thus the largest
potentially nonzero length is

\[
k_{\max}(n)=
\begin{cases}
1,&n=2,\\
\lfloor(n-1)/2\rfloor,&n\geq3.
\end{cases}
\]

This gives the support-sharp filtered envelope

\[
e(Y_n)\leq b_n,
\qquad
b_n=
\begin{cases}
6,&n=2,\\
3n-1,&n\geq3\ \text{odd},\\
3n-2,&n\geq4\ \text{even}.
\end{cases}
\]

“Support-sharp” means that no smaller bound follows from parameter weight,
bracket subadditivity, and the identity \([V_1,V_1]=0\) alone.  Individual
universal Magnus components can have further rational cancellations; using
those requires an additional theorem about the relevant Lie words and is not
part of this generic filtration lemma.

The first coefficients exhibit the envelope directly:

\[
\begin{aligned}
Y_2&=\tfrac12V_1,\\
Y_3&=\tfrac13V_2,\\
Y_4&=\tfrac14V_3+\text{lower-excess terms},\\
Y_5&=\tfrac15V_4-\tfrac1{60}[V_1,V_2]
      +\text{lower-excess terms},\\
Y_6&=\tfrac16V_5-\tfrac1{48}[V_1,V_3]
      +\text{lower-excess terms}.
\end{aligned}
\]

Only the displayed degree-relevant terms are asserted; signs depend on the
left/right convention.

## Counterexamples to the slope-two conclusion

The claimed implication already fails at order two.  On one affine
coordinate \(v\), take

\[
V(s)=s\,v^7\partial_v.
\]

Then \(e(V_1)=6=2\cdot1+4\), all other coefficients vanish, and all velocities
are scalar multiples of one autonomous field.  Hence

\[
\Omega(s)=\frac{s^2}{2}v^7\partial_v,
\]

so

\[
e(Y_2)=6>4=2\cdot2,\qquad \deg Y_2=7>5.
\]

The same example is admissible for the source lift ideals after embedding it
as \((v^7,0)\).

Brackets can also attain the larger generic envelope.  Take

\[
V_1=v^7\partial_v,\qquad V_2=v^9\partial_v.
\]

Then

\[
[V_1,V_2]=2v^{15}\partial_v,
\qquad e([V_1,V_2])=14,
\]

and the nonzero order-five Magnus term
\(-[V_1,V_2]/60\) attains \(b_5=14\).

Thus neither integration nor passage to a logarithm removes the extra four
units in the velocity hypothesis.  Magnus brackets can amplify them.

## Premise that would imply the desired bound

The triangular slope-two statement follows immediately from the stronger
coefficient estimate

\[
e(V_m)\leq2(m+1)=2m+2.
\]

Indeed, every contributing monomial then obeys

\[
e(\text{monomial})
\leq\sum_i2(m_i+1)=2n,
\]

and therefore

\[
e(Y_n)\leq2n,\qquad \deg Y_n\leq2n+1.
\]

Equivalently, if the velocity is indexed as

\[
V(s)=\sum_{r\geq2}s^{r-1}W_r,
\]

the sufficient bound is \(e(W_r)\leq2r\).

The weaker \(2m+4\) estimate can still yield slope two if its top two excess
layers satisfy a family-specific theorem forcing every over-budget Magnus
word to vanish or cancel.  Examples of adequate extra hypotheses would be:

- the over-budget shells are all invariant multiples of one field and their
  mixed brackets vanish;
- every length-\(k\) word receives a compensating deficit of at least \(2k\);
- the actual coefficientwise estimate improves to \(2m+2\) after passing to
  the admissible source quotient.

None of these follows from \(e(V_m)\leq2m+4\) alone.

## Application boundary

Under the current contact convention, the desired
\(\deg Y_n\leq2n+1\) does **not** follow from the proposed velocity envelope.
One must prove either the \(2m+2\) coefficient estimate or a precise
commuting/invariant-shell lemma for the particular Jacobian family.

No Lean file is warranted yet: the arithmetic filtration lemma is settled,
but the family-specific premise that would connect it to the current contact
is exactly the unresolved mathematical step.  Encoding the desired
conclusion now would merely encode a missing hypothesis.

## Kill conditions for the proposed mechanism

The slope-two route is killed if any of the following occurs:

1. some actual \(V_m\) has excess greater than \(2m+2\) and its high shell
   survives in \(Y_{m+1}\);
2. an over-budget mixed bracket, beginning with
   \([V_1,V_2]\) at logarithmic order five, is nonzero;
3. the claimed invariant-multiple relation holds only for leading terms but
   not for every shell above the slope-two budget;
4. passage to the full lift enlarges polynomial degree beyond the quotient
   filtration;
5. the velocity actually has a parameter-order-zero term, in which case all
   weights and bounds must be reindexed before applying this lemma.
