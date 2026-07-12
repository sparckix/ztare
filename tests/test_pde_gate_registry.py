from ztare.pde.registry import (
    all_pde_gate_entries,
    entries_for_op,
    entry_by_gate_id,
)


def test_pde_gate_registry_surfaces_core_pde_gate_metadata() -> None:
    entries = all_pde_gate_entries()
    gate_ids = {entry["gate_id"] for entry in entries}

    assert "G-PDE-ANALYTIC-SUBSTANCE" in gate_ids
    assert "G-PDE-THEOREM-APPLICABILITY" in gate_ids
    assert "G-PDE-EQUALITY-PROVENANCE" in gate_ids
    assert "G-PDE-OPERATOR-ADMISSIBILITY" in gate_ids
    assert "G-PDE-RIGOROUS-NUMERICS" in gate_ids
    assert "G-PDE-HOSTILE-WITNESS" in gate_ids
    assert "G-SAME-CARRIER-PACKING" in gate_ids
    assert all(entry["workbench_flag"].startswith("--") for entry in entries)
    legacy_flag_key = "cli" + "_flag"
    assert all(legacy_flag_key not in entry for entry in entries)
    assert all(entry["runner"] for entry in entries)


def test_pde_gate_registry_routes_gp219_ops_to_relevant_gates() -> None:
    pec_l = entries_for_op("pec_l")
    ids = {entry["gate_id"] for entry in pec_l}

    assert "G-PDE-ANALYTIC-SUBSTANCE" in ids
    assert "G-PDE-EQUALITY-PROVENANCE" in ids
    assert "G-PDE-OPERATOR-ADMISSIBILITY" in ids
    assert "G-POSITIVE-VARIATION-BRIDGE" in ids
    assert "G-LINEAR-OBS-COERCIVITY" in ids

    theorem = entry_by_gate_id("G-PDE-THEOREM-APPLICABILITY")
    assert theorem is not None
    assert theorem["workbench_flag"] == "--theorem-applicability-json"
