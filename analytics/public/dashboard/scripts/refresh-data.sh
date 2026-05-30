#!/usr/bin/env bash
# Refresh dashboard data: rebuild the canonical bundle from the latest
# query/ledger JSONs and stage it (plus per-dataset copies as
# fallback) into the dashboard's src/data/ and public/data/.
#
# Run once to bootstrap, and again after each pipeline re-run.

set -euo pipefail

DASHBOARD_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$DASHBOARD_DIR/../../.." && pwd)"
QUERIES="$REPO_ROOT/analytics/public/queries"
PUBLIC_DATA="$DASHBOARD_DIR/public/data"
SRC_DATA="$DASHBOARD_DIR/src/data"

mkdir -p "$PUBLIC_DATA" "$SRC_DATA"

# 1. Rebuild the canonical dashboard bundle from the source datasets.
# The bundle is what the React app statically imports (see
# src/lib/data.ts); the per-dataset files below remain as a
# dev-mode fallback and to keep safe-build.sh's graph sanitization
# pointed at a stable file path.
PYTHON="$(command -v python3 || command -v python)"
"$PYTHON" "$REPO_ROOT/scripts/public/mining/build_dashboard_bundle.py" \
  --out "$QUERIES/dashboard_bundle.json"
cp "$QUERIES/dashboard_bundle.json" "$SRC_DATA/dashboard_bundle.json"
cp "$QUERIES/dashboard_bundle.json" "$PUBLIC_DATA/dashboard_bundle.json"
echo "  staged dashboard_bundle.json → src/data + public/data"

# 2. Per-dataset fallback copies. The bundle above is the load-bearing
# input; these stay because (a) safe-build.sh's graph sanitization
# operates on reference_graph.json directly, and (b) dev-server mode
# fetches individual JSONs from public/data/.
CORE_JSONS=(
  "trajectory_curves.json"
  "inflection_candidates.json"
  "taste_weighted_insight.json"
  "reference_graph.json"
  "consequential_artifacts_by_week.json"
  "recursive_gain_candidates.json"
  "bifurcation_report.json"
  "graph_sowhat.json"
  "p0_metrics.json"
)
for f in "${CORE_JSONS[@]}"; do
  case "$f" in
    trajectory_curves.json|inflection_candidates.json|taste_weighted_insight.json)
      src="$QUERIES/trajectory/$f"
      [[ "$f" == "taste_weighted_insight.json" ]] && src="$QUERIES/taste/$f"
      ;;
    reference_graph.json)
      src="$QUERIES/$f"
      ;;
    consequential_artifacts_by_week.json|recursive_gain_candidates.json)
      src="$QUERIES/trajectory/$f"
      ;;
    bifurcation_report.json|p0_metrics.json)
      src="$REPO_ROOT/analytics/public/ledgers/reflexive/$f"
      ;;
    *)
      src="$QUERIES/$f"
      ;;
  esac
  if [[ -f "$src" ]]; then
    cp "$src" "$SRC_DATA/$f"
    cp "$src" "$PUBLIC_DATA/$f"
    echo "  copied $f → src/data + public/data"
  else
    # Write empty placeholder so the static import doesn't break
    if [[ ! -f "$SRC_DATA/$f" ]]; then
      echo '{}' > "$SRC_DATA/$f"
      echo "  (placeholder created — $f not yet generated)"
    fi
  fi
done

# Optional secondary JSONs — only copied to public/ for runtime fetch
# in case future views want them; not statically imported.
for f in process_catalog.json structural_analogies.json cross_audit_dashboard.json; do
  src="$QUERIES/$f"
  [[ "$f" == "process_catalog.json" || "$f" == "structural_analogies.json" ]] && src="$QUERIES/process/$f"
  if [[ -f "$src" ]]; then
    cp "$src" "$PUBLIC_DATA/$f"
    echo "  copied $f → public/data only"
  fi
done

# Publish-safety M1 (dashboard_publish_safety_spec_2026_05_17): the
# contextualized-rater primer is the operator's PRIVATE memory index.
# It is deliberately NOT staged into the dashboard bundle. The
# Methodology tab describes the primer's role without reproducing it.
# Remove any stale copy a previous (unsafe) refresh may have left.
rm -f "$SRC_DATA/_taste_context_primer.md" "$PUBLIC_DATA/_taste_context_primer.md"

echo "done."
