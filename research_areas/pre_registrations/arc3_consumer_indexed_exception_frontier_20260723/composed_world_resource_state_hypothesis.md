# Composed world/resource state

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-COMPOSED-WORLD-RESOURCE-STATE-20260726-41`  
Status: refuted at inference

## Eigenquestion

Do mutable-world inventory, secondary resource configuration, and clock form
the missing product state for selected-target search?

## Hypothesis

Replacing the H35 point predicate with the complete evidence-derived secondary
resource configuration, then composing it with H40's object inventory and
clock identity, will recover both the observed positive-control edge and the
H30-selected edge within depth 180 / 20,000 states per search.

## Fixed construction

1. Start from the accepted compiled projection without H35/H36 point splits.
2. Retain H40's canonical world-component inventory.
3. Take the rows owned by the primary ordered-budget rendering and all columns
   after its final owned column.
4. From the evidence bank, retain exactly cells with at least two observed
   values; require each to be binary and to include the modal world-background
   value.
5. Append one Boolean per retained cell (`value != background`) to
   `ordered_feasibility_configuration`.
6. Preserve absolute carrier time because no time-translation certificate is
   available.

The secondary coordinate is inferred from rendering ownership and evidence
variation. It contains no hand-selected cells, raw live value, target, route,
valence, or named substrate resource.

## Discriminating test

- require the inferred codebook to reproduce the four measured configurations
  and a deterministic single cycle;
- require direct separation of the H35 and H40 interface witnesses and H38/H39
  world witnesses;
- search/replay the observed target, then the selected configuration
  `4dd96788…`;
- require selected joint code `c1968343…`.

## Success criterion

Both searches return `edge_found` without projection counterexamples; all four
witnesses are separated; codebook/transition criteria hold; both replays are
admissible and selected replay reaches the exact factors/code; no environment
contact.

## Kill conditions

Reject on inference ambiguity, codebook/transition mismatch, any witness
collision, noncommutation, ordinary/bound exhaustion, replay mismatch, target
leakage, or environment contact.

## Claim boundary

A pass yields an offline route and certifies this product coordinate for the
current carrier. Core promotion and live execution remain separate.
