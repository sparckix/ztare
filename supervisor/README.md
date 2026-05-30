# Supervisor Control Plane

This directory holds the supervisor-owned control artifacts.

Contents:
- `program_registry.json`, curated routable program portfolio
- `program_genesis/`, immutable genesis artifacts for accepted programs
- `program_manifests/`, mutable packet backlogs for active programs
- `proposed_manifests/`, pre-registry planning outputs from seed-to-plan work
- `agent_wrappers.json`, configured launch commands for thin agent wrappers
- `model_pricing.json`, optional pricing matrix for budget-aware refinement; disabled by default

What does not belong here:
- seed specs
- tactical debate logs
- benchmark outputs

Those remain in:
- `research_areas/`
- `research_areas/debates/`

Human-readable rendered plans live in:
- `research_areas/program_plans/`
- `research_areas/proposal_plans/`
