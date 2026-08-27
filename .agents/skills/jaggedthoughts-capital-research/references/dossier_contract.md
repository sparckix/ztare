# Candidate research dossier contract

The dossier is JSON with schema `jaggedthoughts-candidate-research-dossier-v1`. It is an evidence artifact consumed by `workspace draft-candidate`, not a capital instruction.

Required top-level fields:

```json
{
  "schema": "jaggedthoughts-candidate-research-dossier-v1",
  "request_id": "exact agent research request id",
  "request_sha256": "exact agent research request content hash",
  "candidate_leaf": "64-character golden leaf SHA",
  "candidate_sha256": "candidate payload SHA",
  "entity_id": "TICKER",
  "as_of": "source epoch timestamp",
  "generated_at": "research completion timestamp",
  "thesis": {
    "claim": "causal, conditional claim",
    "mechanism": "choices -> earnings power -> expectations gap",
    "confidence": 0.0
  },
  "rival_view": {
    "claim": "strongest competing explanation",
    "mechanism": "competing causal chain"
  },
  "decisive_observation": {
    "observation": "future evidence that separates the mechanisms",
    "horizon": "date or reporting window",
    "thesis_if": "expected result under thesis",
    "rival_if": "expected result under rival"
  },
  "falsifiers": [
    {"condition": "observable failure", "horizon": "date/window", "source_plan": "where to check"}
  ],
  "catalysts": [
    {"event": "expectations-changing event", "horizon": "date/window", "mechanism": "why it matters"}
  ],
  "strategy": {
    "choices": [{"id": "choice", "description": "committed choice", "evidence_refs": ["source-id"]}],
    "reinforcing_edges": [{"from": "choice", "to": "choice", "mechanism": "reinforcement", "evidence_refs": ["source-id"]}],
    "tradeoffs": ["what the company deliberately does not optimize"],
    "frontier_move": "local strategic move or threat that changes attainable outcomes",
    "representation_residuals": ["important omitted structure"],
    "feasibility_constraints": {
      "incompatibilities": [
        {"constraint_id": "exclusive-paths", "option_ids": ["choice-a", "choice-b"], "evidence_refs": ["source-id"]}
      ],
      "prerequisites": [
        {"constraint_id": "requires-platform", "option_id": "choice-b", "requires": ["choice-a"], "evidence_refs": ["source-id"]}
      ],
      "resources": [
        {"constraint_id": "capacity", "resource_id": "qualified-lines", "unit": "lines", "limit": 2, "uses": [{"option_id": "choice-a", "amount": 1}], "evidence_refs": ["source-id"]}
      ]
    },
    "constraint_challenge_examples": {
      "admitted_bundles": [
        {"example_id": "observed-together", "option_ids": ["choice-a"], "evidence_refs": ["source-id"]}
      ],
      "excluded_bundles": [
        {"example_id": "explicitly-rejected-pair", "option_ids": ["choice-a", "choice-b"], "evidence_refs": ["source-id"]}
      ],
      "implication_pairs": [
        {"example_id": "explicit-prerequisite", "antecedent_option_ids": ["choice-b"], "required_option_ids": ["choice-a"], "evidence_refs": ["source-id"]}
      ]
    }
  },
  "industry": {
    "profit_pool": "where economic profit accrues",
    "rival_responses": ["likely competitor response"],
    "customer_and_supplier_power": "mechanism summary",
    "substitution_and_entry": "mechanism summary",
    "cycle_and_regulation": "material state variables"
  },
  "durable_earnings_bridge": {
    "revenue_durability": "qualitative evidence beyond accounting persistence",
    "earnings_quality_adjustments": ["normalization issue"],
    "reinvestment_and_capital_allocation": "incremental returns and allocation behavior",
    "concentration_and_fragility": ["customer, product, geography, supplier, financing risk"]
  },
  "valuation_assumptions": {
    "base_growth": 0.03,
    "terminal_growth": 0.025,
    "why": "source-bound rationale and sensitivity caveat"
  },
  "strategy_event_assessment": {
    "move_observation_sha256": "exact trigger move hash",
    "event_research_request_sha256": "exact trigger request hash",
    "status": "supports_thesis|supports_rival|mixed|unresolved",
    "finding": "what the opened evidence establishes",
    "durable_earnings_implication": "bounded operating implication",
    "valuation_implication": "bounded expectations or valuation implication",
    "evidence_refs": ["source-id"]
  },
  "sources": [
    {
      "id": "source-id",
      "title": "document title",
      "url": "https://...",
      "publisher": "publisher",
      "published_at": "date or timestamp",
      "accessed_at": "timestamp",
      "source_kind": "filing|issuer|regulator|government|research",
      "supports": ["bounded claim ids"]
    }
  ]
}
```

When the work begins from an agent research request, `request_id` and `request_sha256` are required. Run `workspace submit-dossier <path>` for every request-bound dossier. The kernel validates the exact request and candidate identity, adds `dossier_sha256`, records a golden-store leaf, and advances the research job projection to `researched`. Monitor and fund candidates stop there; only a qualified public-equity candidate can proceed through `draft-candidate`.

The kernel enforces identity and required sections. The skill is responsible for source quality, internal consistency, and ensuring every material assertion has an evidence reference.

`strategy_event_assessment` is required only when the immutable research request
contains `strategy_event_trigger`; otherwise omit it. Copy both hashes exactly.
Every cited source must include the exact token
`strategy_event:<move_observation_sha256>` in `supports`. The kernel rejects a
missing assessment, crossed event identity, or unsupported event source. This field
orders and structures learning research; it cannot change screen state, security
rank, paper policy, or capital authority.

Admission requires at least two opened HTTPS sources, including at least one `filing`, `issuer`, `regulator`, or `government` source. Every strategy choice and reinforcing edge must carry nonempty `evidence_refs`, and each reference must resolve to a declared dossier source ID.

The strategy grammar admits one to eight choices. Every reinforcing edge's
`from` and `to` values must exactly equal ids in `strategy.choices`. This lets
the kernel canonicalize the directed graph up to choice naming and use repeated
topologies as cross-entity challenger prompts. A topology match does not imply
shared mechanism meaning, earnings effects, or prospective return.

All three feasibility arrays are required and may be empty. A row is admissible
only when every referenced opened primary source includes the exact support token
`strategy_constraint:<constraint_id>`. Constraint option ids must be exact choice
ids. Resource uses require nonnegative numeric amounts in one declared unit.
Qualitative tension, inferred capacity, and ordinary tradeoffs stay outside Z3.
Every challenge example must cite an opened primary source whose `supports`
contains `strategy_constraint_example:<example_id>`. An exclusion or implication
also requires at least one separately sourced admitted bundle. The deterministic
replay admits predicates only when one inclusion-minimal candidate set explains
the observed bundle dispositions.
