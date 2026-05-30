# GP-026 Runner No-Suite Rejection Seam

> **Seam metadata** · `seam_id:` GP-026 · `track:` apparatus · `status:` unrecorded · `last_updated:` 2026-05-17


## Problem Snapshot

During a long Gemini hardening run on a private domain project, several low-scoring mutations were expected and legitimate. One failure mode was not.

The mutator emitted a candidate without a usable Python falsification suite. Instead of rejecting that mutation before evaluation, `autoresearch_loop.py` wrote a sentinel fallback into `test_model.py`:

```python
assert False, 'AI failed to provide a testable falsification suite.'
```

That candidate then proceeded through the normal evaluation path, producing a scored `0` iteration and updating latest artifacts.

This is fail-closed in one sense, but it is the wrong layer:

- it burns loop budget on a malformed candidate
- it contaminates `latest_eval_results.json` with a non-thesis failure
- it makes long hardening runs look noisier than they really are
- it weakens interpretability of basin-search behavior

## Current State

Before GP-026:

- missing Python suite -> sentinel `assert False` written into `test_model.py`
- unit test fails downstream
- scored `0` debate log is recorded

This behavior was first observed in a private project's debate log (kept out of this repo).

## Debate Log

### Turn 1, Why this is not just “bad mutation”

The mutator is allowed to explore bad basins. That is normal. But a candidate with no usable falsification suite is not a meaningful basin; it is a malformed artifact.

ZTARE already has Runner R1 / R3 rejection logic for malformed or inadmissible candidates. This specific case belongs there.

### Turn 2, Why it existed

The sentinel fallback was originally a pragmatic fail-closed mechanism:

- better to fail loudly than silently accept a no-test mutation

That logic is still directionally right, but in long-run hardening it is no longer the best boundary. The right behavior is:

- preserve fail-closed rigor
- reject the malformed candidate before evaluation

### Turn 3, Correct boundary

Missing-suite and explicit sentinel-suite candidates should be:

- Runner R1 rejections
- restored to best state
- logged as a malformed mutation event

They should not become scored iterations that overwrite latest artifacts.

## Conclusion

GP-026 should harden the runner so that:

- missing Python suite block -> pre-eval rejection
- explicit no-suite sentinel block -> pre-eval rejection

This keeps long hardening traces interpretable without weakening rigor.
