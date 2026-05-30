"""Scientific Ground Truth modules — one file per substrate.

Each ``gp<N>_*_gt.py`` defines the substrate's true / dominant form,
holdout structure, and validator hooks. Covered substrates include the
Feynman benchmark set, the GP-079 / GP-080 / GP-088 calibration
families, the GP-163 Radial Acceleration Relation, and the Hardy–
Ramanujan / Tacrolimus / A002865 cases.

Read by ``ztare.scaffold`` (to generate Division A / Division B
artifacts) and by the validator (to score holdout performance). Never
imported by mutator-visible code.
"""
