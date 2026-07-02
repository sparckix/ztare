"""Research-landscape graph — a read-only PROJECTION over the kernel artifacts a project already
produces, assembled into one typed node/edge graph (the "topographical map" of the problem).

No new kernel computation: this only reads existing files and expresses the relationships that are
already implicit in their fields as explicit edges. Sources (exact files + fields) per node/edge type
are documented inline. Exposed via `ztare autoresearch research-graph --project <p> --json` so the
workbench consumes it through the CLI, never by reading kernel files directly.

Node types: thesis · claim (DAG sub-claim) · candidate (claim to test) · evidence (source) · tension
(contradiction) · gap (epistemic void) · constraint · branch (discriminator) · falsifier (inverter
test) · rejected (non-claim).
Edge relations: SUPPORTS · DERIVES · CHALLENGES · CONTRADICTS · CONSTRAINS · TESTS · FALSIFIES · RULED_OUT.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ztare.common import graph_algorithms

SCHEMA = "ztare-research-graph-v1"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                out.append(row)
    except Exception:
        return out
    return out


def _short(text: str, n: int = 90) -> str:
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


class _Graph:
    """Accumulator with node de-dup by id and a cap per node-type so the graph stays legible."""

    def __init__(self, cap: int = 9) -> None:
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self.cap = cap
        self._type_counts: dict[str, int] = {}
        self.truncated: dict[str, int] = {}

    def add(self, node_id: str, ntype: str, label: str, *, detail: str = "", weight: float | None = None, status: str = "") -> bool:
        node_id = str(node_id or "").strip()
        if not node_id:
            return False
        if node_id in self.nodes:
            return True
        if ntype != "thesis" and self._type_counts.get(ntype, 0) >= self.cap:
            self.truncated[ntype] = self.truncated.get(ntype, 0) + 1
            return False
        self.nodes[node_id] = {
            "id": node_id, "type": ntype, "label": _short(label, 90),
            "detail": str(detail or label or "").strip(), "weight": weight, "status": status,
        }
        self._type_counts[ntype] = self._type_counts.get(ntype, 0) + 1
        return True

    def link(self, src: str, dst: str, relation: str) -> None:
        if src in self.nodes and dst in self.nodes and src != dst:
            self.edges.append({"from": src, "to": dst, "relation": relation})


def build_research_graph(project: str, repo_root: Path) -> dict[str, Any]:
    proot = repo_root / "projects" / project
    g = _Graph()

    # --- The thesis / conclusion at the centre (DAG outcome → else bounded claim from the packet). ---
    eval_data = _read_json(proot / "latest_eval_results.json") or _read_json(proot / "workspace" / "latest_eval_results.json") or {}
    dag = eval_data.get("probability_dag") if isinstance(eval_data.get("probability_dag"), dict) else _read_json(proot / "latest_probability_dag.json") or {}
    thesis_label = ""
    if isinstance(dag, dict) and isinstance(dag.get("outcome"), dict):
        thesis_label = str(dag["outcome"].get("label") or "").strip()
    if not thesis_label:
        packet = _read_json(next(iter(proot.glob("*_packet.json")), proot / "missing")) or {}
        thesis_label = str(packet.get("bounded_claim") or packet.get("thesis") or "This project's thesis").strip()
    g.add("thesis", "thesis", thesis_label or "This project's thesis",
          detail=thesis_label, weight=(dag.get("outcome", {}) or {}).get("probability"))

    # --- DAG sub-claims → the thesis (the reasoning spine). ---
    for n in (dag.get("nodes") if isinstance(dag.get("nodes"), list) else []):
        if not isinstance(n, dict):
            continue
        nid = f"claim:{n.get('id')}"
        watch = str(n.get("watch_signal") or "").strip()
        det = str(n.get("label") or "") + (f"\nWhat would settle it: {watch}" if watch else "")
        if g.add(nid, "claim", n.get("label") or n.get("id") or "", detail=det, weight=n.get("probability")):
            g.link(nid, "thesis", "DERIVES")

    # --- The compiled evidence packet: sources, candidate claims, contradictions, voids. ---
    packet = _read_json(proot / "compiled_evidence_packet.json") or {}
    src_label: dict[str, str] = {}
    for p in (packet.get("provenance") if isinstance(packet.get("provenance"), list) else []):
        if isinstance(p, dict) and p.get("source_id"):
            sid = f"src:{p['source_id']}"
            label = str(p.get("summary") or p.get("path") or p["source_id"]).strip()
            src_label[str(p["source_id"])] = sid
            g.add(sid, "evidence", label, detail=f"{label}\n({p.get('source_type') or p.get('kind') or 'source'})")
    for gt in (packet.get("immutable_ground_truth") if isinstance(packet.get("immutable_ground_truth"), list) else []):
        if isinstance(gt, dict) and gt.get("statement"):
            fid = f"fact:{abs(hash(gt['statement'])) % 10_000_000}"
            if g.add(fid, "evidence", gt["statement"], detail=str(gt["statement"]), status=str(gt.get("strength") or "")):
                for s in (gt.get("source_ids") or []):
                    if str(s) in src_label:
                        g.link(src_label[str(s)], fid, "SUPPORTS")
                g.link(fid, "thesis", "SUPPORTS")
    for c in (packet.get("candidate_claims_to_test") if isinstance(packet.get("candidate_claims_to_test"), list) else []):
        if isinstance(c, dict) and c.get("claim"):
            cid = f"cand:{abs(hash(c['claim'])) % 10_000_000}"
            det = str(c["claim"]) + (f"\nWhy testable: {c.get('why_testable')}" if c.get("why_testable") else "")
            if g.add(cid, "candidate", c["claim"], detail=det, status=str(c.get("priority") or "")):
                for s in (c.get("source_ids") or []):
                    if str(s) in src_label:
                        g.link(src_label[str(s)], cid, "SUPPORTS")
                g.link(cid, "thesis", "TESTS")
    for ct in (packet.get("identified_contradictions") if isinstance(packet.get("identified_contradictions"), list) else []):
        if isinstance(ct, dict):
            label = str(ct.get("topic") or ct.get("why_it_matters") or "Contradiction").strip()
            tid = f"tension:{abs(hash(label)) % 10_000_000}"
            det = label + (f"\n{ct.get('claim_a')} ⟷ {ct.get('claim_b')}" if ct.get("claim_a") else "")
            if g.add(tid, "tension", label, detail=det):
                g.link(tid, "thesis", "CHALLENGES")
    for v in (packet.get("epistemic_voids") if isinstance(packet.get("epistemic_voids"), list) else []):
        if isinstance(v, dict) and (v.get("unknown") or v.get("why_it_matters")):
            label = str(v.get("unknown") or v.get("why_it_matters")).strip()
            vid = f"gap:{abs(hash(label)) % 10_000_000}"
            if g.add(vid, "gap", label, detail=str(v.get("why_it_matters") or label), status=str(v.get("blocking") or "")):
                g.link(vid, "thesis", "CHALLENGES")

    # --- Derived constraints (established rules) → CONSTRAIN the thesis. ---
    dc = _read_json(proot / "workspace" / "derived_constraints.json") or {}
    for key, status in (("confirmed_constraints", "confirmed"), ("provisional_constraints", "provisional")):
        for row in (dc.get(key) if isinstance(dc.get(key), list) else []):
            text = row.get("constraint") if isinstance(row, dict) else str(row)
            if text:
                kid = f"constraint:{abs(hash(text)) % 10_000_000}"
                if g.add(kid, "constraint", text, detail=str(text), status=status):
                    g.link(kid, "thesis", "CONSTRAINS")

    # --- Branches to test (discriminators) → TEST the claim under pressure. ---
    for d in _read_jsonl(proot / "workspace" / "next_discriminator_queue.jsonl"):
        test = str(d.get("cheapest_discriminator") or d.get("discriminator") or "").strip()
        if test:
            bid = f"branch:{abs(hash(test)) % 10_000_000}"
            det = test + (f"\nKill condition: {d.get('kill_condition')}" if d.get("kill_condition") else "")
            if g.add(bid, "branch", test, detail=det, status=str(d.get("severity_label") or d.get("priority") or "")):
                g.link(bid, "thesis", "TESTS")

    # --- Inverter falsification tests → FALSIFY the thesis. ---
    inv = _read_json(proot / "workspace" / "inverter_review.json") or {}
    for t in (inv.get("tests") if isinstance(inv.get("tests"), list) else []):
        if isinstance(t, dict):
            label = str(t.get("munger_inversion") or t.get("popper_test") or "").strip()
            if label:
                fid = f"falsifier:{abs(hash(label)) % 10_000_000}"
                det = label + (f"\nKills it if: {t.get('fail_criterion')}" if t.get("fail_criterion") else "")
                if g.add(fid, "falsifier", label, detail=det):
                    g.link(fid, "thesis", "FALSIFIES")

    # --- Rejected alternatives (non-claims) → RULED_OUT by the thesis. ---
    for nc in (eval_data.get("non_claims") if isinstance(eval_data.get("non_claims"), list) else []):
        text = str(nc).strip()
        if text:
            rid = f"rejected:{abs(hash(text)) % 10_000_000}"
            if g.add(rid, "rejected", text, detail=text):
                g.link("thesis", rid, "RULED_OUT")

    counts: dict[str, int] = {}
    for n in g.nodes.values():
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    carrier = {"graph_kind": "source_claim_graph", "nodes": list(g.nodes.values()), "edges": g.edges}
    return {
        "ok": True, "schema": SCHEMA, "project": project,
        "nodes": carrier["nodes"], "edges": carrier["edges"],
        "type_counts": counts, "truncated": g.truncated, "graph_kind": carrier["graph_kind"],
        # Structural insight the eye can't get from a node cloud — graph-algorithmic, not LLM, computed
        # by the shared `graph_algorithms` suite over this source_claim_graph carrier (CLI is master).
        "insights": graph_algorithms.analyze(carrier),
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare autoresearch research-graph")
    parser.add_argument("--project", required=True)
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = build_research_graph(args.project, args.repo or _repo_root())
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
