# H-GPSA-RELATIONAL-GOAL-CONSUMER-20260727-70

Lower the common relational task version space into the existing
`goal_edge_fn` planner protocol. Preserve source epoch, task contract,
descriptor identity, active hypothesis identity, and local refutation.

The bounded discriminator has two edge candidates. Planning must reach the
first source-operation relation and stop before predicting through it. An
external open task receipt then refutes only that candidate. A second leg must
receive the surviving relation. Existing exact authoritative edges and unary
goals must retain their behavior. No ARC descriptor is admitted.
