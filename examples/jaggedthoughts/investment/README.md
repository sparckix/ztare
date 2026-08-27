# JaggedThoughts investment reference

Compile the fictional value-quality decision and record its typed leaves:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli compile \
  examples/jaggedthoughts/investment/value_quality_play.yaml \
  --output projects/jaggedthoughts_capital/workspace/investment/decisions/alpha-decision.json \
  --report projects/jaggedthoughts_capital/workspace/investment/decisions/alpha-decision.md \
  --store projects/jaggedthoughts_capital/workspace/investment/jaggedthoughts-capital.sqlite \
  --summary
```

The compiler excludes the future-dated CSV row, compiles an entity fingerprint
and a market-premium committee, enumerates source-bound valuation programs and
their expectations frontier, feeds the price-implied excess return into the
policy state, enumerates the recursive contingent policy grammar, preserves the
robust frontier across two mechanisms, selects one bounded paper action, and
writes a content-addressed decision lineage.

To settle, copy `outcome_2027q2.template.json`, replace its decision hash with
the compiled hash, then run:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli settle \
  projects/jaggedthoughts_capital/workspace/investment/decisions/alpha-decision.json \
  projects/jaggedthoughts_capital/workspace/investment/outcomes/alpha-outcome.json \
  --output projects/jaggedthoughts_capital/workspace/investment/outcomes/alpha-scorecard.json \
  --store projects/jaggedthoughts_capital/workspace/investment/jaggedthoughts-capital.sqlite \
  --summary
```

Inspect the append-only store with `store verify`, `store list`, `store show`,
or `store lineage`. Embedding receipts may later point to a vector index, but
the vectors remain a disposable retrieval projection over the typed leaves.

Assemble one or more compatible entity decisions under a shared capital,
turnover, position, and weighted-downside budget:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli portfolio \
  examples/jaggedthoughts/investment/portfolio_assembly.yaml \
  --output projects/jaggedthoughts_capital/workspace/investment/portfolio/reference-portfolio.json \
  --store projects/jaggedthoughts_capital/workspace/investment/jaggedthoughts-capital.sqlite \
  --summary
```

The reference profile contains one entity and therefore exercises the complete
portfolio transaction without claiming cross-entity value. Additional source
profiles must share the owner, decision epoch, benchmark, currency, and starting
paper book. The assembler evaluates exact accept-or-decline combinations inside
its declared population bound, keeps the Pareto frontier, and records dominance
witnesses plus the declared utility receipt.

The price-action lane evaluates a frozen proposal against at least one frozen
control:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli price-eval \
  examples/jaggedthoughts/investment/price_action/lagrangian_candidate.json \
  examples/jaggedthoughts/investment/price_action/outcome.json \
  --baseline examples/jaggedthoughts/investment/price_action/historical_mean_control.json
```

These files are synthetic. The Lagrangian-labelled candidate predicts both
return and a linked observable; the evaluator checks chronology, identical
entity/period coverage, error against the control, and after-cost directional
policy return. It does not derive the candidate or authorize capital.

Run a multi-episode world-model tournament:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli tournament \
  examples/jaggedthoughts/investment/world_model_tournament.yaml \
  --output projects/jaggedthoughts_capital/workspace/investment/experiments/alpha-world-model-tournament.json \
  --report projects/jaggedthoughts_capital/workspace/investment/experiments/alpha-world-model-tournament.md \
  --store projects/jaggedthoughts_capital/workspace/investment/jaggedthoughts-capital.sqlite \
  --summary
```

The tournament fixture compares a historical control with a strategy-transition
candidate over eight quarterly inference blocks. Every walk-forward forecast is
frozen before its episode, both models cover the same outcomes, and the
Lagrangian-labelled candidate predicts owner-earnings growth, a linked
concentration change, and a margin-pressure probability. The evaluator scores
prediction loss, linked-observable loss, and after-cost benchmark-relative
return, then applies paired tests and false-discovery correction. It emits a
survivor committee and keeps all capital authority outside the tournament.
