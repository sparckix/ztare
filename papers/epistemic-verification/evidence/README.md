# Evidence: Chapter 2.5 (within-case iteration analysis)

This packet lets a third party reproduce every quantitative claim in
Chapter 2.5 from public, version-controlled sources. Chapter 2.5 reports
within-case evidence from a single adversarial-verification system: it
characterises how that one system behaved across its scored iterations.
The figures are not independent replication on another system, and the
packet does not present them as such — it makes them auditable.

## Chain of evidence

Three sources, all git-tracked in this repository:

1. `analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl`
   — one record per scored iteration: `project`, `iter_timestamp`,
   `score`, judge/mutator model ids, rubric/charter hashes, and the
   free-text `weakest_point` critique written by the Meta-Judge.
2. `analytics/public/queries/classification/weakest_link_clusters_2026-04-24.json`
   — the regex/cluster fast-path: `(project, iter_timestamp) -> cluster_id`.
3. `analytics/public/queries/classification/weakest_link_llm_subclasses_2026-04-24.json`
   — finer labels (OpenAI `gpt-4.1-mini`) for the records the fast-path
   left as `other_unclustered`.

The two classification files are **cached classifier outputs**. Rebuilding
the dataset reuses those labels; it does not call any model. The only
computation between the sources and the paper's numbers is deterministic
arithmetic.

## Reproduce

```sh
export ZTARE_REPO_ROOT=/path/to/this/repo
python reproducers/build_classified_dataset.py    # -> chapter25_classified_iterations.jsonl
python reproducers/verify_chapter25_claims.py     # prints the bucket counts, lift table, persistence profile
```

`chapter25_classified_iterations.jsonl` is the frozen, joined dataset the
paper analyses (2,395 classified, scored iterations). It is committed here
so the second script runs without rebuilding; the first script regenerates
it from the sources above.

## Snapshot note

The live archive keeps growing; the classification caches were frozen on
2026-04-24. The join therefore covers the iterations present in both the
current archive and the caches — 2,395 records across 121 projects,
2026-04-09 to 2026-05-04. An earlier draft of this chapter reported a
1,825-iteration snapshot that was never frozen and is no longer
recoverable; the numbers in the current paper are exactly what
`verify_chapter25_claims.py` prints for the committed dataset. The
qualitative finding (two failure-class regimes; a monotonic persistence
profile) is unchanged.

## Data-integrity caveat

Some iterations predate a fully sealed tool-use corridor (see the paper's
scope statement). That caveat applies to this corpus as to the rest: raw
auto-tool stdout was not retained for the earliest runs, so the absence of
boundary-crossing cannot be proven retroactively. No result is withdrawn
on that basis.
