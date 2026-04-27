# GP-123 — Underutilized Bayesian DAG: Closing the Decision Loop

**Status:** OPEN
**Opened:** 2026-04-22
**Category:** Apparatus / Engine / Decision Infrastructure

## Eigenquestion

Every iteration produces a probability DAG with nodes like
"N1: functional form is correct, p=0.6" and edges with weights.
We generate it, save it to latest_probability_dag.json, and
never USE it to make decisions. The DAG is a dead-end artifact.

## What the DAG Contains

Each DAG has:
- An outcome node with overall probability
- 3-5 intermediate nodes, each with a probability
- Edges with weights (how much each node contributes to the outcome)
- Watch signals (what observable would change this node's probability)

## What the DAG Should Drive

1. **Inverter targeting (GP-119):** The Inverter should READ the DAG
   and propose tests for the WEAKEST node (lowest probability).
   Currently the Inverter generates tests generically. The DAG tells
   it exactly where to look.

2. **Iteration budget allocation:** If all nodes are above 0.8, stop
   iterating (the thesis is well-supported). If any node is below 0.3,
   the thesis has a structural weakness that iteration alone won't fix.

3. **Topological pivot trigger:** Instead of using stagnation_count
   (a proxy), use the DAG: if the weakest node's probability hasn't
   changed in 3 iterations, the loop is stuck on that specific
   assumption, and the pivot should target it.

4. **GP-113 feedback targeting:** The failure diagnostic should
   reference the specific DAG node that the compression failure
   maps to, not just the general failure.

5. **Cross-substrate learning:** If the same DAG node is weak across
   3+ substrates ("functional form validity in the tail"), that's
   a systematic apparatus weakness, not a substrate-specific problem.

## Connection to GP-070 (Strategy Office)

The strategy office (GP-070 Goal Orchestrator) should read DAGs
across all active projects and allocate operator attention to the
project with the weakest DAG. This is the Chandlerian general
office function: strategic resource allocation based on divisional
performance metrics.

The DAG IS the divisional performance metric. It just isn't wired
to the general office.

## Implementation Path

1. Inverter reads latest_probability_dag.json, targets weakest node
2. Stagnation detection uses DAG node delta instead of score delta
3. GP-113 maps failure to specific DAG node
4. GP-070 aggregates DAGs across projects

## Checklist

- [ ] Wire DAG to Inverter (GP-119): target weakest node
- [ ] Wire DAG to stagnation detector: node-level stagnation
- [ ] Wire DAG to GP-113: failure → node mapping
- [ ] Wire DAG to GP-070: cross-project DAG aggregation
