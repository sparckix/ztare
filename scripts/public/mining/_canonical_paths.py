"""Single source of truth for reflexive-mining canonical paths.

WHY THIS EXISTS: the scripts-reorg stranded ~half a dozen scripts at
pre-reorg `analytics/trajectory_archive*.jsonl` paths (incident
2026-05-16; see docs/concepts/reflexive_mining_methodology.md §3/§4).
The root cause was every script hardcoding its own ROOT/"analytics"/...
constants. The right fix is NOT to merge the scripts (modular +
testable is correct) — it is to collapse the duplicated *path
knowledge* here so the defect surface is one file, not thirteen.

New / migrated mining scripts should `from _canonical_paths import ...`
rather than re-deriving these. The orchestrator (run_reflexive_mine.py)
owns ordering; this module owns locations.
"""
from pathlib import Path

REPO = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()

# Trajectory archives (Stage 1 + enrich)
LEDGERS_TRAJECTORY = REPO / "analytics" / "public" / "ledgers" / "trajectory"
TRAJECTORY_ARCHIVE = LEDGERS_TRAJECTORY / "trajectory_archive.jsonl"
TRAJECTORY_ARCHIVE_ENRICHED = LEDGERS_TRAJECTORY / "trajectory_archive_enriched.jsonl"

# Query + taste surfaces
QUERIES = REPO / "analytics" / "public" / "queries"
TASTE = QUERIES / "taste"
REFERENCE_GRAPH = QUERIES / "reference_graph.json"
REFERENCE_GRAPH_GRAPHS = QUERIES / "graphs" / "reference_graph.json"  # G6 reader copy

# Reflexive index + bifurcation (orchestrator Phase 1)
REFLEXIVE_DIR = REPO / "analytics" / "public" / "ledgers" / "reflexive"
ARTIFACT_INDEX = REFLEXIVE_DIR / "artifact_index.jsonl"

CANONICAL_RATER = "cold_subagent_contextualized"
