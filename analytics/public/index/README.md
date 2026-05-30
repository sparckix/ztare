# analytics/public/index/

Architecture / artifact indexes (~13 code references). The
architecture index is the precheck channel agents consult before
proposing work (the amnesia-basin entrypoint).

- `architecture_index.jsonl` - the indexed artifact graph; validated
  by `scripts/public/validators/validate_architecture_index.py`.
- `mathlib_graph/` - a 243 MB Mathlib dependency graph used by the
  GP-225 premise-selection work. **Gitignored** (regenerable, large);
  not an archive target.

Read by the precheck and the reference-graph miners.
