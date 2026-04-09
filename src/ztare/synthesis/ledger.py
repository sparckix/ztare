"""
ledger.py — Prediction Track Record

Scans all projects/*/champion_probability_dag.json (falling back to latest) and appends new predictions
to track_record.csv. Run this after every engine run.

Once a prediction resolves, open track_record.csv and fill in:
  - actual_outcome: "CORRECT", "INCORRECT", or "PARTIAL"
  - notes: what actually happened

Usage:
    python -m src.ztare.synthesis.ledger              # scan and append new predictions
    python -m src.ztare.synthesis.ledger --report     # print calibration summary
"""

import os
import json
import csv
import argparse
from datetime import datetime
from src.ztare.common.paths import PROJECTS_DIR as PROJECTS_PATH, REPO_ROOT

LEDGER_PATH = str(REPO_ROOT / "track_record.csv")
PROJECTS_DIR = str(PROJECTS_PATH)

FIELDNAMES = [
    "date_logged",
    "project",
    "thesis_version",   # history filename stem — ties prediction to exact thesis that produced it
    "node_id",
    "prediction",
    "engine_score",
    "rubric",
    "confidence",
    "watch_signal",
    "actual_outcome",   # fill in: CORRECT / INCORRECT / PARTIAL
    "date_resolved",    # fill in when known
    "notes",
]


def load_existing_ledger():
    """Returns set of (project, thesis_version, node_id) already in the ledger."""
    existing = set()
    if not os.path.exists(LEDGER_PATH):
        return existing
    with open(LEDGER_PATH, newline="") as f:
        for row in csv.DictReader(f):
            existing.add((row["project"], row.get("thesis_version", ""), row["node_id"]))
    return existing


def load_best_run_meta(project):
    """
    Returns (best_score, rubric, run_id) for the highest-scoring run in history.
    Reads sidecar _meta.json files — reliable across rubric versions.
    Falls back to parsing filenames for legacy entries.
    """
    history_dir = os.path.join(PROJECTS_DIR, project, "history")
    best = {"score": "unknown", "rubric": "unknown", "run_id": "unknown"}
    if not os.path.exists(history_dir):
        return best

    best_score = -1
    for fname in os.listdir(history_dir):
        if fname.endswith("_meta.json"):
            try:
                with open(os.path.join(history_dir, fname)) as f:
                    meta = json.load(f)
                if meta.get("score", -1) > best_score:
                    best_score = meta["score"]
                    best = {
                        "score": meta["score"],
                        "rubric": meta.get("rubric", "unknown"),
                        "run_id": meta.get("run_id", "unknown"),
                    }
            except (json.JSONDecodeError, KeyError):
                pass

    # Legacy fallback: parse old vN_score_X.md filenames
    if best_score == -1:
        for fname in os.listdir(history_dir):
            if "_score_" in fname and fname.endswith(".md"):
                try:
                    score = int(fname.split("_score_")[1].split("_")[0].replace(".md", ""))
                    if score > best_score:
                        best_score = score
                        best["score"] = score
                except ValueError:
                    pass

    return best


def find_best_dag(project):
    """
    Returns (dag, meta) for the highest-scoring run that has a saved DAG.
    Falls back to champion_probability_dag.json, then latest_probability_dag.json if no history DAGs exist yet.
    """
    history_dir = os.path.join(PROJECTS_DIR, project, "history")
    best_score = -1
    best_dag = None
    best_meta = {}

    if os.path.exists(history_dir):
        for fname in os.listdir(history_dir):
            if not fname.endswith("_dag.json"):
                continue
            dag_path = os.path.join(history_dir, fname)
            meta_path = dag_path.replace("_dag.json", "_meta.json")

            # New format: read score from sidecar meta file
            if os.path.exists(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    score = meta.get("score", -1)
                except (json.JSONDecodeError, KeyError):
                    continue
            else:
                # Old format: parse score from filename e.g. v1_score_35_dag.json
                try:
                    score = int(fname.split("_score_")[1].split("_")[0].replace("_dag.json", "").replace(".json", ""))
                    meta = {"score": score, "rubric": "unknown"}
                except (IndexError, ValueError):
                    continue

            if score > best_score:
                try:
                    with open(dag_path) as f:
                        dag = json.load(f)
                    best_score = score
                    best_dag = dag
                    best_meta = meta
                    # Stem = filename without _dag.json
                    best_meta["thesis_stem"] = fname.replace("_dag.json", "")
                except json.JSONDecodeError:
                    pass

    if best_dag is not None:
        return best_dag, best_meta

    # Fallback: current champion / latest DAG (no thesis stem available)
    fallback_candidates = [
        os.path.join(PROJECTS_DIR, project, "champion_probability_dag.json"),
        os.path.join(PROJECTS_DIR, project, "latest_probability_dag.json"),
    ]
    for fallback in fallback_candidates:
        if os.path.exists(fallback):
            with open(fallback) as f:
                best_dag = json.load(f)
            run_meta = load_best_run_meta(project)
            return best_dag, {"score": run_meta["score"], "rubric": run_meta["rubric"], "thesis_stem": "legacy"}

    return None, {}


def scan_and_append():
    existing = load_existing_ledger()
    new_rows = []

    for project in sorted(os.listdir(PROJECTS_DIR)):
        dag, run_meta = find_best_dag(project)
        if dag is None:
            continue

        engine_score = run_meta.get("score", "unknown")
        rubric = run_meta.get("rubric", "unknown")
        thesis_version = run_meta.get("thesis_stem", "legacy")
        outcome_label = dag.get("outcome", {}).get("label", "")
        outcome_prob = dag.get("outcome", {}).get("probability", None)

        # Log the outcome node itself
        outcome_key = (project, thesis_version, "OUTCOME")
        if outcome_key not in existing:
            new_rows.append({
                "date_logged": datetime.now().strftime("%Y-%m-%d"),
                "project": project,
                "thesis_version": thesis_version,
                "node_id": "OUTCOME",
                "prediction": outcome_label,
                "engine_score": engine_score,
                "rubric": rubric,
                "confidence": f"{outcome_prob:.3f}" if outcome_prob is not None else "unknown",
                "watch_signal": "See node watch_signals below",
                "actual_outcome": "",
                "date_resolved": "",
                "notes": "",
            })

        # Log each node as an independently trackable prediction
        for node in dag.get("nodes", []):
            node_id = node.get("id", "")
            key = (project, thesis_version, node_id)
            if key in existing:
                continue

            new_rows.append({
                "date_logged": datetime.now().strftime("%Y-%m-%d"),
                "project": project,
                "thesis_version": thesis_version,
                "node_id": node_id,
                "prediction": node.get("label", ""),
                "engine_score": engine_score,
                "rubric": rubric,
                "confidence": f"{node.get('probability', 0):.3f}",
                "watch_signal": node.get("watch_signal", ""),
                "actual_outcome": "",
                "date_resolved": "",
                "notes": "",
            })

    if not new_rows:
        print("✅ Ledger is up to date. No new predictions found.")
        return

    write_header = not os.path.exists(LEDGER_PATH)
    with open(LEDGER_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"📋 Added {len(new_rows)} new predictions to {LEDGER_PATH}")
    for r in new_rows:
        print(f"   [{r['project']}] {r['node_id']} — confidence {r['confidence']}")


def print_report():
    if not os.path.exists(LEDGER_PATH):
        print("❌ No ledger found. Run: python -m src.ztare.synthesis.ledger")
        return

    rows = []
    with open(LEDGER_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    resolved = [r for r in rows if r["actual_outcome"] in ("CORRECT", "INCORRECT", "PARTIAL")]
    open_preds = [r for r in rows if not r["actual_outcome"]]

    print(f"\n{'='*55}")
    print(f"  ADVERSARIAL ENGINE — PREDICTION TRACK RECORD")
    print(f"{'='*55}")
    print(f"  Total predictions logged : {len(rows)}")
    print(f"  Resolved                 : {len(resolved)}")
    print(f"  Open (awaiting outcome)  : {len(open_preds)}")

    # Group everything by project — calibration across projects is meaningless
    projects = sorted(set(r["project"] for r in rows))

    for project in projects:
        proj_rows = [r for r in rows if r["project"] == project]
        proj_resolved = [r for r in proj_rows if r["actual_outcome"] in ("CORRECT", "INCORRECT", "PARTIAL")]
        proj_open = [r for r in proj_rows if not r["actual_outcome"]]
        rubric = proj_rows[0].get("rubric", "unknown") if proj_rows else "unknown"

        thesis_versions = sorted(set(r.get("thesis_version", "legacy") for r in proj_rows))
        print(f"\n  PROJECT: {project.upper()}  (rubric: {rubric})")
        print(f"  Thesis versions: {', '.join(thesis_versions)}")
        print(f"  {'─'*50}")
        print(f"  Total: {len(proj_rows)} | Resolved: {len(proj_resolved)} | Open: {len(proj_open)}")

        if proj_resolved:
            correct = sum(1 for r in proj_resolved if r["actual_outcome"] == "CORRECT")
            partial = sum(1 for r in proj_resolved if r["actual_outcome"] == "PARTIAL")
            incorrect = sum(1 for r in proj_resolved if r["actual_outcome"] == "INCORRECT")
            accuracy = (correct + 0.5 * partial) / len(proj_resolved) * 100
            print(f"  Accuracy: {accuracy:.1f}%  (✓{correct} ~{partial} ✗{incorrect})")

            score_bands = {}
            for r in proj_resolved:
                try:
                    score = int(r["engine_score"])
                    band = f"{(score // 10) * 10}-{(score // 10) * 10 + 9}"
                except (ValueError, TypeError):
                    band = "unknown"
                score_bands.setdefault(band, {"correct": 0, "partial": 0, "incorrect": 0, "total": 0})
                score_bands[band]["total"] += 1
                if r["actual_outcome"] == "CORRECT":
                    score_bands[band]["correct"] += 1
                elif r["actual_outcome"] == "PARTIAL":
                    score_bands[band]["partial"] += 1
                else:
                    score_bands[band]["incorrect"] += 1

            print(f"  By score band:")
            for band in sorted(score_bands.keys()):
                d = score_bands[band]
                band_acc = (d["correct"] + 0.5 * d["partial"]) / d["total"] * 100
                print(f"    Score {band}: {band_acc:.0f}% ({d['total']} resolved)")

        if proj_open:
            print(f"  Open predictions:")
            for r in proj_open:
                print(f"    [{r['node_id']}] conf={r['confidence']} | {r['prediction'][:60]}")
                if r.get("watch_signal") and r["watch_signal"] not in ("See node watch_signals below", ""):
                    print(f"      Watch: {r['watch_signal'][:75]}")

    print(f"{'='*55}\n")
    print(f"  To resolve: open {LEDGER_PATH} and fill in actual_outcome + date_resolved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="Print calibration summary")
    args = parser.parse_args()

    if args.report:
        print_report()
    else:
        scan_and_append()
