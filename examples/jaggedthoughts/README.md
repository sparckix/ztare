# JaggedThoughts quick start

JaggedThoughts compiles a source-bound strategic decision into a typed option
space, scenario evaluations, a Pareto frontier, neighborhood-relative peaks,
elimination witnesses, and a representation-status boundary.

Run the reference decision from the repository root:

```bash
./venv/bin/python -m ztare.strategy.cli \
  examples/jaggedthoughts/integrated_option_demo.yaml \
  --output projects/jaggedthoughts_capital/workspace/investment/decisions/strategy-example.json \
  --report projects/jaggedthoughts_capital/workspace/investment/decisions/strategy-example.md
```

The YAML declares:

- the decision owner, question, and evidence epoch;
- local sources and exact excerpts used as evidence;
- typed strategic choices and composition operators;
- external, internal, and dynamic burdens of proof;
- scenario main effects and interaction effects;
- the aggregation rule and one-choice neighborhood.

The compiler enumerates and scores every target-typed program. The output keeps
grammar exhaustion (`scope_closed`) separate from a representation-audited
decision boundary (`decision_closed`). Duplicate the profile for a company or
case, replace the source file and excerpts, calibrate the scenario factors, and
version the grammar whenever the choice language changes.

Use `--summary` for a compact status object and `--agenda` for machine-readable
selection of the next frontier-sensitive evidence test. Use
`--challenge CHALLENGER.yaml` to compare a separately authored grammar epoch
under the same evaluation surface and expose newly expressible frontier
behavior.

## Autonomous mechanism loop

The autonomous reference profile starts one layer earlier: observed strategic
transitions constrain competing executable mechanisms; recursive policies are
rolled through every surviving mechanism; the robust frontier uses the worst
score per objective; and a guarded evidence adapter selects the next
model-discriminating readout.

Compile it:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.strategy.autonomous_cli compile \
  examples/jaggedthoughts/autonomous_service_strategy.yaml \
  --summary
```

Advance one evidence step without modifying the source profile:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.strategy.autonomous_cli step \
  examples/jaggedthoughts/autonomous_service_strategy.yaml \
  --run-state-out projects/jaggedthoughts_capital/workspace/investment/state/strategy-run.json \
  --output projects/jaggedthoughts_capital/workspace/investment/decisions/strategy-step.json \
  --report projects/jaggedthoughts_capital/workspace/investment/decisions/strategy-step.md
```

The bundled `file_transition` adapter reads a scoped, content-hashed observation
file. Host applications may register additional adapters in code; profile data
cannot inject executable adapters. Probe selection is constrained by adapter,
action tier, primitive cost, and irreversibility allowlists. The run-state
artifact carries appended observations and temporal eligibility edges, while
the profile remains the immutable decision contract.

The compiled output also carries `diagnostics`: typed residuals for state
aliasing, exhausted mechanism languages, probe deadlocks, policy truncation,
frontier saturation, and declared representation gaps. Each residual names a
required refinement and a kill test. `summary.next_refinement_action` routes
the next bounded step instead of allowing a successful compile to imply that
the representation is adequate.

See the [capability model and operating loop](../../docs/concepts/jaggedthoughts_autonomous_strategy.md)
for the earned capability levels, structural analogues, assumptions, and
improvement sequence.
