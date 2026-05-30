# analytics/public/closure_metric_specs/

Declarative specs for closure-progress metrics (referenced once in
code). Each file pins how a closure signal is computed so the metric
cannot be silently redefined.

- `chokepoint_declaration.json` - the declared binding constraint /
  chokepoint for a closure line.
- `closure_progress_monotonicity.json` - the monotonicity contract a
  closure metric must satisfy (guards against Goodhart on "progress").

Specs, not outputs. Stable; change only with an accompanying gate.
