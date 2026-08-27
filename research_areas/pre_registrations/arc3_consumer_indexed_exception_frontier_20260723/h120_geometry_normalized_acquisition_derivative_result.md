# H120 result — later behavior reached the oracle ceiling

Status: **within-session compounding signal; causal source unresolved**.

An exact breadth-first evaluator over the locally cached full `tu93` dynamics
found an 18-action minimum for Level 1 and a 10-action minimum for Level 2.
Both witnesses completed on fresh replay. H119 used 22 and 10 actions,
respectively, so excess cost fell from four actions to zero.

The 22-to-10 decline is therefore not explained entirely by path length. The
persistent actor became optimal on the later level. H120 does not identify why:
the Level 2 visual state may be easier for a fresh model, so task order remains
a confound. A fresh-session rollout from the identical Level 2 start is needed
before attributing the efficiency change to learned fast state.

Evidence: `h120_geometry_normalized_acquisition_derivative_result.json`;
evaluator: `h120_geometry_normalized_acquisition_derivative_audit.py`.

