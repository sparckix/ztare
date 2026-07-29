#!/usr/bin/env python3
"""Replay a CaDiCaL SAT model against both the probe CNF and code semantics."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_binary_distance_sat_model.py CADICAL CNF")
    solver, cnf_text = sys.argv[1], sys.argv[2]
    cnf_path = Path(cnf_text).resolve()
    metadata = json.loads(cnf_path.with_suffix(".cnf.json").read_text())
    rows = tuple(int(value, 16) for value in metadata["rows_hex"])
    run = subprocess.run(
        [solver, str(cnf_path), "--quiet", "--sat"],
        check=False,
        capture_output=True,
        text=True,
    )
    if run.returncode != 10 or "s SATISFIABLE" not in run.stdout:
        raise RuntimeError(f"expected SAT exit 10, got {run.returncode}")
    literals = [
        int(token)
        for line in run.stdout.splitlines()
        if line.startswith("v ")
        for token in line.split()[1:]
        if token != "0"
    ]
    assignment = {abs(literal): literal > 0 for literal in literals}
    clauses = [
        tuple(map(int, line.split()[:-1]))
        for line in cnf_path.read_text(encoding="ascii").splitlines()
        if line and not line.startswith(("c", "p"))
    ]
    if len(assignment) != metadata["variable_count"]:
        raise ValueError("SAT model does not assign every declared variable")
    if any(
        not any(assignment[abs(literal)] == (literal > 0) for literal in clause)
        for clause in clauses
    ):
        raise ValueError("SAT model fails a CNF clause")

    message = sum(
        1 << index
        for index, variable in enumerate(metadata["message_variables"])
        if assignment[variable]
    )
    encoded = 0
    for index, row in enumerate(rows):
        if (message >> index) & 1:
            encoded ^= row
    model_word = sum(
        1 << index
        for index, variable in enumerate(metadata["codeword_variables"])
        if assignment[variable]
    )
    if message == 0 or model_word != encoded:
        raise ValueError("SAT model disagrees with the frozen binary encoding")
    if encoded.bit_count() > metadata["maximum_bad_weight"]:
        raise ValueError("SAT model violates the encoded weight bound")
    print(json.dumps({
        "schema": "leanmill.binary_distance_sat_model_replay.v1",
        "cnf": cnf_path.name,
        "all_clauses_satisfied": True,
        "assigned_variables": len(assignment),
        "message_hex": hex(message),
        "codeword_hex": hex(encoded),
        "weight": encoded.bit_count(),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
