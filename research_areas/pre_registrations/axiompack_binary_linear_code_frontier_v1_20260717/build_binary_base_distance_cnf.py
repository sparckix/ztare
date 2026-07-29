#!/usr/bin/env python3
"""Generate CNFs for the frozen [50,20,13] base of the parity extension."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from build_binary_distance_cnf import CNF, encode_at_most


ROOT = Path(__file__).resolve().parent
ROWS = tuple(
    int(value, 16)
    for value in (
        "24883bee00001",
        "091077dd00002",
        "1220ebbb00004",
        "2441d37700008",
        "0893a2ef00010",
        "112741df00020",
        "224e83be00040",
        "049d077d00080",
        "092a0efb00100",
        "12441df700200",
        "3081a9c300400",
        "2113538600800",
        "0236a30d01000",
        "046d421b02000",
        "08ca843704000",
        "11850c6e08000",
        "230a18dc10000",
        "061435b820000",
        "0c286b7040000",
        "1840d6e180000",
    )
)
LENGTH = 50


def build(required_distance: int) -> tuple[CNF, dict[str, object]]:
    cnf = CNF()
    messages = [cnf.new_var() for _ in ROWS]
    codeword = [cnf.new_var() for _ in range(LENGTH)]
    xor_aux: list[int] = []
    cnf.add(*messages)
    for coordinate, output in enumerate(codeword):
        selected = [
            messages[index]
            for index, row in enumerate(ROWS)
            if (row >> coordinate) & 1
        ]
        if not selected:
            cnf.add(-output)
        elif len(selected) == 1:
            cnf.add(-selected[0], output)
            cnf.add(selected[0], -output)
        else:
            previous = selected[0]
            for index, current in enumerate(selected[1:]):
                target = output if index == len(selected) - 2 else cnf.new_var()
                if target != output:
                    xor_aux.append(target)
                cnf.xor_equiv(previous, current, target)
                previous = target
    counter = encode_at_most(cnf, codeword, required_distance - 1)
    metadata: dict[str, object] = {
        "schema": "leanmill.binary_base_distance_cnf_probe.v1",
        "length": LENGTH,
        "dimension": len(ROWS),
        "required_distance": required_distance,
        "maximum_bad_weight": required_distance - 1,
        "rows_hex": [f"0x{row:013x}" for row in ROWS],
        "message_variables": messages,
        "codeword_variables": codeword,
        "xor_auxiliary_variables": xor_aux,
        "counter_variables": counter,
        "variable_count": cnf.variable_count,
        "clause_count": len(cnf.clauses),
    }
    return cnf, metadata


def main() -> None:
    summary: dict[str, object] = {
        "schema": "leanmill.binary_base_distance_cnf_probe_set.v1",
        "coordinate_convention": "bit_i_is_coordinate_i",
    }
    for distance in (13, 14):
        cnf, metadata = build(distance)
        text = cnf.render()
        cnf_path = ROOT / f"binary_base_distance_{distance}.cnf"
        meta_path = ROOT / f"binary_base_distance_{distance}.cnf.json"
        cnf_path.write_text(text, encoding="ascii")
        metadata["cnf_sha256"] = hashlib.sha256(text.encode("ascii")).hexdigest()
        meta_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary[str(distance)] = {
            "cnf": cnf_path.name,
            "metadata": meta_path.name,
            "cnf_sha256": metadata["cnf_sha256"],
            "variable_count": metadata["variable_count"],
            "clause_count": metadata["clause_count"],
        }
    (ROOT / "binary_base_distance_cnf_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
