---
description: "Pre-registered target-isolation probe for every LeanMill governance organ."
status: closed_pass
date: 2026-07-17
---

# All-organs target-scope probe

## Identity boundary

A target-ratification check owns one resolved theorem plus the declarations
available before it. Later siblings and unrelated same-file declarations are
outside that theorem's premise environment.

## Hypothesis

The consequence-exposure and currency-mismatch organs still receive the whole
module even when a qualified target is carried. A later sibling can therefore
contaminate an earlier target's verdict. Routing consequence exposure through
the canonical source-through-target prefix and currency mismatch through the
selected declaration will remove that cross-target channel while preserving
module-audit behavior when no target is requested.

## Discriminating test

1. Select an earlier theorem in a multi-declaration source.
2. Put a consequence-exposure or currency-mismatch trigger only in a later
   sibling.
3. Require the selected target to remain unaffected.
4. Select the triggering sibling and require the relevant organ to see it.
5. Supply an absent qualified target and require typed target-identity
   unavailability rather than full-module fallback.

## Success criterion

- later declarations never affect an earlier selected target;
- selecting the later declaration preserves detector strength;
- target absence/ambiguity withholds credit and names the identity failure;
- calls without a target preserve module-level behavior.

## Kill conditions

- target isolation drops declarations that precede and define the selected
  theorem;
- the repair reconstructs Lean syntax outside the canonical source parser;
- normal target-scope controls change verdict without an identified defect.

If killed, return typed target-policy unavailability for multi-declaration
ratification rather than applying module-wide checks to a selected theorem.

## Result

Passed. Target governance now resolves one qualified theorem identity and
derives three views from it: the normalized signature, the selected
declaration, and the source prefix through the selected declaration.
Consequence exposure receives the prefix; currency and proof-shape checks
receive the declaration; later siblings cannot influence either view.

The positive and negative controls are
`test_target_scoped_organs_exclude_later_siblings`,
`test_proof_shape_organs_are_fenced_to_selected_declaration`, and
`test_supplied_unresolved_target_is_typed_unavailable`. Calls without a target
retain module-audit behavior.
