"""Witness-transversal probe selector — ATTRIBUTE + AGENDA cells reused.

Given candidate-memory near-miss records or spec_nogood clauses, builds a
witness hypergraph (each refutation witness = a hyperedge over its distinguishing
atoms), finds near-minimal transversals (hitting-set over the hyperedges), and
ranks candidate probes by identification_bits (AGENDA cell).

Agency-preserving: returns ranked probe suggestions with their scores and the
transversal witness. Never auto-runs anything.

Registered as leaf workbench capability `select_worldmodel_probes`
(pure_diagnostic, stateless, zero-credit).
"""
from __future__ import annotations

import json
import re as _re
from pathlib import Path
from typing import Any, Hashable

from ztare.common.hitting_sets import minimal_hitting_sets
from ztare.common.information_yield_pricing import identification_bits, residual_information_yield
from ztare.common.leaf_workbench_contract import LeafWorkbenchCapability

_CELL_ATOM_RE = _re.compile(r"^cell_row_(.+)_col_(.+)$")


PROBE_SELECTION_CAPABILITY = LeafWorkbenchCapability(
    capability_id="select_worldmodel_probes",
    purpose=(
        "Build a witness hypergraph from candidate-memory near-miss records or "
        "spec_nogood clauses; compute near-minimal transversals (hitting-set over "
        "refutation witnesses); rank candidate probes by information yield "
        "(identification_bits over surviving candidate families). Returns ranked "
        "probe suggestions with scores and transversal witness — never auto-runs."
    ),
    authority="pure_diagnostic",
    secret_policy="public_only",
    input_contract=["source_ref", "probe_budget"],
    output_contract=["ranked_probes", "transversal_count", "committee_size"],
)


# ── core functions ──────────────────────────────────────────────────────────


def build_witness_hypergraph(records: list[dict]) -> dict[str, frozenset[str]]:
    """From near-miss records / nogood clauses: each refutation witness becomes
    a hyperedge over its distinguishing atoms (fields/features named in the witness).

    Returns {witness_id: frozenset[atom]} where atoms are the field names that
    the witness names as distinguishing (extracted from counterexample_trace,
    mismatch_classes, holdout_witness, witness_summary).
    """
    hyperedges: dict[str, frozenset[str]] = {}
    for i, rec in enumerate(records):
        atoms: set[str] = set()

        # Near-miss records (candidate_memory): extract from counterexample_trace
        trace = rec.get("counterexample_trace") or {}
        if isinstance(trace, dict):
            for key in ("mismatch_classes", "first_mismatch_signature"):
                val = trace.get(key)
                if isinstance(val, list):
                    atoms.update(str(v) for v in val if v)
                elif isinstance(val, dict):
                    atoms.update(str(k) for k in val if k)
            hw = trace.get("holdout_witness")
            if isinstance(hw, dict):
                for cell in hw.get("divergent_cells", []):
                    if isinstance(cell, dict):
                        atoms.add(f"cell_row_{cell.get('row')}_col_{cell.get('col')}")

        # Spec_nogood clauses: extract from witness_summary and provenance
        summary = rec.get("witness_summary") or ""
        if summary:
            # Pull field references from the summary string (e.g. "cell(row=1,col=2)")
            for m in _re.finditer(r"(\w+)=(\w+)", summary):
                atoms.add(f"{m.group(1)}_{m.group(2)}")

        prov = rec.get("provenance") or {}
        if isinstance(prov, dict):
            # claim_class or failure_family as atoms
            for key in ("failure_family", "claim_class", "source"):
                val = prov.get(key)
                if val:
                    atoms.add(str(val))

        # claim_class at top level (candidate_memory records)
        cc = rec.get("claim_class")
        if cc:
            atoms.add(str(cc))

        if atoms:
            wid = rec.get("signature") or rec.get("gated_sha256") or f"witness_{i}"
            hyperedges[str(wid)] = frozenset(atoms)

    return hyperedges


def minimal_probe_sets(
    hyperedges: dict[str, frozenset[str]],
    max_size: int = 3,
) -> list[frozenset[str]]:
    """Near-minimum transversals of the witness hypergraph via minimal_hitting_sets.

    A transversal hits every hyperedge (witness) — probing the atoms in the
    transversal would cover every known refutation witness. Uses the shared
    hitting-set core from ztare.common.hitting_sets (same algorithm as
    argument_kernel.minimal_cores, just a different predicate).
    """
    if not hyperedges:
        return []
    edges = list(hyperedges.values())
    # Universe = all atoms that appear in any hyperedge
    universe = sorted({atom for edge in edges for atom in edge})

    def is_transversal(cs: frozenset[str]) -> bool:
        return all(cs & edge for edge in edges)

    return minimal_hitting_sets(universe, is_transversal, max_size)


def _atom_in_record(atom: str, record: object) -> bool:
    """Return True if `atom` is 'mentioned' by this record.

    Cell atoms (cell_row_R_col_C) are synthetic names built by build_witness_hypergraph;
    they must be matched structurally against holdout divergent_cells, not by JSON string
    presence.  All other atoms use the original JSON mention-search.
    """
    m = _CELL_ATOM_RE.match(atom)
    if m and isinstance(record, dict):
        row_s, col_s = m.group(1), m.group(2)
        hw = (record.get("counterexample_trace") or {}).get("holdout_witness") or {}
        for cell in hw.get("divergent_cells", []):
            if isinstance(cell, dict) and str(cell.get("row")) == row_s and str(cell.get("col")) == col_s:
                return True
        return False
    record_str = json.dumps(record, default=str) if not isinstance(record, str) else record
    return atom in record_str


def rank_probes(
    transversals: list[frozenset[str]],
    committee: list[Any],
    *,
    max_probes: int = 10,
    baseline_probe_ids: frozenset[str] = frozenset(),
    baseline_ref: str = "arc_agi.no_declared_probe_baseline.v1",
) -> list[dict]:
    """Rank candidate probes by residual_information_yield (AGENDA one-door rule).

    Probes are priced through residual_information_yield instead of raw identification_bits:
    atoms already explained by the champion's visible-evidence replay (baseline) are
    subtracted before scoring.  Raw bits are kept in the receipt for observability.

    committee = the surviving candidate records / clause families.
    Binary mention-split predict: member mentions the atom → 'pos', else 'neg'.
    Cell atoms (cell_row_R_col_C) are matched structurally against holdout divergent_cells
    rather than by JSON string presence — they are synthetic names, not literal JSON fields.

    ponytail: binary partition approximation retained (cheapest correct proxy; description_units
    = 1.0 per atom, verification_cost = 0).
    """
    if not committee or not transversals:
        return []

    n = len(committee)
    atoms: dict[str, int] = {}
    for t in transversals:
        for atom in t:
            atoms[atom] = atoms.get(atom, 0) + 1

    if baseline_probe_ids and baseline_ref == "arc_agi.no_declared_probe_baseline.v1":
        raise ValueError("nonempty ARC probe baseline requires a receipt identity")

    def _predict(candidate_id: str, member: object) -> str:
        return "pos" if _atom_in_record(candidate_id, member) else "neg"

    results: list[dict] = []
    for atom, transversal_count in atoms.items():
        # Raw bits (for observability): uses same mention predicate
        pos = [m for m in committee if _atom_in_record(atom, m)]
        neg = [m for m in committee if not _atom_in_record(atom, m)]
        raw_cells: dict[Hashable, list] = {k: v for k, v in {"pos": pos, "neg": neg}.items() if v}
        raw_bits = identification_bits(raw_cells, n) if raw_cells else 0.0

        # Residual bits via the one pricing function (AGENDA one-door rule)
        coords = residual_information_yield(
            candidate_ids=[atom],
            baseline_ids=list(baseline_probe_ids & {atom}),
            objects=committee,
            predict=_predict,
            baseline_ref=baseline_ref,
            description_units=1.0,
        )
        residual_bits = coords.identification_bits

        results.append({
            "probe": atom,
            "raw_identification_bits": round(raw_bits, 4),
            "residual_identification_bits": round(residual_bits, 4),
            "baseline_ref": coords.baseline_ref,
            "in_transversals": transversal_count,
            "transversal_witness": sorted(
                next(t for t in transversals if atom in t)
            ),
        })

    results.sort(key=lambda r: (-r["residual_identification_bits"], -r["raw_identification_bits"],
                                -r["in_transversals"], r["probe"]))
    return results[:max_probes]


# ── workbench handler ───────────────────────────────────────────────────────


def _handle_select_worldmodel_probes(
    project_dir: "str | Path",
    req: dict[str, Any],
    _row: "dict[str, Any] | None",
    _contract: Any,
) -> dict[str, Any]:
    """Leaf workbench handler for select_worldmodel_probes."""
    project = Path(project_dir)
    input_refs = req.get("input_refs") if isinstance(req.get("input_refs"), dict) else {}
    source_ref = str(input_refs.get("source_ref") or "workspace/candidate_memory.json")
    probe_budget = int(input_refs.get("probe_budget") or 10)

    # Load records from source_ref
    source_path = project / source_ref
    records: list[dict] = []
    if source_path.exists():
        try:
            raw = json.loads(source_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                records = raw.get("records") or []
            elif isinstance(raw, list):
                records = raw
        except Exception:  # noqa: BLE001
            records = []

    # Also try spec_visible_nogoods.jsonl if candidate_memory is empty
    if not records:
        nogood_path = project / "workspace" / "spec_visible_nogoods.jsonl"
        if nogood_path.exists():
            for line in nogood_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    pass

    hyperedges = build_witness_hypergraph(records)
    transversals = minimal_probe_sets(hyperedges, max_size=3)
    ranked = rank_probes(transversals, records, max_probes=probe_budget)

    summary = json.dumps(
        {
            "ranked_probes": ranked,
            "transversal_count": len(transversals),
            "committee_size": len(records),
            "hyperedge_count": len(hyperedges),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return {
        "input_hashes": {
            "source_ref": source_ref,
            "probe_budget": probe_budget,
        },
        "output_summary": summary,
    }


def select_worldmodel_probes(project_dir: "str | Path", source_ref: str = "workspace/candidate_memory.json", probe_budget: int = 10) -> dict:
    """Convenience entry point for direct invocation (real-artifact proof)."""
    req = {"input_refs": {"source_ref": source_ref, "probe_budget": probe_budget}}
    result = _handle_select_worldmodel_probes(project_dir, req, None, None)
    return json.loads(result["output_summary"])
