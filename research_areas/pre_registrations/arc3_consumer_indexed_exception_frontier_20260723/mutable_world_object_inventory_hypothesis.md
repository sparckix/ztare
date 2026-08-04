# Mutable-world object inventory

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-MUTABLE-WORLD-OBJECT-INVENTORY-20260726-40`  
Status: refuted

## Eigenquestion

Does a canonical inventory of world components supply the persistent state
identity that local footprints and rendered-marker bits lack?

## Hypothesis

Factoring each state into:

- controlled-object coordinates;
- existing finite/scalar coordinates;
- carrier time;
- the H35 downstream marker; and
- a palette-normalized connected-component inventory of the world after
  removing the controlled rendering and projection-owned interface rows

will separate both same-time witnesses H38 and H39 and return `edge_found` for
the H30-selected target within depth 180 / 20,000 states.

## Fixed construction

1. Infer the interface boundary as the least row used by the projection's
   display or ordered-budget renderings; inventory only rows above it.
2. Infer background as the modal remaining value after erasing the current
   controlled-object cells.
3. Extract four-connected nonbackground components.
4. Encode each component by absolute bounding box plus a first-occurrence
   palette partition of its local shape; sort the inventory and hash the exact
   tuple.
5. Append `(component_count, inventory_digest)` to the projection's
   operation-domain coordinate.

The inventory uses no target action, route, valence, named object, hand-chosen
world coordinate, or environment result. Static geometry may appear in the
inventory but does not multiply states; only component lifecycle changes it.

## Discriminating test

Reconstruct the H38 and H39 source differences and require different inventory
digests for each pair. Then rerun the exact time-guarded selected search with
the H35 split. Replay any route and require configuration `4dd96788…`, joint
code `c1968343…`, and the target operation.

## Success criterion

- both prior same-time witnesses are separated;
- search returns `edge_found` with no projection counterexample;
- replay is admissible and reaches the selected factors/code;
- no environment contact.

## Kill conditions

Reject on ambiguous interface/background, failure to separate either witness,
new noncommutation, ordinary/bound exhaustion, replay mismatch, target leakage,
or environment contact.

## Claim boundary

A pass certifies the inventory coordinate and an offline route. Core promotion
and live execution remain separate.
