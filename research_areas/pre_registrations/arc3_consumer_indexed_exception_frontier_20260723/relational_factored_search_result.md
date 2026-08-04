# Relational factored-search result

H72 returned a typed projection counterexample.

- The generic bounded fixture passed: carrier-equal states with different
  task-relation truth remained distinct, and search found the expected
  two-operation edge.
- All 248 focused relational, factored-search, and worldmodel tests passed.
- The Level 3 run used the current carrier, current seed, H71 descriptor, four
  evidence-derived operations, depth 180, and a 20,000-state ceiling.
- Search stopped after 529 generated / 459 expanded states at depth 21 with
  `projection_noncommuting`.
- The merged sources had identical declared carrier coordinates, resource
  order, clock, and task-relation truth. Action `0` produced different
  successor keys.
- The complete source difference was two cells: `(61,57)` and `(62,57)`,
  values `3` versus `8`. These cells belong to an auxiliary 2×2 object read by
  a relocation mechanism in the accepted carrier chain; the compiled chart
  represents the principal controlled object and ordered resource but omits
  this coupled object.

The task relation was not refuted. The current mechanism quotient was: it is
not closed under the accepted transition program. The next discriminator
should refine the chart by a causally tested auxiliary-object coordinate, then
rerun the same frozen relation search. No environment contact occurred.
