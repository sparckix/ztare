# Scalar polynomial identity continuation into the critical holonomy loop

## Eigenquestion

Once a nonzero specialized polynomial `p : C[X]` is available, can existing
analytic-continuation data force every critical-loop return value to be a
root of `p`, so that the existing finite-root escape theorem applies without
accepting return-root membership as a premise?

## Existing boundary

`FormalCriticalHolonomyLoop` constructs an explicit scalar continuation and
proves that its natural-turn endpoints are injective.  In contrast,
`FormalFinitePolynomialCoverOrbitEscape` deliberately assumes a root relation
for every return.  The local algebraic-root carriers also store their root
identity and prove boundary regularity; none transports that identity around
the critical loop.

`FormalAnalyticContinuation.IdentityContinuation` already owns the required
coordinate-aware continuation chain.  Its edges include eventual endpoint
compatibility, while each chart makes the endpoint analytic on a connected
domain.  This is enough to propagate the scalar analytic identity

\[
z\longmapsto p(\operatorname{endpoint}(z))=0
\]

without routing it through the Julia-specific derivative-factor residual.

## Candidate theorem

Add a small extension of the existing continuation interface:

```text
endpointPolynomialValue p chart z := aeval (chart.endpoint z) p

IdentityContinuation.propagate_endpointPolynomial_zero
  continuation p
  (EqOn (endpointPolynomialValue p first) 0 first.domain)
  : EqOn (endpointPolynomialValue p last) 0 last.domain
```

The terminal-center corollary must produce

```text
p.IsRoot (last.endpoint last.center)
```

as a conclusion.  It may not accept that root statement.

Compose this with a critical loop realization, one return chart and one
continuation chain for each natural turn, and an equality binding each return
chart endpoint to the explicit critical-loop endpoint.  The derived root
relation and the already-proved injectivity then contradict the finite root
set of nonzero `p`.

## Proof skeleton

1. Analyticity of each chart endpoint and polynomial evaluation gives
   analyticity of `endpointPolynomialValue`.
2. `IdentityEdge.endpoint_compatible` gives eventual equality of the right
   polynomial value with the left value after the transition.
3. The left zero identity and `transition_mem_left` give a zero germ on the
   right.  The analytic identity theorem extends it across the connected
   right-chart domain.
4. Induct over `IdentityContinuation` and evaluate at the terminal center to
   derive `IsRoot`.
5. Apply the construction to every return chart, rewrite by its binding to
   `CriticalLoopRealization.carrier.continuedValue`, and feed the resulting
   root sequence plus `explicit_critical_orbit` injectivity to the existing
   finite-polynomial-cover escape theorem with a one-element sheet type.

## Exact surviving premises

The composition still requires the upstream critical adapter to construct:

- an initial chart on which the specialized eliminant identity is locally
  zero;
- for each natural turn, a coordinate-aware `IdentityContinuation` to a
  return chart; and
- equality of that chart's terminal endpoint with the explicit critical-loop
  continuation endpoint.

These are strictly stronger and more inspectable than a supplied sequence of
return roots.  The new theorem derives return-root membership from them.

## Kill conditions

- A nonzero polynomial, a starting root, and the scalar ODE alone do not
  imply return roots.  For `p = X - 1`, initial value `1`, and a nontrivial
  multiplier, the first return is not a root.  Thus the continuation of the
  polynomial identity is indispensable.
- Pointwise equality of endpoints at one overlap point is insufficient;
  `IdentityEdge` needs eventual germ compatibility.
- One finite continuation chain does not cover all natural turns; a chain
  must be constructed for each retained return.
- A chart endpoint not bound to the critical-loop endpoint proves a root for
  the wrong branch.
- If the specialized polynomial is zero, finite-root escape is unavailable.
- This kernel does not construct a regular specialization of the rational
  eliminant or derive the initial local identity from derivative-prefix
  evaluation.

## Discriminating test

The focused Lean module must expose the terminal `IsRoot` theorem and the
critical-loop contradiction while taking no `forall N, p.IsRoot ...` premise.
It must reuse `IdentityContinuation` and the existing critical injective-orbit
and finite-root-escape theorems rather than introduce a parallel path-lift or
orbit abstraction.

## Outcome

`FormalCriticalScalarPolynomialHolonomyEscape` passes direct compilation and
its focused named build.  It adds scalar endpoint-polynomial propagation on
the existing `IdentityEdge`/`IdentityContinuation` data, derives terminal
`IsRoot`, and composes this with `CriticalLoopRealization.explicit_critical_orbit`
and the one-sheet case of `no_injective_orbit_over_finite_polynomial_cover`.
No return-root sequence is accepted as a premise.

The exact residual is now constructional: the critical adapter must build the
initial local eliminant identity, one existing-style continuation chain per
natural return, and terminal endpoint bindings to the explicit loop.  The
kernel does not claim those data already exist.  `#print axioms` for the
terminal root and contradiction theorems reports only `propext`,
`Classical.choice`, and `Quot.sound`.
