from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "public"
    / "analytics_shared"
    / "export_layered_knowledge_graph.py"
)
SPEC = spec_from_file_location("export_layered_knowledge_graph", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
classify_layer = MODULE.classify_layer


def test_classify_layer_seam() -> None:
    assert classify_layer({"@id": "seam:GP-216e", "@type": "seam"}) == "artifact_graph"


def test_classify_layer_code() -> None:
    assert classify_layer({"@id": "func:orchestrator_contract_table.get_spec"}) == "code_graph"


def test_classify_layer_vocab() -> None:
    assert classify_layer({"@id": "op:core_07"}) == "vocabulary_graph"
