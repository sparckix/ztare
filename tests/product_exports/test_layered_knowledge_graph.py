from __future__ import annotations

import sys
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

VALIDATOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "public"
    / "validators"
    / "validate_knowledge_graph.py"
)
VALIDATOR_SPEC = spec_from_file_location("validate_knowledge_graph", VALIDATOR_PATH)
assert VALIDATOR_SPEC is not None and VALIDATOR_SPEC.loader is not None
VALIDATOR_MODULE = module_from_spec(VALIDATOR_SPEC)
sys.modules["validate_knowledge_graph"] = VALIDATOR_MODULE
VALIDATOR_SPEC.loader.exec_module(VALIDATOR_MODULE)
PRIVATE_PATH = "research_areas/" + "private/seams/example.md"


def test_classify_layer_seam() -> None:
    assert classify_layer({"@id": "seam:GP-216e", "@type": "seam"}) == "artifact_graph"


def test_classify_layer_code() -> None:
    assert classify_layer({"@id": "func:orchestrator_contract_table.get_spec"}) == "code_graph"


def test_classify_layer_vocab() -> None:
    assert classify_layer({"@id": "op:core_02"}) == "vocabulary_graph"


def test_knowledge_graph_validator_rejects_private_paths() -> None:
    report = VALIDATOR_MODULE.validate(
        {
            "@graph": [
                {
                    "@id": "seam:GP-999",
                    "@type": "seam",
                    "path": PRIVATE_PATH,
                    "depends_on": [],
                    "instantiates_op": [],
                    "references_gate": [],
                }
            ]
        }
    )

    assert report.private_path_refs == [
        ("seam:GP-999", PRIVATE_PATH)
    ]
