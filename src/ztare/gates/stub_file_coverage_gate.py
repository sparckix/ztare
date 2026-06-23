"""G-STUB-FILE-COVERAGE — block downstream proofs depending on entire-file-open stubs (advisory v0.1).

Mechanizes the graph-scale finding that some receipt-tree files have 100% open
obligations (e.g., `ns_low_high_profile_lipschitz_composition` 14/14, `ns_clay_closure_bridge` 5/5).
A closure attempt that imports such a stub but doesn't address its obligations
is taking a structural shortcut.

Cross-scale: GP-219 proto-op A (Auxiliary Object Construction) at graph scale —
the stub file is an "engineered placeholder" whose declarations stand in for
unproven obligations. The gate enforces that downstream attempts either close
the stub's obligations or explicitly acknowledge dependency-on-placeholder.

# Status: ADVISORY v0.1 (2026-05-05)

Flip to promote-blocking with `enforce_block=True` after 3-5 closure-attempt observations.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def find_stub_files(graph_path: Path, receipt_node_id: str, threshold: float = 1.0) -> list[dict]:
    """Find files in receipt-tree where >= threshold fraction of decls are open_obligation."""
    if not graph_path.exists():
        return []
    g = json.loads(graph_path.read_text())
    nodes = g.get("@graph", [])
    files = [n for n in nodes if n.get("@type") == "ns_lean_file"]
    decls = [n for n in nodes if n.get("@type") == "ns_lean_decl"]
    fwd = {f["@id"]: set(f.get("imports", [])) for f in files}

    def reach(start):
        seen, stack = {start}, [start]
        while stack:
            n = stack.pop()
            for nb in fwd.get(n, []):
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        return seen

    if receipt_node_id not in fwd:
        return []
    receipt_tree = reach(receipt_node_id)

    file_open = defaultdict(int)
    file_total = defaultdict(int)
    for d in decls:
        if d.get("file") not in receipt_tree:
            continue
        if d.get("kind") not in ("theorem", "lemma", "def"):
            # Only count provable declarations
            pass
        file_total[d["file"]] += 1
        if d.get("status") == "open_obligation":
            file_open[d["file"]] += 1

    stubs = []
    for fid, total in file_total.items():
        if total == 0:
            continue
        ratio = file_open[fid] / total
        if ratio >= threshold and file_open[fid] >= 2:  # need at least 2 open to count
            file_node = next((f for f in files if f["@id"] == fid), None)
            if file_node:
                stubs.append({
                    "file_id": fid, "file_name": file_node["name"],
                    "n_open": file_open[fid], "n_total": total,
                    "ratio": ratio,
                })
    stubs.sort(key=lambda s: -s["n_open"])
    return stubs


def run_stub_file_coverage_gate(
    rubric_data: dict[str, Any] | None = None,
    artifact_graph_path: str | Path | None = None,
    receipt_node_id: str = "ns_file:ns_gp216_bridge_composition_receipt",
    *,
    threshold: float = 1.0,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Verify closure attempt acknowledges stub-file dependencies.

    Args:
        rubric_data: looks for `imported_files` (which files this attempt imports)
          and `acknowledged_stubs` (list of stub file names this attempt knows are stubs)
        threshold: open/total ratio to flag as stub (default 1.0 = entire-file-open)
        enforce_block: if True, return passed=False on violations.

    Returns dict with passed/violations/stub_files/etc.
    """
    rubric_data = rubric_data or {}
    imported = set(rubric_data.get("imported_files") or [])
    acknowledged = set(rubric_data.get("acknowledged_stubs") or [])

    if artifact_graph_path is None:
        artifact_graph_path = Path(__file__).resolve().parents[3] / "analytics" / "queries" / "ns_trackb_artifact_graph.json"
    artifact_graph_path = Path(artifact_graph_path)

    if not artifact_graph_path.exists():
        return {
            "passed": True, "blocking_active": enforce_block,
            "violations": [{"type": "graph_not_found", "severity": "advisory",
                            "reason": f"Artifact graph not found at {artifact_graph_path}; gate skipped."}],
            "advisory_warnings": ["graph not generated"],
            "stub_files": [], "summary": "graph not generated; gate skipped",
        }

    stubs = find_stub_files(artifact_graph_path, receipt_node_id, threshold)
    violations: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not stubs:
        return {
            "passed": True, "blocking_active": enforce_block,
            "violations": [], "advisory_warnings": [],
            "stub_files": [], "summary": "0 stub files in receipt-tree",
        }

    # Find imported stubs that aren't acknowledged
    imported_stub_names = {s["file_name"] for s in stubs if s["file_name"] in imported}
    unacknowledged = imported_stub_names - acknowledged

    if unacknowledged:
        top_stubs = ", ".join(
            f"{stub['file_name']}({stub['n_open']} open)"
            for stub in stubs[:3]
        )
        violations.append({
            "type": "imported_stub_not_acknowledged",
            "severity": "advisory" if not enforce_block else "blocking",
            "unacknowledged_stubs": sorted(unacknowledged),
            "stub_details": [s for s in stubs if s["file_name"] in unacknowledged],
            "reason": (
                f"Closure attempt imports {len(unacknowledged)} stub file(s) "
                f"(entire-file-open) without acknowledgment: {sorted(unacknowledged)}. "
                f"Add to rubric `acknowledged_stubs: [...]` with reason, OR provide "
                f"closing proofs for at least 1 of the stub's open obligations. "
                f"Top stubs: {top_stubs}."
            ),
        })
        warnings.append(f"{len(unacknowledged)} unacknowledged stub imports")

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    passed = (not blocking) if enforce_block else True

    summary_parts = [
        f"{len(stubs)} stub file(s) in receipt-tree",
        f"{len(imported_stub_names)} imported by attempt",
        f"{len(unacknowledged)} unacknowledged",
    ]
    if not enforce_block:
        summary_parts.append("ADVISORY mode")

    return {
        "passed": passed,
        "blocking_active": enforce_block,
        "violations": violations,
        "advisory_warnings": warnings,
        "stub_files": stubs,
        "imported_stubs": sorted(imported_stub_names),
        "unacknowledged_stubs": sorted(unacknowledged),
        "summary": "; ".join(summary_parts),
    }


def _self_test() -> None:
    import tempfile
    fake = {
        "@graph": [
            {"@id": "ns_file:ns_gp216_bridge_composition_receipt", "@type": "ns_lean_file",
             "imports": ["ns_file:ns_stub", "ns_file:ns_normal"], "name": "receipt"},
            {"@id": "ns_file:ns_stub", "@type": "ns_lean_file", "imports": [], "name": "ns_stub"},
            {"@id": "ns_file:ns_normal", "@type": "ns_lean_file", "imports": [], "name": "ns_normal"},
            # ns_stub: 3 of 3 open
            *[{"@id": f"ns_decl:stub.o{i}", "@type": "ns_lean_decl", "name": f"o{i}",
               "file": "ns_file:ns_stub", "status": "open_obligation", "kind": "theorem", "uses_decl": []}
              for i in range(3)],
            # ns_normal: 1 open / 2 closed
            {"@id": "ns_decl:normal.o", "@type": "ns_lean_decl", "name": "o", "file": "ns_file:ns_normal",
             "status": "open_obligation", "kind": "theorem", "uses_decl": []},
            *[{"@id": f"ns_decl:normal.c{i}", "@type": "ns_lean_decl", "name": f"c{i}",
               "file": "ns_file:ns_normal", "status": "closed_theorem", "kind": "theorem", "uses_decl": []}
              for i in range(2)],
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(fake, f)
        gp = f.name

    # T1: stub detected, no acknowledgment
    r = run_stub_file_coverage_gate(
        rubric_data={"imported_files": ["ns_stub"]}, artifact_graph_path=gp,
    )
    assert any(v["type"] == "imported_stub_not_acknowledged" for v in r["violations"])
    assert r["passed"] is True  # advisory

    # T2: stub acknowledged → no violation
    r = run_stub_file_coverage_gate(
        rubric_data={"imported_files": ["ns_stub"], "acknowledged_stubs": ["ns_stub"]},
        artifact_graph_path=gp,
    )
    assert not r["violations"]

    # T3: don't import stub → no violation
    r = run_stub_file_coverage_gate(
        rubric_data={"imported_files": ["ns_normal"]}, artifact_graph_path=gp,
    )
    assert not r["violations"]

    # T4: blocking mode with unacknowledged stub → passed=False
    r = run_stub_file_coverage_gate(
        rubric_data={"imported_files": ["ns_stub"]}, artifact_graph_path=gp, enforce_block=True,
    )
    assert r["passed"] is False

    import os; os.unlink(gp)
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    _self_test()
