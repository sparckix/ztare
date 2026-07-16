# GPT-5.5-medium ternary-quasigroup result (2026-07-13)

## Outcome

The campaign closed `frontier_objective_unmet`. It produced one formally
verified consequence and one larger-carrier refutation, but no frontier
mathematical result.

The frozen order-three chart contained 11 canonical ternary quasigroups, 680
anonymous formulas, and 86 semantic profiles. Every structure was already a
singleton under that chart, preventing a leaf from winning by proposing a
finite-record identifier. Three isolated lineages nevertheless remained inside
the supplied equation chart; none requested a new representation epoch.

The first two-premise program used

1. `forall x y z, p(x,p(y,z,x),y)=z`;
2. `forall x, p(p(x,x,x),x,x)=x`.

Its prediction `forall x, p(x,x,p(x,x,x))=x` survived size-four and size-five
countermodel search and was accepted by Isabelle and Lean with both premises
attributed. Another prediction was refuted by a larger finite model. The proved
prediction is an elementary rewrite: instantiate the first premise and rewrite
with the second. The remaining predictions were correctly left untested after
their program was refuted.

## Frozen evidence

- Hetzner attempt:
  `/tmp/axiompack_ternary_quasigroup_frontier_20260713/attempt-34533ad27d804909987543fb7ef9c357`
- Campaign: `leanmill-campaign:aac582cb84c35b13232ee386ee65b3f26b813a338f8a3b541b103462a3005a03`
- Context: `5d3d9bce37aff3658c660e05b3f4ceff28eb830281ae21edcfbeddfc28d97a14`
- Mixed boundary result: `ee9a631c65b7c4ed72139c763fe4e78871c42c4ce72f57d3de295451f5d4f2c0`
- Governed proof recheck: `1ed142e8e73915f2a5999e9aeba0e2096f54a43745b99ef71bc22a43d7d8b2ec`
- Terminal exhaustion: `ca65a92eb9c8351c7eaed1912c6b2f4889cc6249d21599b33ace424792657e99`
- Replay v4: `5897aa611293c41ba239e19f1b60a7b120b37da460d92de88215300ddda69a19`

Replay reports `ok=true`, no finalists, and no outstanding reservations. The
bounded literature role timed out twice at its 300-second subscription-runtime
boundary, first at medium effort and then at low effort. This is recorded as
`review_unavailable`; it supplies no novelty credit and was not retried again.

## Apparatus finding

The host initially priced the proved target at 2.55 residual bits because the
three non-equational coordinate-recoverability axioms caused the equational
baseline to abandon rewrite deduction. The same bounded deduction finds the
short proof when run over the equational fragment alone. Background constraints
now continue to restrict finite models while only equations enter the rewrite
system.

The mixed boundary also exposed lifecycle asymmetry. Proof governance now runs
before a refuted sibling returns the program to search; boundary feedback
preserves both the governed positive and the countermodel witness. Refuted
programs cannot re-enter from stale durable views, and replay-schema changes
invalidate cached audit conclusions.

## Next discriminator

Do not repeat this finite ternary chart. A successor must make representation
invention precede theorem nomination and score predictions by a held-out
construction, classification, or obstruction that the original chart could
not express. Exact finite geometry remains useful as the referee after the
leaf chooses that representation.
