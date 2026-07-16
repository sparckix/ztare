#!/usr/bin/env python3
"""Replay the coprime-cycle audit against the published cycle-set database.

The source repository enumerates involutive Yang--Baxter solutions up to
isomorphism through order 10.  Its IYB tables are left-translation tables for
cycle sets.  This audit parses every selected table without GAP, recomputes
indecomposability from the generated permutation action, verifies the cycle-set
axioms on every indecomposable table, and searches for the coprime-cycle
counterexample requested by Castelli's Question 30.

Database completeness is inherited from the cited enumeration.  The checks in
this file independently validate the parsed tables and the target predicate;
they do not reconstruct the authors' isomorph-free enumeration proof.
"""

from __future__ import annotations

import argparse
import ast
import bz2
from collections import Counter, deque
from collections.abc import Iterable, Iterator
import hashlib
import json
from math import gcd
from pathlib import Path
import subprocess
import sys
import time


SCHEMA = "leanmill.cycle_set_enumeration_database_audit.v1"
EXPECTED_ORIGIN = "https://github.com/vendramin/enumeration.git"
EXPECTED_COMMIT = "92f85ee118ec73fdb7a397e4fd748f1265f02bc3"
EXPECTED = {
    8: {
        "raw_table_count": 34_530,
        "indecomposable_count": 100,
        "file_sha256": {
            "CSsize8.g.bz2": (
                "5da619c7e2d8ae1a228bd032f72b89d03ae14345c50bdda6ca84274630cd59b9"
            ),
        },
    },
    9: {
        "raw_table_count": 321_931,
        "indecomposable_count": 16,
        "file_sha256": {
            "CSsize9.g.bz2": (
                "f4850998a42505305b3cf37769ec16b2e971e529eb9ada0560fcdce1631c3f94"
            ),
        },
    },
    10: {
        "raw_table_count": 4_895_272,
        "indecomposable_count": 36,
        "file_count": 42,
        "manifest_sha256": (
            "3d343e26b6f9a2c3db941480af1d1aca4eeb56b081680f86125cb70079a1713e"
        ),
    },
}


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _numeric_file_key(path: Path) -> tuple[int, str]:
    stem = path.name.removesuffix(".bz2").removesuffix(".g")
    suffix = stem.rsplit("_", maxsplit=1)[-1]
    return (int(suffix) if suffix.isdigit() else 0, path.name)


def _source_files(data_dir: Path, size: int) -> list[Path]:
    if size in (8, 9):
        compressed = data_dir / f"CSsize{size}.g.bz2"
        plain = data_dir / f"CSsize{size}.g"
        path = compressed if compressed.exists() else plain
        if not path.exists():
            raise FileNotFoundError(f"missing database file for order {size}")
        return [path]
    if size == 10:
        compressed = sorted(data_dir.glob("CSsize10_*.g.bz2"), key=_numeric_file_key)
        paths = compressed or sorted(
            data_dir.glob("CSsize10_*.g"), key=_numeric_file_key
        )
        if not paths:
            raise FileNotFoundError("missing partitioned database files for order 10")
        return paths
    raise ValueError(f"unsupported database order: {size}")


def _open_text(path: Path):
    if path.suffix == ".bz2":
        return bz2.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _iter_tables(path: Path, *, size: int) -> Iterator[list[list[int]]]:
    """Parse one-table-per-line GAP data and convert entries to zero-based."""

    with _open_text(path) as handle:
        for line_number, line in enumerate(handle, start=1):
            payload = line.strip()
            if not payload.startswith("["):
                continue
            if payload.endswith(","):
                payload = payload[:-1]
            try:
                value = ast.literal_eval(payload)
            except (SyntaxError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: malformed GAP table") from exc
            if not isinstance(value, list) or len(value) != size:
                raise ValueError(f"{path}:{line_number}: expected {size} rows")
            table = []
            for row in value:
                if not isinstance(row, list) or len(row) != size:
                    raise ValueError(
                        f"{path}:{line_number}: expected a square order-{size} table"
                    )
                table.append([int(entry) - 1 for entry in row])
            yield table


def _validate_nondegenerate_table(table: list[list[int]]) -> None:
    n = len(table)
    expected = list(range(n))
    if any(sorted(row) != expected for row in table):
        raise ValueError("left translation is not a permutation")
    if sorted(table[x][x] for x in range(n)) != expected:
        raise ValueError("diagonal map is not a permutation")


def _cycle_law_holds(table: list[list[int]]) -> bool:
    n = len(table)
    for x in range(n):
        row_x = table[x]
        for y in range(n):
            row_y = table[y]
            xy = row_x[y]
            yx = row_y[x]
            for z in range(n):
                if table[xy][row_x[z]] != table[yx][row_y[z]]:
                    return False
    return True


def _action_is_transitive(table: list[list[int]]) -> bool:
    """Test the orbit of 0 under the group generated by table rows.

    Forward generator edges suffice: each row is a finite permutation, so its
    inverse is a positive power of the same row.
    """

    n = len(table)
    seen = {0}
    queue = deque([0])
    while queue:
        value = queue.popleft()
        for row in table:
            target = row[value]
            if target not in seen:
                seen.add(target)
                if len(seen) == n:
                    return True
                queue.append(target)
    return len(seen) == n


def _cycles(permutation: list[int]) -> list[list[int]]:
    unseen = set(range(len(permutation)))
    result = []
    while unseen:
        start = min(unseen)
        cycle = []
        value = start
        while value in unseen:
            unseen.remove(value)
            cycle.append(value)
            value = permutation[value]
        result.append(cycle)
    return result


def _prime_divisors(value: int) -> list[int]:
    result = []
    candidate = 2
    remaining = value
    while candidate * candidate <= remaining:
        if remaining % candidate == 0:
            result.append(candidate)
            while remaining % candidate == 0:
                remaining //= candidate
        candidate += 1
    if remaining > 1:
        result.append(remaining)
    return result


def _cycle_profile(
    table: list[list[int]],
) -> tuple[tuple[int, ...], tuple[int, ...], list[dict[str, object]]]:
    n = len(table)
    lengths = set()
    witnesses = []
    for row_index, row in enumerate(table):
        for cycle in _cycles(row):
            length = len(cycle)
            if length == 1:
                continue
            lengths.add(length)
            if gcd(length, n) == 1:
                witnesses.append(
                    {
                        "row_index": row_index,
                        "cycle": cycle,
                        "cycle_length": length,
                    }
                )
    ordered_lengths = tuple(sorted(lengths))
    common_primes = tuple(
        prime
        for prime in _prime_divisors(n)
        if ordered_lengths and all(length % prime == 0 for length in ordered_lengths)
    )
    return ordered_lengths, common_primes, witnesses


def _git_value(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _file_evidence(paths: list[Path]) -> tuple[list[dict[str, object]], str]:
    rows = []
    for path in sorted(paths, key=lambda item: item.name):
        rows.append(
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    manifest_text = "".join(
        f"{row['sha256']}  {row['name']}\n" for row in rows
    )
    return rows, hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()


def _audit_size(
    data_dir: Path,
    *,
    size: int,
    verify_all_laws: bool,
    progress_every: int,
) -> dict[str, object]:
    paths = _source_files(data_dir, size)
    files, manifest_sha256 = _file_evidence(paths)
    expected = EXPECTED[size]
    expected_file_hashes = expected.get("file_sha256", {})
    for row in files:
        expected_hash = expected_file_hashes.get(row["name"])
        if expected_hash is not None and row["sha256"] != expected_hash:
            raise RuntimeError(f"source digest mismatch: {row['name']}")
    if "file_count" in expected and len(files) != expected["file_count"]:
        raise RuntimeError(f"unexpected file count for order {size}: {len(files)}")
    if (
        "manifest_sha256" in expected
        and manifest_sha256 != expected["manifest_sha256"]
    ):
        raise RuntimeError(f"source manifest mismatch for order {size}")

    raw_count = 0
    indecomposable_count = 0
    law_verified_count = 0
    profile_counts: Counter[tuple[tuple[int, ...], tuple[int, ...]]] = Counter()
    file_counts: Counter[str] = Counter()
    file_indecomposable_counts: Counter[str] = Counter()
    candidates = []
    for path in paths:
        for table_index, table in enumerate(_iter_tables(path, size=size), start=1):
            raw_count += 1
            file_counts[path.name] += 1
            _validate_nondegenerate_table(table)
            transitive = _action_is_transitive(table)
            if verify_all_laws or transitive:
                if not _cycle_law_holds(table):
                    raise ValueError(
                        f"{path.name} table {table_index} violates the cycle-set law"
                    )
                law_verified_count += 1
            if transitive:
                indecomposable_count += 1
                file_indecomposable_counts[path.name] += 1
                lengths, common_primes, witnesses = _cycle_profile(table)
                profile_counts[(lengths, common_primes)] += 1
                if witnesses:
                    candidates.append(
                        {
                            "source_file": path.name,
                            "table_index_1_based": table_index,
                            "nontrivial_cycle_lengths": list(lengths),
                            "coprime_cycle_witnesses": witnesses,
                            "table_1_based": [
                                [entry + 1 for entry in row] for row in table
                            ],
                        }
                    )
            if progress_every and raw_count % progress_every == 0:
                print(
                    f"order {size}: parsed {raw_count:,} tables",
                    file=sys.stderr,
                    flush=True,
                )

    if raw_count != expected["raw_table_count"]:
        raise RuntimeError(
            f"order {size}: expected {expected['raw_table_count']} tables, got {raw_count}"
        )
    if indecomposable_count != expected["indecomposable_count"]:
        raise RuntimeError(
            "order "
            f"{size}: expected {expected['indecomposable_count']} indecomposable "
            f"tables, got {indecomposable_count}"
        )

    profiles = [
        {
            "nontrivial_cycle_lengths": list(lengths),
            "common_prime_divisors": list(common_primes),
            "model_count": count,
        }
        for (lengths, common_primes), count in sorted(profile_counts.items())
    ]
    return {
        "carrier_size": size,
        "files": files,
        "file_manifest_sha256": manifest_sha256,
        "file_table_counts": dict(sorted(file_counts.items())),
        "file_indecomposable_counts": dict(
            sorted(file_indecomposable_counts.items())
        ),
        "raw_table_count": raw_count,
        "nondegenerate_table_count": raw_count,
        "cycle_law_verified_count": law_verified_count,
        "cycle_law_verification_scope": (
            "all_parsed_tables" if verify_all_laws else "all_indecomposable_tables"
        ),
        "indecomposable_count": indecomposable_count,
        "cycle_profiles": profiles,
        "coprime_cycle_counterexample_count": len(candidates),
        "coprime_cycle_counterexamples": candidates,
        "expected_counts_matched": True,
    }


def _self_test() -> None:
    identity = [[0, 1, 2] for _ in range(3)]
    cyclic = [[1, 2, 0] for _ in range(3)]
    for table in (identity, cyclic):
        _validate_nondegenerate_table(table)
        assert _cycle_law_holds(table)
    assert not _action_is_transitive(identity)
    assert _action_is_transitive(cyclic)
    lengths, common_primes, witnesses = _cycle_profile(cyclic)
    assert lengths == (3,)
    assert common_primes == (3,)
    assert witnesses == []


def run_audit(
    repository: Path,
    *,
    sizes: Iterable[int],
    verify_all_laws: bool,
    progress_every: int,
) -> dict[str, object]:
    _self_test()
    repository = repository.resolve()
    commit = _git_value(repository, "rev-parse", "HEAD")
    origin = _git_value(repository, "config", "--get", "remote.origin.url")
    if commit != EXPECTED_COMMIT:
        raise RuntimeError(f"expected source commit {EXPECTED_COMMIT}, got {commit}")
    if origin != EXPECTED_ORIGIN:
        raise RuntimeError(f"expected source origin {EXPECTED_ORIGIN}, got {origin}")
    data_dir = repository / "IYB" / "data"
    started = time.monotonic()
    results = [
        _audit_size(
            data_dir,
            size=size,
            verify_all_laws=verify_all_laws,
            progress_every=progress_every,
        )
        for size in sizes
    ]
    core: dict[str, object] = {
        "schema": SCHEMA,
        "source": {
            "repository": EXPECTED_ORIGIN,
            "commit": commit,
            "enumeration_scope": (
                "authors' isomorphism-class database of involutive solutions "
                "through order 10"
            ),
            "citation": (
                "Akgun--Mereb--Vendramin, Math. Comp. 91 (2022), 1469--1481, "
                "doi:10.1090/mcom/3696"
            ),
        },
        "target": {
            "description": (
                "an indecomposable finite cycle set with a nontrivial left-row "
                "cycle whose length is coprime to the carrier size"
            ),
            "question": "Castelli 2025, Question 30",
        },
        "orders": results,
        "result": (
            "counterexample_found"
            if any(row["coprime_cycle_counterexample_count"] for row in results)
            else "no_counterexample_in_selected_database_orders"
        ),
        "claim_boundary": (
            "finite database audit only; source completeness is inherited from "
            "the authors' enumeration, and no unrestricted implication follows"
        ),
        "authority": "deterministic_campaign_local_external_database_audit",
    }
    return {
        **core,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "receipt_sha256": _canonical_hash(core),
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path)
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[8, 9, 10],
        choices=sorted(EXPECTED),
    )
    parser.add_argument("--verify-all-laws", action="store_true")
    parser.add_argument("--progress-every", type=int, default=250_000)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_test:
        _self_test()
        print(json.dumps({"schema": SCHEMA, "self_test": "pass"}, sort_keys=True))
        return 0
    if args.repository is None:
        parser.error("--repository is required unless --self-test is used")
    if args.progress_every < 0:
        parser.error("--progress-every must be nonnegative")
    print(
        json.dumps(
            run_audit(
                args.repository,
                sizes=args.sizes,
                verify_all_laws=args.verify_all_laws,
                progress_every=args.progress_every,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
