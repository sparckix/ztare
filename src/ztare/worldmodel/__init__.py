"""World-model synthesis over interactive grid substrates (GP-250 P0').

The subsystem treats an interactive environment as an open conjecture about a
transition law: episodes are the search, and a ratified transition program is
the closure. Layout:

- `grid_dsl`: the typed seed grammar and evaluator for transition programs.
- `episode_log`: the canonical append-only `(s, a, s')` record; every other
  module reads the log, never a live environment.
- `synthesis`: enumeration + MDL ranking + behavioral dedup over the log.
- `gates`: replay-consistency and rollout-depth gates (fail-closed).
- `policy`: expected-information-gain action selection with typed fallbacks.
- `harness`: the pre-registered BC-0/1' runner for the sealed synthetic suite.

Seam of record: research_areas/seams/substrates/arc/GP-250_*.md.
"""

__all__: list[str] = []
