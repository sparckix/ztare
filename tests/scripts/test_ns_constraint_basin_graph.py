import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts" / "public" / "projects" / "ns" / "archive" / "graph_stack" / "ns_constraint_basin_graph.py"
)


def _load_script():
    spec = importlib.util.spec_from_file_location("ns_constraint_basin_graph", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_theorem_signature_equalities_become_constraint_edges(tmp_path):
    mod = _load_script()
    lean_dir = tmp_path / "ZtareProofs"
    lean_dir.mkdir()
    (lean_dir / "ns_sample.lean").write_text(
        "theorem explicit_identity_bridge\n"
        "    (L S : Real) :\n"
        "    leraySelfTaxLimitPrice L = continuumGlobalSelfTaxTarget S := by\n"
        "  rfl\n",
        encoding="utf-8",
    )

    graph = mod.parse_lean_files(lean_dir, strip_plumbing=True)

    assert graph["summary"]["operator_counts"].get("eq") == 1
    edges = [
        edge for edge in graph["@graph"]
        if edge.get("@type") == "ns_inequality_edge"
    ]
    assert any(
        edge["src"] == "qty:leraySelfTaxLimitPrice"
        and edge["dst"] == "qty:continuumGlobalSelfTaxTarget"
        and edge["op"] == "eq"
        and edge["atomic"] is True
        for edge in edges
    )


def test_theorem_argument_types_do_not_become_quantity_edges(tmp_path):
    mod = _load_script()
    lean_dir = tmp_path / "ZtareProofs"
    lean_dir.mkdir()
    (lean_dir / "ns_sample.lean").write_text(
        "theorem typed_argument_pollution_guard\n"
        "    (B : FullLedgerBlock)\n"
        "    (S : LeraySelfTaxProfilePriceStream) :\n"
        "    S.payoffLimit ≤ B.gamma := by\n"
        "  exact le_rfl\n",
        encoding="utf-8",
    )

    graph = mod.parse_lean_files(lean_dir, strip_plumbing=True)

    quantity_nodes = {
        node["name"] for node in graph["@graph"]
        if node.get("@type") == "ns_lean_quantity"
    }
    assert "FullLedgerBlock" not in quantity_nodes
    assert "LeraySelfTaxProfilePriceStream" not in quantity_nodes
    assert "S.payoffLimit" in quantity_nodes
    assert "B.gamma" in quantity_nodes


def test_prop_valued_defs_do_not_become_quantity_edges(tmp_path):
    mod = _load_script()
    lean_dir = tmp_path / "ZtareProofs"
    lean_dir.mkdir()
    (lean_dir / "ns_sample.lean").write_text(
        "structure FullLedgerBlock where\n"
        "  gamma : Real\n\n"
        "def ThresholdDefectConvexity (B : FullLedgerBlock) : Prop :=\n"
        "  True\n\n"
        "theorem quantified_prop_pollution_guard :\n"
        "    ∀ B : FullLedgerBlock,\n"
        "      sharpTarget < B.gamma → ThresholdDefectConvexity B := by\n"
        "  intro B h\n"
        "  trivial\n",
        encoding="utf-8",
    )

    graph = mod.parse_lean_files(lean_dir, strip_plumbing=True)

    quantity_nodes = {
        node["name"] for node in graph["@graph"]
        if node.get("@type") == "ns_lean_quantity"
    }
    assert "FullLedgerBlock" not in quantity_nodes
    assert "ThresholdDefectConvexity" not in quantity_nodes
    assert "sharpTarget" in quantity_nodes
    assert "B.gamma" in quantity_nodes


def test_composite_edges_are_marked_non_atomic(tmp_path):
    mod = _load_script()
    lean_dir = tmp_path / "ZtareProofs"
    lean_dir.mkdir()
    (lean_dir / "ns_sample.lean").write_text(
        "theorem composite_edge_guard :\n"
        "    leftPrice ≤ rightPrice + reservePrice := by\n"
        "  exact le_rfl\n",
        encoding="utf-8",
    )

    graph = mod.parse_lean_files(lean_dir, strip_plumbing=True)

    edges = [
        edge for edge in graph["@graph"]
        if edge.get("@type") == "ns_inequality_edge"
    ]
    assert edges
    assert all(edge["atomic"] is False for edge in edges)
    assert {edge["rhs_quantity_count"] for edge in edges} == {2}


def test_negated_bound_theorems_do_not_emit_positive_edges(tmp_path):
    mod = _load_script()
    lean_dir = tmp_path / "ZtareProofs"
    lean_dir.mkdir()
    (lean_dir / "ns_sample.lean").write_text(
        "theorem negated_candidate_guard :\n"
        "    ¬ ∀ a b : Real, falseBoundLeft ≤ falseBoundRight := by\n"
        "  intro h\n"
        "  have hbad := h 1 0\n"
        "  norm_num at hbad\n",
        encoding="utf-8",
    )

    graph = mod.parse_lean_files(lean_dir, strip_plumbing=True)

    edges = [
        edge for edge in graph["@graph"]
        if edge.get("@type") == "ns_inequality_edge"
    ]
    assert edges == []
