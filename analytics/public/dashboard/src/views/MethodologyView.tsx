// Publish-safety (dashboard_publish_safety_spec_2026_05_17 M1): the
// contextualized-rater primer is the operator's PRIVATE memory index and
// MUST NOT be inlined into the public bundle. The verbatim-primer panel
// and its `?raw` import were removed; the methodology is described
// publicly without dumping the private anchor.

export function MethodologyView() {
  return (
    <>
      <div className="methodology">
        <h3>How the trajectory dashboard is computed</h3>
        <p>
          The dashboard combines four independent measurement pipelines, all
          deterministic + filesystem-based (except the taste rater, which is
          LLM-based via a cold sub-agent or LLMRuntime call). Each pipeline
          writes a JSON to <code>analytics/queries/</code>; this UI imports
          them at build time.
        </p>
        <ol>
          <li>
            <strong>Volume mining</strong>{" "}
            (<code>scripts/mining/mine_trajectory_curves.py</code>) — walks
            apparatus dirs, bins per-week file creation by frontmatter date /
            stat birthtime / mtime. Produces 9 curves (sophistication ×2,
            insight ×5, confound ×2).
          </li>
          <li>
            <strong>Inflection detection</strong>{" "}
            (<code>scripts/mining/detect_inflections.py</code>) — MAD-based
            change-point detector per curve, then multi-metric convergence
            check: a week is a <em>real inflection</em> iff ≥3 of the 6
            quantitative curves show coincident step-changes there.
          </li>
          <li>
            <strong>Reference-graph mining</strong>{" "}
            (<code>scripts/mining/mine_reference_graph.py</code>) — extracts
            citations from every apparatus markdown via two regex patterns
            (<code>GP-NNN</code> identifiers + file-path references). Builds
            a directed graph; per-week aggregates inbound/outbound edge counts
            and a compounding ratio (out_to_earlier / nodes).
          </li>
          <li>
            <strong>Taste rating</strong>{" "}
            (<code>sample_artifacts_for_taste.py</code> →{" "}
            <code>build_context_primer.py</code> → cold sub-agent →{" "}
            <code>aggregate_taste.py</code>) — stratified sample of ~25
            artifacts/week × 11 kinds, blinded by week, rated 0–5 against a
            contextualized primer. Ratings persist in{" "}
            <code>taste_ledger.json</code> keyed by content SHA so re-runs
            are cheap.
          </li>
        </ol>

        <p>
          <strong>Cost discipline:</strong> ratings are content-hash cached.
          A re-run only rates artifacts whose content changed. Bumping{" "}
          <code>CODE_VERSION</code> in the sampler/aggregator (or running{" "}
          <code>invalidate_ledger.py</code>) selectively invalidates stale
          entries when a bug fix or primer change lands.
        </p>

        <p>
          <strong>Honest limitations:</strong> N=7 weeks is too short for
          inferential change-point detection. Per-artifact taste mean is
          bounded by the 0-5 scale, so total apparatus-output gain shows up
          as count×mean (volume rises, mean stays flat-to-rising → product
          compounds). The contextualized rater is anchored on a primer, so
          changes to the primer change the rating distribution.
        </p>
      </div>

      <div className="panel">
        <h3>About the contextualized primer</h3>
        <p style={{ fontSize: 13, color: "#666", margin: 0 }}>
          The contextualized rater reads a project-specific primer before
          rating any sample, which establishes what counts as central in
          this codebase and calibrates the 0–5 scale via worked examples.
          The primer is an internal calibration artifact and is intentionally
          not reproduced in this public dashboard; the rating methodology
          above is what it operationalizes.
        </p>
      </div>
    </>
  );
}
