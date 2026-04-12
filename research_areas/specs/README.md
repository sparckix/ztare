# Specs

Spec files are the blueprint layer.

They should be clean, implementation-facing, and separate from the messy debate.

Specs follow the same visibility rule as seams/drafts/board rows:

- public when shipped/closed and free of exploit content / first-mover IP
- private otherwise

When in doubt, default private.

Layout:

- `research_areas/specs/active/`
- `research_areas/specs/archive/`
- `research_areas/private/specs/active/`
- `research_areas/private/specs/archive/`

Naming rule:

- `<ID>_<slug>_spec.md`

Examples:

- `GP-021_topological_pivot_heuristics_spec.md`
- `GP-022_forecast_project_typing_spec.md`

Formatting is governed by:

- `research_areas/private/kernel/ztare_spec_format.md`
