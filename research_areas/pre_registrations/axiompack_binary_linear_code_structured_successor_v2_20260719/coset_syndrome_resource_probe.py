"""Bounded resource probe for the killed full-syndrome-table route.

This executable computes the exact dual-spectrum support and benchmarks only
16--26 syndrome bits.  The native worker refuses the 31-bit campaign instance.
It cannot produce a covering certificate or a construction witness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from math import comb
from pathlib import Path
import subprocess
import tempfile
import time

from coset_extension_cegis import frozen_shortening
from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.theory_ir import content_hash


ROOT = Path(__file__).resolve().parent
NATIVE_SOURCE = ROOT / "coset_syndrome_distance_transform.c"
DEFAULT_OUTPUT = ROOT / "coset_syndrome_resource_probe_receipt.json"
PROBE_BITS = (16, 18, 20, 22, 24, 26)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def exact_spectra() -> tuple[list[int], list[int]]:
    matrix = frozen_shortening(0)
    primal = [0] * 51
    primal[0] = 1
    previous_gray = 0
    word = 0
    for step in range(1, 1 << 19):
        gray = step ^ (step >> 1)
        word ^= matrix.rows[(gray ^ previous_gray).bit_length() - 1]
        primal[word.bit_count()] += 1
        previous_gray = gray
    dual = []
    for degree in range(51):
        numerator = 0
        for weight, multiplicity in enumerate(primal):
            if not multiplicity:
                continue
            polynomial = sum(
                (-1 if term & 1 else 1)
                * comb(weight, term)
                * comb(50 - weight, degree - term)
                for term in range(
                    max(0, degree - (50 - weight)),
                    min(degree, weight) + 1,
                )
            )
            numerator += multiplicity * polynomial
        coefficient, remainder = divmod(numerator, 1 << 19)
        if remainder or coefficient < 0:
            raise AssertionError("integer MacWilliams replay failed")
        dual.append(coefficient)
    if sum(primal) != 1 << 19 or sum(dual) != 1 << 31:
        raise AssertionError("weight-spectrum mass mismatch")
    return primal, dual


def run_probe(*, threads: int) -> dict[str, object]:
    if not 1 <= threads <= 64:
        raise ValueError("threads must lie in [1,64]")
    matrix = frozen_shortening(0)
    masks = tuple(row >> 19 for row in matrix.rows)
    primal, dual = exact_spectra()
    support = [weight for weight, count in enumerate(dual) if weight and count]
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="axiompack-syndrome-probe-") as raw:
        workspace = Path(raw)
        executable = workspace / "distance_transform_probe"
        compile_command = [
            "clang",
            "-std=c11",
            "-O3",
            "-pthread",
            str(NATIVE_SOURCE),
            "-o",
            str(executable),
        ]
        subprocess.run(compile_command, check=True, capture_output=True, text=True)
        compiler = subprocess.run(
            ["clang", "--version"], check=True, capture_output=True, text=True
        ).stdout.splitlines()[0]
        measurements = []
        for bits in PROBE_BITS:
            mask_file = workspace / f"masks_{bits}.txt"
            table_file = workspace / f"table_{bits}.bin"
            truncation = (1 << bits) - 1
            mask_file.write_text(
                f"{bits} {len(masks)}\n"
                + "".join(f"{value & truncation:x}\n" for value in masks),
                encoding="ascii",
            )
            wall_started = time.monotonic()
            completed = subprocess.run(
                [str(executable), str(mask_file), str(table_file), str(threads)],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            wall_ms = max(1, int((time.monotonic() - wall_started) * 1000))
            native = json.loads(completed.stdout)
            if (
                native.get("schema")
                != "axiompack.binary_syndrome_distance_transform_resource_probe.v1"
                or native.get("state_count") != 1 << bits
                or sum(native.get("histogram", [])) != 1 << bits
                or table_file.stat().st_size != 1 << bits
            ):
                raise AssertionError("native resource probe failed replay")
            measurements.append(
                {
                    "syndrome_bits": bits,
                    "states": 1 << bits,
                    "table_bytes": 1 << bits,
                    "directional_relaxations": bits * (1 << bits),
                    "wall_ms": wall_ms,
                    "transform_elapsed_ms": native["transform_elapsed_ms"],
                    "total_elapsed_ms": native["total_elapsed_ms"],
                    "maximum_distance_on_truncated_instance": native[
                        "maximum_distance"
                    ],
                }
            )
    full_bits = 31
    full_model = {
        "syndrome_bits": full_bits,
        "states": 1 << full_bits,
        "table_bytes": 1 << full_bits,
        "pair_butterflies": full_bits * (1 << (full_bits - 1)),
        "directional_relaxations": full_bits * (1 << full_bits),
        "compact_certificate_available": False,
        "execution_authorized": False,
    }
    core = {
        "schema": "axiompack.binary_syndrome_resource_probe.v1",
        "status": "full_table_route_killed_no_compact_certificate",
        "hypothesis_id": "H-AXIOMPACK-BLC-20260720-02",
        "source_artifact_sha256": matrix.artifact_sha256,
        "native_source_sha256": sha256(NATIVE_SOURCE),
        "compiler": compiler,
        "compile_command": compile_command,
        "threads": threads,
        "primal_weight_distribution": primal,
        "dual_weight_distribution": dual,
        "dual_nonzero_weight_support": support,
        "external_distance": len(support),
        "external_distance_disposition": "bound_too_weak",
        "measurements": measurements,
        "full_instance_resource_model": full_model,
        "elapsed_ms": max(1, int((time.monotonic() - started) * 1000)),
        "claim_scope": (
            "resource and certificate-format evidence only; no covering-radius, "
            "extension-cone, or ambient code-existence authority"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run_probe(threads=args.threads)
    write_json_atomic(args.output, receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "external_distance": receipt["external_distance"],
                "largest_probe_bits": receipt["measurements"][-1][
                    "syndrome_bits"
                ],
                "receipt_sha256": receipt["receipt_sha256"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
