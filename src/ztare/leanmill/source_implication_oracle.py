"""Generic source-bound single-premise implication evidence."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ztare.leanmill.theory_ir import content_hash


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class SourceImplicationOracle:
    """Read an exact directed implication relation over source node numbers."""

    formula_to_source_node: Mapping[str, int]
    rle_encoded_relation: tuple[int, ...]
    node_count: int
    status_names: tuple[str, ...]
    proved_true_codes: frozenset[int]
    proved_false_codes: frozenset[int]
    source_ref: str
    relation_sha256: str
    mapping_receipt: Mapping[str, Any]

    @classmethod
    def from_rle_file(
        cls,
        formula_to_source_node: Mapping[str, int],
        *,
        relation_path: str | Path,
        relation_sha256: str,
        node_count: int,
        status_names: Sequence[str],
        proved_true_codes: Sequence[int],
        proved_false_codes: Sequence[int],
        source_ref: str,
        mapping_receipt: Mapping[str, Any],
    ) -> "SourceImplicationOracle":
        if sha256_file(relation_path) != relation_sha256:
            raise ValueError("source implication relation digest mismatch")
        payload = json.loads(Path(relation_path).read_text(encoding="utf-8"))
        encoded = payload.get("rle_encoded_array") if isinstance(payload, Mapping) else None
        if (
            not isinstance(encoded, list)
            or len(encoded) % 2
            or not all(type(row) is int for row in encoded)
        ):
            raise ValueError("source implication relation has invalid RLE bytes")
        names = tuple(str(row) for row in status_names)
        true_codes = frozenset(int(row) for row in proved_true_codes)
        false_codes = frozenset(int(row) for row in proved_false_codes)
        if (
            type(node_count) is not int
            or node_count < 1
            or not names
            or true_codes & false_codes
            or not true_codes | false_codes
            or any(code not in range(len(names)) for code in true_codes | false_codes)
        ):
            raise ValueError("source implication relation semantics are invalid")
        total = sum(encoded[index] for index in range(1, len(encoded), 2))
        if total != node_count * node_count:
            raise ValueError("source implication relation has the wrong decoded size")
        receipt = dict(mapping_receipt)
        receipt_core = {
            key: value for key, value in receipt.items() if key != "receipt_sha256"
        }
        if receipt.get("receipt_sha256") != content_hash(receipt_core):
            raise ValueError("source formula mapping receipt digest mismatch")
        mapping = {str(key): int(value) for key, value in formula_to_source_node.items()}
        if any(node < 1 or node > node_count for node in mapping.values()):
            raise ValueError("source formula mapping contains an invalid node number")
        return cls(
            formula_to_source_node=mapping,
            rle_encoded_relation=tuple(encoded),
            node_count=node_count,
            status_names=names,
            proved_true_codes=true_codes,
            proved_false_codes=false_codes,
            source_ref=str(source_ref),
            relation_sha256=relation_sha256,
            mapping_receipt=receipt,
        )

    def _lookup_codes(self, pairs: Sequence[tuple[int, int]]) -> dict[tuple[int, int], int]:
        indices = {
            (left - 1) * self.node_count + (right - 1): (left, right)
            for left, right in pairs
        }
        if any(
            left < 1 or right < 1 or left > self.node_count or right > self.node_count
            for left, right in pairs
        ):
            raise ValueError("source node number outside implication relation")
        wanted = sorted(indices)
        found: dict[tuple[int, int], int] = {}
        cursor = 0
        wanted_index = 0
        for offset in range(0, len(self.rle_encoded_relation), 2):
            value = self.rle_encoded_relation[offset]
            count = self.rle_encoded_relation[offset + 1]
            if value not in range(len(self.status_names)) or count < 1:
                raise ValueError("source implication relation contains an invalid RLE run")
            end = cursor + count
            while wanted_index < len(wanted) and wanted[wanted_index] < end:
                index = wanted[wanted_index]
                if index >= cursor:
                    found[indices[index]] = value
                wanted_index += 1
            cursor = end
        if len(found) != len(indices):
            raise ValueError("source implication lookup did not resolve every pair")
        return found

    def audit(
        self,
        premise_formula_ids: Sequence[str],
        target_formula_id: str,
    ) -> dict[str, Any]:
        premises = tuple(str(row) for row in premise_formula_ids)
        target = str(target_formula_id)
        missing = [
            row for row in (*premises, target) if row not in self.formula_to_source_node
        ]
        checks: list[dict[str, Any]] = []
        target_node: int | None = None
        if not missing:
            target_node = self.formula_to_source_node[target]
            pairs = [
                (self.formula_to_source_node[premise], target_node)
                for premise in premises
            ]
            codes = self._lookup_codes(pairs)
            for premise, pair in zip(premises, pairs, strict=True):
                code = codes[pair]
                checks.append(
                    {
                        "premise_formula_id": premise,
                        "premise_source_node": pair[0],
                        "target_source_node": pair[1],
                        "source_status_code": code,
                        "source_status": self.status_names[code],
                        "proved_implies": code in self.proved_true_codes,
                        "proved_does_not_imply": code in self.proved_false_codes,
                    }
                )
        if missing:
            status = "unavailable_formula_mapping"
        elif any(row["proved_implies"] for row in checks):
            status = "refuted_by_known_single_premise"
        elif checks and all(row["proved_does_not_imply"] for row in checks):
            status = "certified_single_premise_nonimplication"
        else:
            status = "unresolved_source_relation"
        core = {
            "schema": "leanmill.source_single_premise_ablation.v1",
            "status": status,
            "premise_formula_ids": list(premises),
            "target_formula_id": target,
            "target_source_node": target_node,
            "missing_formula_ids": missing,
            "premise_checks": checks,
            "source_ref": self.source_ref,
            "relation_sha256": self.relation_sha256,
            "mapping_receipt_sha256": self.mapping_receipt["receipt_sha256"],
        }
        return {**core, "receipt_sha256": content_hash(core)}


__all__ = ["SourceImplicationOracle", "sha256_file"]
