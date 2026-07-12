from __future__ import annotations

import hashlib
import json

import pytest

from ztare.leanmill.adapters.magma_equational import build_single_premise_oracle
from ztare.leanmill.magma_law_universe import MagmaTerm, magma_laws_through_order
from ztare.leanmill.source_implication_oracle import SourceImplicationOracle
from ztare.leanmill.theory_ir import content_hash


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rle_file(tmp_path, codes: list[int]):
    encoded: list[int] = []
    for code in codes:
        if encoded and encoded[-2] == code:
            encoded[-1] += 1
        else:
            encoded.extend((code, 1))
    path = tmp_path / "relation.json"
    path.write_text(json.dumps({"rle_encoded_array": encoded}), encoding="utf-8")
    return path


def _mapping_receipt(mapping):
    core = {
        "schema": "test.source_mapping.v1",
        "mapping_sha256": content_hash(mapping),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def test_generic_source_oracle_distinguishes_single_premise_from_pack_synergy(tmp_path):
    count = 4
    codes = [6] * (count * count)
    for index in range(count):
        codes[index * count + index] = 7
    codes[0 * count + 2] = 7
    relation = _rle_file(tmp_path, codes)
    mapping = {f"formula:{index}": index + 1 for index in range(count)}
    oracle = SourceImplicationOracle.from_rle_file(
        mapping,
        relation_path=relation,
        relation_sha256=_sha256(relation),
        node_count=count,
        status_names=tuple(f"status_{index}" for index in range(9)),
        proved_true_codes=(3, 7),
        proved_false_codes=(2, 6),
        source_ref="test:source",
        mapping_receipt=_mapping_receipt(mapping),
    )

    refuted = oracle.audit(("formula:0", "formula:1"), "formula:2")
    assert refuted["status"] == "refuted_by_known_single_premise"
    assert [row["proved_implies"] for row in refuted["premise_checks"]] == [True, False]

    certified = oracle.audit(("formula:1", "formula:2"), "formula:3")
    assert certified["status"] == "certified_single_premise_nonimplication"
    assert all(row["proved_does_not_imply"] for row in certified["premise_checks"])


def _infix(term: MagmaTerm) -> str:
    if term.is_variable:
        assert term.variable is not None
        return chr(ord("x") + term.variable)
    assert term.left is not None and term.right is not None
    return f"({_infix(term.left)} ◇ {_infix(term.right)})"


def test_magma_adapter_materializes_external_mapping_capability(tmp_path):
    laws = magma_laws_through_order(1)
    catalog = tmp_path / "equations.txt"
    catalog.write_text(
        "\n".join(f"{_infix(law.left)} = {_infix(law.right)}" for law in laws)
        + "\n",
        encoding="utf-8",
    )
    count = len(laws)
    codes = [6] * (count * count)
    for index in range(count):
        codes[index * count + index] = 7
    relation = _rle_file(tmp_path, codes)
    oracle = build_single_premise_oracle(
        adapter_config={"max_total_operation_order": 1},
        oracle_config={
            "source_ref": "test:catalog",
            "node_catalog_path": str(catalog),
            "node_catalog_sha256": _sha256(catalog),
            "relation_path": str(relation),
            "relation_sha256": _sha256(relation),
            "node_count": count,
            "status_names": [f"status_{index}" for index in range(9)],
            "proved_true_codes": [3, 7],
            "proved_false_codes": [2, 6],
        },
    )
    assert len(oracle.formula_to_source_node) == count
    result = oracle.audit((laws[0].formula_id,), laws[1].formula_id)
    assert result["status"] == "certified_single_premise_nonimplication"


def test_source_oracle_fails_closed_on_relation_drift(tmp_path):
    relation = _rle_file(tmp_path, [6])
    mapping = {"formula:0": 1}
    with pytest.raises(ValueError, match="relation digest mismatch"):
        SourceImplicationOracle.from_rle_file(
            mapping,
            relation_path=relation,
            relation_sha256="0" * 64,
            node_count=1,
            status_names=tuple(f"status_{index}" for index in range(9)),
            proved_true_codes=(3, 7),
            proved_false_codes=(2, 6),
            source_ref="test:source",
            mapping_receipt=_mapping_receipt(mapping),
        )
