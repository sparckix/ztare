---
description: "Canonical registry and protocol for graph records and decision receipts used by ZTARE."
---

# Graph Interfaces

> **Up:** [Documentation map](../README.md)

ZTARE already uses several graph-shaped records: probability DAGs in the
in-loop validator, primitive-family edges in the capability surface, source to
claim graphs in project intake, and the Navier-Stokes constraint-basin graph.
This page defines the common interface for those records so graph work can be
reused without turning every project into a special case.

Older code and a few schema names use `graph_carrier`. Treat that as the
implementation name for a graph record plus a decision receipt. Public docs
should prefer graph record, graph diagnostic, or graph decision receipt unless
they are naming a literal field, file, or historical operator card.

Graph diagnostics are structural orientation and accounting aids. They do not
prove a theorem, validate a claim, or replace a domain gate. A graph result
becomes useful only when it records what changed in the next decision.
The typed schema guard lives in
[`src/ztare/common/graph_carrier.py`](../../src/ztare/common/graph_carrier.py).

## Interface Contract

Every promoted graph record should declare:

| Field | Meaning |
|---|---|
| `graph_id` | Stable id for the graph family and version. |
| `graph_kind` | One of the registered kinds below, or a new kind with rationale. |
| `producer` | Command, module, or extraction rule that builds the graph. |
| `source_artifacts` | Files or ledgers read by the producer. |
| `consumer` | Module, gate, report, or research workflow that reads the graph. |
| `freshness_rule` | What makes the graph stale and how freshness is checked. |
| `node_vocabulary` | Node types and whether they are domain-specific. |
| `edge_vocabulary` | Edge types and whether direction or weights matter. |
| `diagnostics` | Graph algorithms run and the baseline they compare against. |
| `noise_filter` | Plumbing, aliases, generated binders, or low-signal edges removed. |
| `decision_receipt` | The decision effect: `strategy_change`, `no_strategy_change`, or `misleading_or_noise`. |
| `non_use` | If a graph exists but was not used, the reason. |
| `library_anchor` | External library used, such as NetworkX or igraph. |
| `literature_anchor` | Nearest method family in the literature when a diagnostic is not standard. |

The decision receipt is required because a graph metric with no downstream
effect is only orientation. The minimal receipt names the selected next
discriminator, the route demoted, or the reason the graph output was ignored.

## Executable Audit

Run the current boundary check with:

```bash
make graph-capability-audit
```

The audit classifies each graph surface as a standard algorithm with a ZTARE
adapter, a ZTARE recombination layer, a ready receipt path, or a research
candidate that still needs a benchmark. It is meant to keep release wording
honest: the base graph algorithms remain standard-library backed; the ZTARE
claim is the artifact-extraction, sink/claim conditioning, perturbation,
disagreement, action-card lowering, and decision-receipt layer where those are
present.

## Registered Graph Kinds

| Kind | Current producer | Current consumer | Status |
|---|---|---|---|
| `probability_dag` | `latest_probability_dag.json` from the autoresearch workspace | `compute_dag_steering_context` in `src/ztare/validator/autoresearch_loop.py`; circularity and falsifiability gates | `generic_now` |
| `primitive_capability_graph` | `src/ztare/architecture_index/graph.yaml` plus the primitive catalog | `primitive_tick_surface._load_graph_bonus` and RD briefing surfaces | `generic_now`, curated |
| `constraint_basin_graph` | NS graph extractors through `projects/ns_millennium_hunt/scripts/ns_graph.py` and query JSONs | NS precheck, workmap/report generation, and graph diagnostic pattern | `generic_after_adapter` by method; some fields remain `ns_private` |
| `source_claim_graph` | `workspace/source_index.json`, compiled provenance, compiled claim packet, evidence text, evidence gaps | Autoresearch trace and recovery actions | `generic_now` |
| `code_dependency_graph` | Planned dependency scanner over project code and reproduction scripts | Reproduction-cost estimates and setup-risk routing | `planned` |

New graph kinds should be added here before a second consumer is built. If the
graph is intentionally domain-private, say so and name the boundary.

Autoresearch loop caveat: `probability_dag` is already a real in-loop graph
record.
`src/ztare/validator/probability_dag_carrier.py` now owns the shared JSON
parser, urgency scorer, vulnerable-assumption renderer, and graph decision
receipt builder. `autoresearch_loop.py` now renders one
`probability_dag_context` prompt block through `compute_dag_steering_context()`;
steering remains gated by `enable_dag_steering`, while the vulnerable-assumption
view is emitted when a usable DAG exists. Forecast/Elo/Brier signals belong
behind a separate prediction contract first; they should not steer autoresearch
iterations until per-iteration predictions are emitted, resolved, and shown to
beat simple baselines.

## NS Basin Harvest

The NS basin stack contains graph algorithms that are broader than NS, but
they have not yet been harvested into a general interface or reused across both
in-loop and out-of-loop flows. The first task is classification, not a new
engine.

| Method family | Current use | Framework coverage | Possible ZTARE contribution |
|---|---|---|---|
| Min-cut and bottleneck paths | Identify fragile proof-spine bridges | Standard in NetworkX/igraph | Lean-signature extraction, plumbing filter, witness edge rendering, sink-conditioned interpretation |
| Dominators | Identify mandatory corridors into a target | Standard in NetworkX | Synthetic super-source over sink ancestors, proof-route interpretation |
| Weakly/strongly connected components | Detect disconnected or decorative regions | Standard | Substrate-specific non-use and decorative-route receipts |
| Feedback-arc and cycle analysis | Expose circular or backwards dependencies | Partly standard; current implementation uses capped cycle participation | Cycle-to-bound-chain explanation and false-proof-edge warnings |
| Edge betweenness, PageRank, HITS, k-core | Rank central or transit nodes | Standard | Multi-method convergence/disagreement receipts with plumbing filters |
| Fiedler bisection and Louvain communities | Find structural partitions | Standard | Partition-to-obligation/route mapping and stability checks |
| k-shortest paths | Compare alternate routes into a target | Standard | Targeted route witness rendering |
| Robustness ensembles | Test whether rankings survive perturbation | Standard pattern over standard algorithms | Retraction discipline when a graph finding is not stable |
| Counterfactual edge perturbation | Estimate sensitivity to edge removal/addition | Standard pattern over standard algorithms | Decision receipt tying perturbation to changed route or no-action |
| Adamic-Adar and common-neighbor link prediction | Baseline missing-edge hypotheses | Standard | Baseline discipline before any GNN or learned predictor claim |
| Structural-role clustering | Derive role labels from graph features | Standard clustering pattern | Mechanically-derived role labels over proof/claim objects |
| F-row trajectory overlay | Planned comparison between graph salience and recorded belief updates | ZTARE-specific ledger overlay | Not promoted until a concrete ledger adapter and decision receipt exist |
| Workmap linkage | Turn graph diagnostics into next-obligation ordering | ZTARE-specific composition | Connects graph results to open obligations and next checks |

The harvest rule is conservative: promote only the algorithm and receipt shape
that transfer. NS-specific node names, proof obligations, and theorem surfaces
stay in the NS project.

## Novelty Boundary

The base graph algorithms are mostly not novel. NetworkX already exposes
minimum cut, immediate dominators, PageRank, edge betweenness, core numbers,
Louvain communities, shortest simple paths, and Adamic-Adar link prediction;
igraph covers the same general family at a different performance and API
profile. The possible ZTARE capability is the layer above those algorithms:

- extracting typed graph records from proof, run, source, or claim artifacts;
- filtering domain-specific plumbing before ranking;
- conditioning diagnostics on a sink, claim, route, or open obligation;
- comparing several algorithms and recording disagreement;
- perturbing or re-running diagnostics to retract unstable findings;
- linking graph output to a decision receipt rather than treating a metric as
  self-justifying;
- replaying the same receipt schema in in-loop and out-of-loop workflows.

The release-worthy claim, if the audit supports it, should be framed as a graph
diagnostic workbench and decision-receipt protocol for research artifacts. It
should not be framed as a replacement for NetworkX, igraph, graph neural network
libraries, or proof-specific premise-selection systems unless a benchmark
directly supports that stronger claim.

Out-of-loop consumer status: `src/ztare/research_director/graph_carrier_actions.py`
now lowers validated graph receipts into `graph_rd_actions[]` in
`autoresearch trace`. A source-claim graph with an active public-source evidence
gap becomes an `out_of_loop_evidence_recovery` prep action and blocks
`route_preview.can_run_now`; local verifier gaps, such as preflight or
falsifier-execution gaps, remain `in_loop_focus_receipt` rows. The same graph
record consumes the compiled-evidence claim-support audit: weak or unsourced
claim rows, and claim rows whose raw source context no longer verifies, become
a `strategy_change` receipt that tells the caller to repair or demote the row
before report export. A probability-DAG focus also remains an
`in_loop_focus_receipt` for the autoresearch loop.
`GraphFocusReceiptProvider` carries source-claim in-loop focus receipts into the
mutator briefing so the next patch sees the local verifier target directly.
Evidence-gap routing is schema-first: producers should set `recovery_kind`,
`recovery_channel`, or `action_type`; legacy text matching is only a
compatibility fallback for older gap rows. The source-claim graph and briefing
paths consume the nested `ztare-evidence-gap-recovery-contract-v1` object
(`can_public_fetch` / `in_loop_consumable`) so graph actions do not fork their
own gap classifier. Source-claim graph routing also requires the source
preflight to run cleanly; if source-check is unavailable or blocking, the graph
record demotes itself to `misleading_or_noise` before any evidence-gap route is
emitted.
Each `graph_rd_actions[]` row now also carries `operator_card_routes[]` and
`operator_card_ids[]` for `OP-GDC-01`, so a downstream audit can distinguish a
graph-record decision from an ad hoc evidence-prep or DAG-focus row.

Current non-NS receipt: live project traces validated the graph-record family
across public evidence gaps, local verifier gaps, and compiled-claim demotion.
The probability DAG recorded `no_strategy_change` when no steering decision row
existed; the source-claim graph recorded `strategy_change` by routing public
evidence gaps to `out_of_loop_evidence_recovery`; the later `demo_claims` live
trace showed the paired case, a local verifier gap lowered to an in-loop focus
receipt. The claim-support path now adds the report-export case: a graph record
can route weak source binding to repair/demotion before a claim is presented as
source-backed. Treat this as the model case for graph discipline: a diagnostic
either changes a decision or records why it should not.

Graph diagnostics that do matter should lower into the pattern/action-card
surface. The current historical card id is `OP-GDC-01: Graph Diagnostic
Carrier`; its contract requires the graph kind, producer, diagnostics, noise
filter, decision receipt, and the selected action card, gate, artifact slot, or
explicit non-use/retraction reason.

Current routing caveat: `OP-GDC-01` can route through an operator-card atlas,
and card instances export atlas-ready rows. The atlas is generated explicitly
with `make move-card-atlas-build`; when it is present and queryable,
graph/card rows may report `route_mode: semantic_atlas`, and when it is absent
or unreadable the deterministic card router remains the fallback. The
pattern-action contract records `operator_card_routes[]` with
`route_mode: semantic_atlas` or `route_mode: lexical_fallback`, plus matched
terms or scores. `make graph-capability-audit` reports the current atlas status
and routing mode, so release wording can check the actual state rather than the
intended capability. Do not describe graph-card selection as mature semantic
routing until the card atlas is evaluated on miss cases and used by more than
one real trace. Use `make move-card-router-audit` for the current fixed
paraphrase check; use `make move-card-router-audit SEMANTIC=1` only when a
live embedding environment is intended. The live audit reports
`semantic_error_count` instead of quietly accepting lexical fallback when the
provider path is unavailable.

External anchors for the audit:

- NetworkX algorithm references:
  [`minimum_cut`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.flow.minimum_cut.html),
  [`immediate_dominators`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dominance.immediate_dominators.html),
  [`pagerank`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_analysis.pagerank_alg.pagerank.html),
  [`edge_betweenness_centrality`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.edge_betweenness_centrality.html),
  [`core_number`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.core.core_number.html),
  [`louvain_communities`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html),
  [`shortest_simple_paths`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.simple_paths.shortest_simple_paths.html),
  and [`adamic_adar_index`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_prediction.adamic_adar_index.html).
- Nearby proof/literature anchors:
  [Graph Sequence Learning for Premise Selection](https://arxiv.org/abs/2303.15642)
  and [Premise Selection for Theorem Proving by Deep Graph Embedding](https://arxiv.org/abs/1709.09994).
- Nearby knowledge-graph anchor:
  [Knowledge Graph Reasoning with Logics and Embeddings](https://arxiv.org/abs/2202.07412).

## Mini-Engine Gate

A graph mini-engine may be justified, but only after the repo proves repeated
cross-domain use. Until then, prefer thin adapters over standard libraries
such as NetworkX or igraph.

Build a custom graph layer only when all of the following are true:

1. One non-NS project has used the interface and recorded a decision receipt.
   Current receipt: the prose-quality trace uses the source-claim graph record
   for evidence-gap recovery; `demo_claims` uses it for local verifier focus
   routing.
2. One out-of-loop workflow has consumed a graph record. Current receipt:
   `autoresearch trace` emits `graph_rd_actions[]`.
3. One in-loop autoresearch workflow has consumed a graph record. Current
   receipt: `autoresearch_loop.py` emits one `probability_dag_context` prompt
   block.
4. At least one counterexample has been recorded where the graph produced
   `no_strategy_change` or `misleading_or_noise`.
5. The custom layer is limited to ZTARE-specific duties: graph receipts,
   freshness and provenance checks, decision logging, plumbing filters, and
   handoff between graph diagnostics and gates.

The graph algorithms themselves should remain standard-library backed unless a
method is unavailable or a domain needs a formally specified extraction rule.
Source-claim graph routing is additionally gated by the same artifact-source
binding contract used by `autoresearch trace`: count-only or missing-hash source
rows can still be useful diagnostics, but they are not actionable graph routing
evidence until `kernel_entry_ok=true`.

## Current Call-Sites

- In-loop DAG steering:
  [`src/ztare/validator/autoresearch_loop.py`](../../src/ztare/validator/autoresearch_loop.py)
- Primitive graph bonus:
  [`src/ztare/research_director/primitive_tick_surface.py`](../../src/ztare/research_director/primitive_tick_surface.py)
- Architecture graph source:
  [`src/ztare/architecture_index/graph.yaml`](../../src/ztare/architecture_index/graph.yaml)
- Graph record schema guard, implementation name `graph_carrier.py`:
  [`src/ztare/common/graph_carrier.py`](../../src/ztare/common/graph_carrier.py)
- Primitive-amnesia declaration:
  `graph_carrier.py` and `source_freshness.py` are listed in
  [`primitive_amnesia.PRIMITIVE_MODULES`](../../src/ztare/research_director/primitive_amnesia.py).
  After changing the graph record (`graph_carrier.py`) or source-freshness API, refresh the primitive catalog and atlas:
  `make primitive-catalog-repopulate` and, with an embedding key,
  `make primitive-catalog-build-atlas`. Until that atlas refresh runs, the
  primitive is lexically declared but may not appear in semantic recall.
- Graph capability audit:
  [`src/ztare/reports/graph_capability_audit.py`](../../src/ztare/reports/graph_capability_audit.py)
- Graph action-card lowering:
  [`src/ztare/research_director/primitive_operator_cards.py`](../../src/ztare/research_director/primitive_operator_cards.py)
  and
  [`src/ztare/research_director/pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py)
- NS graph front door:
  [`projects/ns_millennium_hunt/scripts/ns_graph.py`](../../projects/ns_millennium_hunt/scripts/ns_graph.py)
- Graph diagnostic pattern:
  [`graph_diagnostic_belief_update_pattern.md`](graph_diagnostic_belief_update_pattern.md)
