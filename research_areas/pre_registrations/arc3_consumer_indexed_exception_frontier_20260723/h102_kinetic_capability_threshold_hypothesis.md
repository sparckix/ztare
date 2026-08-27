# H102: state-dependent kinetic capability threshold

Date: 2026-08-06

Status: pre-registered, offline theory/algorithm discriminator not yet run

## Correction to H101

H101 compiles a food-generated, reflexively catalyzed reaction set and one
budget-feasible integer flux. That proves combinatorial and stoichiometric
potential. It does not show that the current stock of each capability makes
the reactions fast enough to outrun depreciation, interference, or
obsolescence. Boolean catalyst presence can therefore label a dynamically
inert network as a candidate critical core.

The reproduction reaction also consumes two judgment units and is catalyzed
by measurement design. Under mass-action kinetics its per-capita gain is
state-dependent. This creates an Allee-type threshold: low capability stock
decays while a sufficiently dense stock amplifies under the same topology.

## Eigenquestion

Can one authority-typed catalytic topology be subcritical at a low capability
state, supercritical at a higher state, and resource-blocked at that same high
state when only sparse settlement cost is replaced by factorial cost?

## Hypothesis

Bind each H101 reaction to an exact nonnegative mass-action rate constant and
evidence refs. Bind each capability/error species to an exact depreciation
rate and each state to exact nonnegative species amounts. For reaction `j`,
compute

```text
v_j(x) = k_j
         * product(x_reactant ^ stoichiometric_count)
         * product(x_catalyst)
```

and use the same rate vector for:

1. internal capability/error drift `S_internal v - depreciation * x`;
2. primitive-contact rate `sum(cost_j * v_j)`;
3. catalyst and food availability checks.

A kinetic supercritical candidate requires H101 productive topology, strict
positive internal drift for every capability species, nonpositive drift for
every error species, and primitive-contact rate within budget. Bootstrap
reactions may seed a state but cannot pay internal growth; the post-bootstrap
fixture therefore assigns their kinetic rate constant zero.

## Exact positive and negative states

Reuse the H101 sparse topology, food amounts `base=1`,
`external_settlement=1`, error amount `E=0`, and these exact parameters:

- `bootstrap_judgment`: `k=0`;
- `invert_measurement_wall`, whose reactant and catalyst are both `J`: `k=2`;
- `reproduce_judgment`, with reactants `2J + external_settlement` and catalyst
  `D`: `k=1/4`;
- depreciation: `delta_J=1`, `delta_D=1`, `delta_E=1`;
- H101 topology-admission budget: `200` for both sparse and factorial
  variants, so both topologies remain stoichiometrically feasible and the
  kinetic gate owns the rate comparison;
- primitive-contact rate budget: `300`.

Evaluate the ray `D = 3J/2` at two exact stocks:

1. lower: `J=3/2`, `D=9/4`;
2. upper: `J=7/4`, `D=21/8`.

The predicted reproduction rates and drifts are:

| State | reproduction rate | `J` drift | `D` drift | sparse cost rate |
|---|---:|---:|---:|---:|
| lower | `81/64` | `-15/64` | `9/4` | `405/4` |
| upper | `1029/512` | `133/512` | `7/2` | `5145/32` |

The lower state must be `kinetically_subcritical`. The upper state must be
`kinetically_supercritical_candidate` at sparse reaction cost `80`. Replacing
only that cost with factorial `160` gives upper cost rate `5145/16 > 300` and
must be `resource_rate_blocked` while the state, topology, rate constants, and
depreciation remain unchanged.

The analytic `J` threshold on this ray satisfies `3 J^2 = 8`. The exact lower
and upper stocks bracket it because `3*(3/2)^2 < 8` and
`3*(7/4)^2 > 8`. The audit need not represent the irrational root as a float.

## Negative fixtures

- A rate law bound to another reaction SHA is rejected.
- Missing or extra reaction laws are rejected.
- Missing species amounts or depreciation rates are rejected.
- Float parameters are rejected; all dynamics remain rational.
- A catalyst with zero amount makes its reaction rate zero.
- Positive error drift blocks kinetic criticality.
- Cross-authority topology, model, or state is rejected.
- A claimed threshold bracket must keep topology, kinetics, depreciation,
  budget, and food fixed while increasing capability stocks componentwise.
- Synthetic kinetics cannot authorize a live takeoff claim.

## Success criterion

An inspectable receipt reproduces every exact rate, drift, and cost above. The
lower/upper pair compiles as a valid subcritical-to-supercritical bracket. The
factorial counterfactual differs only in primitive cost and is blocked by the
same rate vector. Every negative fails at its declared identity or dynamic
gate.

## Kill conditions

Kill the kinetic compiler if RAF membership alone determines its verdict; if
the lower and upper states collapse; if bootstrap output pays internal drift;
if rate and cost use different fluxes; if catalyst abundance is ignored; if
float tolerance can cross the threshold; if error growth is omitted; or if a
post-outcome state or parameter relabel can manufacture a bracket.

## Prior-art and claim boundary

Mass-action chemical reaction networks, kinetic RAF analysis, Allee effects,
autocatalytic thresholds, next-generation matrices, and capability
depreciation analogies are established. The candidate surface is their exact
compilation with agent-capability authority, externally settled reaction
evidence, sparse epistemic assay cost, false-edge species, and content-bound
lineage. A pass would correct the architecture's criticality criterion and
provide a theory/algorithm discriminator. It would not establish literature
novelty, measured kinetic parameters, live ARC compounding, or capability
takeoff.
