---
description: "Forward-looking eigenquestions for ZTARE after the cognitive-firm kernel pass."
---
# GP-245 ZTARE Forward Eigenquestions

Date: 2026-05-20

## Read

ZTARE has enough governance primitives to run itself: forecast contracts,
scientific-yield decomposition, action intelligence, trajectory mining, catch
ledger, experiment ledger, post-tick gates, and public smoke targets. The next
constraint is whether those surfaces close the loop:

```text
signal -> decision changed -> action taken -> outcome observed -> learning promoted -> recurrence reduced
```

GP-244 already shows the gap. The system has hundreds of forecast contracts,
GP-233 rows, experiment rows, finding rows, and catch rows. The weak point is
not signal generation; it is durable evidence that signals changed decisions
and suppressed repeated failure modes.

## Eigenquestions

| # | Eigenquestion | Why it matters | Existing primitives | Pull-forward |
|---:|---|---|---|---|
| 1 | Can GP-230 become a decision market rather than a calibrated forecast archive? | Forecasts matter when they change allocation, precondition execution, or retire branches. | Forecast contracts, aggregates, outcomes, scores, calibration, reflexive insights. | Make aggregate consumption produce or require a decision-use row; treat ignored aggregates without reason as source-health debt. |
| 2 | Can GP-243 bind forecasts, catches, GP-233 rows, and trajectory surfaces into action-impact evidence without becoming live policy control? | This is the training and evaluation table for organizational learning. | `action_intelligence.py`, action-impact ledger, source health, shadow recommendations. | Keep GP-243 advisory; auto-derive rows from GP-230 decision use and surfacing consumption. |
| 3 | Can GP-233 yield decomposition become structured enough to route work across substrates? | Markdown rows explain bottlenecks, but weak joins block reliable metrics and policy learning. | GP-233 seam/spec, evidence ledger, bottleneck and next-lever vocabulary, post-tick decision-change requirement. | Add a derived structured read model keyed by `tick_id`, `project_id`, `contract_id`, `lane_id`, `decision_changed`, and `next_lever`. |
| 4 | Can trajectory and catch mining prove recurrence suppression, not just recurrence detection? | The apparatus catches failures; the stronger claim is that catches prevent later repeats. | Catch ledger, trajectory archives, recursive-gain candidates, anti-pattern catalog, amnesia manifests. | Add catch-preconditioner consumption and avoidance rows; backtest top catch categories against later runs. |
| 5 | Can GP-244 become the operator attention surface without inventing authority? | Intelligence surfaces are useful only if they remain honest about weak joins and do not become hidden routers. | Operations intelligence dashboard, source map, ETL manifest, learning candidates. | Add promote/defer/reject/source-fix review states while keeping routing authority in explicit protocols. |
| 6 | Can research-flow metrics reward depth and recovery rather than shallow closure speed? | Flow metrics are useful only when paired with depth receipts, failure recovery, and rework. | `post_tick_check.py`, depth-sensitive `research_done.json`, trajectory curves, experiment ledger. | Join question-to-contract, contract-to-evidence, evidence-to-close, and gate-fail-to-recovery timestamps. |
| 7 | Can the repo graph and primitive surfaces be consolidated by consumer query rather than file movement? | Moving canonical ledgers would break consumers; logical consolidation can still improve navigation. | Knowledge graph targets, query helpers, architecture index, primitive surfaces. | Build graph/read-model consolidation under private analytics first; require edge-loss diffs before public promotion. |
| 8 | Can ZTARE keep the cognitive-firm boundary clean while advancing tenant-specific intelligence? | Generic governance belongs in cognitive-firm; ZTARE-specific research markets and yield overlays should not leak back as generic policy too early. | README boundary, GP-191, GP-230, GP-243, org runtime, membrane. | Promote only generic interfaces, such as action-impact view, source-health view, and learning-event lifecycle. Keep research-market semantics in ZTARE until generalized. |

## Gate Pull-Forwards

The public verification spine should include:

```bash
make smoke-public
make public-adversarial-smoke
make docs-check
make gates
make smoke-docker
```

Additional ZTARE-local checks should stay explicit rather than hidden inside
the generic public smoke:

```bash
./venv/bin/python scripts/public/control/forecast/pool.py materialize-state
./venv/bin/python scripts/public/control/action_intelligence.py materialize
./venv/bin/python scripts/public/control/action_intelligence.py health
./venv/bin/python scripts/public/control/operations_intelligence_dashboard.py --html analytics/private/intelligence/ztare_intelligence_surface.html
./venv/bin/python -m pytest tests/reports/test_operations_intelligence.py -q
```

The new `public-adversarial-smoke` target checks four claims:

- runtime smoke cleans up its synthetic artifacts;
- forecast-pool smoke can run in an isolated temporary root;
- action-intelligence fixture checks reject unsafe live-row shapes;
- Makefile, docs, and `.gitignore` keep public/private boundaries aligned.

## Reorganization

Reorganize by read model first, not by moving canonical files. The repo has many
consumers that expect ledgers in their current paths. A physical move should
wait until a graph/read-model layer proves no consumer edges were lost.

Near-term:

- keep canonical ledgers where scripts already read them;
- use `LEDGERS.md`, source maps, and private analytics read models as the
  navigation layer;
- add edge-loss checks before any directory move;
- keep private intelligence outputs under ignored private paths unless they pass
  explicit publish-safety review.

## External Grounding

The direction matches established cautions: March on exploration and
exploitation; Cohen and Levinthal on absorptive capacity; SPACE and DORA on
multidimensional productivity and flow; the Leiden Manifesto on metrics
supporting judgment; Wolfers and Zitzewitz plus Hanson on prediction markets
and scoring; and Amodei et al. on reward hacking, side effects, safe
exploration, and distribution shift.
