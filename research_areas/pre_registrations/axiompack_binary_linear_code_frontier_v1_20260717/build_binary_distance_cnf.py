#!/usr/bin/env python3
"""Generate exact CNFs for the frozen [51,20,14] LRAT certificate probe."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


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
        "7081a9c300400",
        "6113538600800",
        "4236a30d01000",
        "446d421b02000",
        "48ca843704000",
        "51850c6e08000",
        "630a18dc10000",
        "461435b820000",
        "4c286b7040000",
        "5840d6e180000",
    )
)
LENGTH = 51
DIMENSION = 20


class CNF:
    def __init__(self) -> None:
        self.variable_count = 0
        self.clauses: list[tuple[int, ...]] = []
        self.variables: dict[str, object] = {}

    def new_var(self) -> int:
        self.variable_count += 1
        return self.variable_count

    def add(self, *literals: int) -> None:
        if not literals or any(value == 0 for value in literals):
            raise ValueError("CNF clause must be nonempty and zero-free")
        self.clauses.append(tuple(literals))

    def xor_equiv(self, left: int, right: int, output: int) -> None:
        """Add the four clauses for output iff left XOR right."""

        self.add(left, right, -output)
        self.add(left, -right, output)
        self.add(-left, right, output)
        self.add(-left, -right, -output)

    def render(self) -> str:
        rows = [f"p cnf {self.variable_count} {len(self.clauses)}"]
        rows.extend(" ".join(map(str, clause)) + " 0" for clause in self.clauses)
        return "\n".join(rows) + "\n"


def encode_at_most(cnf: CNF, bits: list[int], maximum: int) -> dict[str, int]:
    """Sinz-style prefix counter, satisfiable exactly when sum(bits) <= maximum."""

    if maximum < 1 or maximum >= len(bits):
        raise ValueError("probe counter bound must lie in [1, n-1]")
    state = {
        (index, count): cnf.new_var()
        for index in range(len(bits))
        for count in range(1, maximum + 1)
    }
    for index, bit in enumerate(bits):
        cnf.add(-bit, state[index, 1])
        if index == 0:
            continue
        for count in range(1, maximum + 1):
            cnf.add(-state[index - 1, count], state[index, count])
        for count in range(2, maximum + 1):
            cnf.add(-bit, -state[index - 1, count - 1], state[index, count])
        cnf.add(-bit, -state[index - 1, maximum])
    return {f"s_{index}_{count}": value for (index, count), value in state.items()}


def build(required_distance: int) -> tuple[CNF, dict[str, object]]:
    maximum_weight = required_distance - 1
    cnf = CNF()
    messages = [cnf.new_var() for _ in range(DIMENSION)]
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

    counter = encode_at_most(cnf, codeword, maximum_weight)
    metadata: dict[str, object] = {
        "schema": "leanmill.binary_distance_cnf_probe.v1",
        "length": LENGTH,
        "dimension": DIMENSION,
        "required_distance": required_distance,
        "maximum_bad_weight": maximum_weight,
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
        "schema": "leanmill.binary_distance_cnf_probe_set.v1",
        "coordinate_convention": "bit_i_is_coordinate_i",
    }
    for distance in (14, 15):
        cnf, metadata = build(distance)
        cnf_text = cnf.render()
        cnf_path = ROOT / f"binary_distance_{distance}.cnf"
        metadata_path = ROOT / f"binary_distance_{distance}.cnf.json"
        cnf_path.write_text(cnf_text, encoding="ascii")
        metadata["cnf_sha256"] = hashlib.sha256(cnf_text.encode("ascii")).hexdigest()
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary[str(distance)] = {
            "cnf": cnf_path.name,
            "metadata": metadata_path.name,
            "cnf_sha256": metadata["cnf_sha256"],
            "variable_count": metadata["variable_count"],
            "clause_count": metadata["clause_count"],
        }
    (ROOT / "binary_distance_cnf_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
