# Hypothesis Bundles

This directory is human-owned exploration space.

Use one subdirectory per candidate hypothesis:

```text
hypotheses/
  safe_asset_convergence/
    thesis.md
    notes.md
    test_model.py      # optional
  response_latency/
    thesis.md
    notes.md
    test_model.py      # optional
```

Rules:

- `thesis.md` in the project root is the active object the loop evaluates.
- `test_model.py` in the project root must travel with the active thesis, or be deleted so the runner fails closed and regenerates a placeholder.
- `workspace/` remains machine-owned. Do not store exploration notes there.
- `.active_bundle.json` in the project root tracks which hypothesis bundle is currently active.

Promotion workflow:

1. Edit a candidate bundle under `hypotheses/`.
2. Promote it with:

```bash
python projects/eu_union_stability/promote_hypothesis.py safe_asset_convergence
```

3. Run the loop fresh.

Promotion now auto-snapshots the outgoing active branch before switching:

- it reads `.active_bundle.json` (or infers the active bundle from matching root files on first use)
- it saves the current root `thesis.md` and `test_model.py` back into that active bundle
- then it promotes the new bundle into the root
- then it updates `.active_bundle.json`

If first-use inference fails because the current root does not exactly match any bundle,
you can force the snapshot source explicitly:

```bash
python projects/eu_union_stability/promote_hypothesis.py response_latency \
  --assume-current comparative_fragility_67
```

If a bundle has no `test_model.py`, promotion deletes the project-root `test_model.py` so the next run cannot accidentally evaluate the new thesis with a stale old suite.

If a bundle does have `test_model.py`, promotion prints a warning-only
"operational neighborhood" report:

- it extracts a proxy signature from the suite using deterministic AST parsing
- it compares that signature to other bundled suites with Jaccard distance
- it warns when the new bundle looks operationally very close to an existing one

This does not block promotion. It is a cheap guard against re-entering the same
operational basin by accident.

Optional:

- Pass `--clear-status` to archive stale workspace status files for operator clarity.
- Pass `--warn-threshold 0.30` (or another value) to tune the warning distance.
- Pass `--no-snapshot` to skip auto-saving the outgoing active branch before switching.
- Pass `--assume-current <bundle>` to preserve the current root into a specific bundle when no active-bundle state exists yet.

This is an operator workflow, not a kernel feature.
