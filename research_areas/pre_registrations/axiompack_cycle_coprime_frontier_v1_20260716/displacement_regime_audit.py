#!/usr/bin/env python3
"""Stratify the pinned cycle-set database by displacement transitivity."""

from __future__ import annotations

import argparse
from collections import Counter, deque
from collections.abc import Iterable
import json
from pathlib import Path
import sys
import time

from enumeration_database_audit import (
    EXPECTED,
    EXPECTED_COMMIT,
    EXPECTED_ORIGIN,
    _action_is_transitive,
    _canonical_hash,
    _cycle_law_holds,
    _cycle_profile,
    _file_evidence,
    _git_value,
    _iter_tables,
    _source_files,
    _validate_nondegenerate_table,
)


SCHEMA = "leanmill.cycle_set_displacement_regime_audit.v1"
PUBLISHED_FPL_COUNTS = {8: 70, 9: 13}


def _inverse(permutation: list[int]) -> list[int]:
    result = [0] * len(permutation)
    for source, target in enumerate(permutation):
        result[target] = source
    return result


def _compose(left: list[int], right: list[int]) -> list[int]:
    return [left[right[value]] for value in range(len(left))]


def _generator_orbit_is_transitive(
    generators: list[list[int]], *, size: int
) -> bool:
    seen = {0}
    queue = deque([0])
    while queue:
        value = queue.popleft()
        for generator in generators:
            target = generator[value]
            if target not in seen:
                seen.add(target)
                if len(seen) == size:
                    return True
                queue.append(target)
    return len(seen) == size


def _displacement_is_transitive(
    table: list[list[int]], *, all_pairs: bool
) -> bool:
    n = len(table)
    if all_pairs:
        inverses = [_inverse(row) for row in table]
        generators = [
            _compose(table[x], inverses[y])
            for x in range(n)
            for y in range(n)
        ]
    else:
        inverse_base = _inverse(table[0])
        generators = [_compose(row, inverse_base) for row in table]
    return _generator_orbit_is_transitive(generators, size=n)


def _profile_rows(
    counts: Counter[tuple[tuple[int, ...], tuple[int, ...]]]
) -> list[dict[str, object]]:
    return [
        {
            "nontrivial_cycle_lengths": list(lengths),
            "common_prime_divisors": list(primes),
            "model_count": count,
        }
        for (lengths, primes), count in sorted(counts.items())
    ]


def _audit_order(
    data_dir: Path,
    *,
    size: int,
    progress_every: int,
) -> dict[str, object]:
    paths = _source_files(data_dir, size)
    files, manifest_sha256 = _file_evidence(paths)
    raw_count = 0
    indecomposable_count = 0
    displacement_transitive_count = 0
    profile_counts = {
        "finite_primitive_level": Counter(),
        "displacement_transitive": Counter(),
    }
    candidates = []
    for path in paths:
        for table_index, table in enumerate(_iter_tables(path, size=size), start=1):
            raw_count += 1
            _validate_nondegenerate_table(table)
            if not _action_is_transitive(table):
                continue
            indecomposable_count += 1
            if not _cycle_law_holds(table):
                raise ValueError(
                    f"{path.name} table {table_index} violates the cycle-set law"
                )
            fixed_base = _displacement_is_transitive(table, all_pairs=False)
            all_pairs = _displacement_is_transitive(table, all_pairs=True)
            if fixed_base != all_pairs:
                raise RuntimeError("displacement generator reductions disagree")
            stratum = (
                "displacement_transitive"
                if fixed_base
                else "finite_primitive_level"
            )
            displacement_transitive_count += int(fixed_base)
            lengths, primes, witnesses = _cycle_profile(table)
            profile_counts[stratum][(lengths, primes)] += 1
            if witnesses:
                candidates.append(
                    {
                        "source_file": path.name,
                        "table_index_1_based": table_index,
                        "stratum": stratum,
                        "witnesses": witnesses,
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
    expected = EXPECTED[size]
    if (
        raw_count != expected["raw_table_count"]
        or indecomposable_count != expected["indecomposable_count"]
    ):
        raise RuntimeError(f"order {size}: source counts changed")
    finite_primitive_level_count = (
        indecomposable_count - displacement_transitive_count
    )
    published = PUBLISHED_FPL_COUNTS.get(size)
    if published is not None and finite_primitive_level_count != published:
        raise RuntimeError(
            f"order {size}: expected {published} finite-primitive-level models, "
            f"got {finite_primitive_level_count}"
        )
    return {
        "carrier_size": size,
        "raw_table_count": raw_count,
        "indecomposable_count": indecomposable_count,
        "finite_primitive_level_count": finite_primitive_level_count,
        "displacement_transitive_count": displacement_transitive_count,
        "published_finite_primitive_level_count": published,
        "published_count_matched": published is None or published == finite_primitive_level_count,
        "file_manifest_sha256": manifest_sha256,
        "files": files,
        "strata": {
            key: {
                "model_count": sum(counter.values()),
                "cycle_profiles": _profile_rows(counter),
            }
            for key, counter in profile_counts.items()
        },
        "coprime_cycle_counterexample_count": len(candidates),
        "coprime_cycle_counterexamples": candidates,
    }


def _self_test() -> None:
    rows = [
        [1, 0, 2],
        [0, 2, 1],
        [2, 1, 0],
    ]
    assert _displacement_is_transitive(rows, all_pairs=False) == (
        _displacement_is_transitive(rows, all_pairs=True)
    )
    constant_cycle = [[1, 2, 0] for _ in range(3)]
    assert _action_is_transitive(constant_cycle)
    assert not _displacement_is_transitive(constant_cycle, all_pairs=False)


def run_audit(
    repository: Path,
    *,
    sizes: Iterable[int],
    progress_every: int,
) -> dict[str, object]:
    _self_test()
    repository = repository.resolve()
    commit = _git_value(repository, "rev-parse", "HEAD")
    origin = _git_value(repository, "config", "--get", "remote.origin.url")
    if commit != EXPECTED_COMMIT or origin != EXPECTED_ORIGIN:
        raise RuntimeError("enumeration source identity mismatch")
    started = time.monotonic()
    orders = [
        _audit_order(
            repository / "IYB" / "data",
            size=size,
            progress_every=progress_every,
        )
        for size in sizes
    ]
    hard_models = sum(row["displacement_transitive_count"] for row in orders)
    core: dict[str, object] = {
        "schema": SCHEMA,
        "source": {
            "repository": EXPECTED_ORIGIN,
            "commit": commit,
        },
        "criterion": (
            "Castelli Theorem 22: finite primitive level iff Dis(X) is intransitive"
        ),
        "orders": orders,
        "aggregate": {
            "indecomposable_count": sum(row["indecomposable_count"] for row in orders),
            "finite_primitive_level_count": sum(
                row["finite_primitive_level_count"] for row in orders
            ),
            "displacement_transitive_count": hard_models,
            "coprime_cycle_counterexample_count": sum(
                row["coprime_cycle_counterexample_count"] for row in orders
            ),
        },
        "result": (
            "counterexample_found"
            if any(row["coprime_cycle_counterexample_count"] for row in orders)
            else "common_prime_pattern_survives_selected_displacement_transitive_strata"
        ),
        "claim_boundary": (
            "finite database stratification only; persistence in the displacement-"
            "transitive stratum supplies no unrestricted implication"
        ),
        "authority": "deterministic_campaign_local_displacement_audit",
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
        choices=sorted(EXPECTED),
        default=[8, 9, 10],
    )
    parser.add_argument("--progress-every", type=int, default=250_000)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_test:
        _self_test()
        print(json.dumps({"schema": SCHEMA, "self_test": "pass"}, sort_keys=True))
        return 0
    if args.repository is None:
        parser.error("--repository is required unless --self-test is used")
    print(
        json.dumps(
            run_audit(
                args.repository,
                sizes=args.sizes,
                progress_every=args.progress_every,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
