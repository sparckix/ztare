#!/usr/bin/env python3
"""Audit permutation-group singularity in the displacement-transitive stratum."""

from __future__ import annotations

import argparse
from collections import Counter, deque
from collections.abc import Iterable
import json
from pathlib import Path
import sys
import time

from sympy.combinatorics import Permutation, PermutationGroup

from displacement_regime_audit import (
    _compose,
    _displacement_is_transitive,
    _inverse,
)
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


SCHEMA = "leanmill.cycle_set_singular_hard_regime_audit.v1"
EXPECTED_HARD_COUNTS = {8: 30, 9: 3}


def _prime_factors(value: int) -> tuple[int, ...]:
    factors = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            factors.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor += 1
    if value > 1:
        factors.append(value)
    return tuple(factors)


def _explicit_group_order(generators: list[list[int]]) -> int:
    """Enumerate the finite permutation group by a direct Cayley-graph BFS."""

    size = len(generators[0])
    identity = tuple(range(size))
    steps = {
        tuple(generator) for generator in generators
    } | {
        tuple(_inverse(generator)) for generator in generators
    }
    seen = {identity}
    queue = deque([identity])
    while queue:
        current = list(queue.popleft())
        for step in steps:
            product = tuple(_compose(list(step), current))
            if product not in seen:
                seen.add(product)
                queue.append(product)
    return len(seen)


def _schreier_sims_order(generators: list[list[int]]) -> int:
    size = len(generators[0])
    group = PermutationGroup(
        *[Permutation(generator, size=size) for generator in generators]
    )
    return int(group.order())


def _checked_group_order(generators: list[list[int]]) -> int:
    explicit = _explicit_group_order(generators)
    schreier_sims = _schreier_sims_order(generators)
    if explicit != schreier_sims:
        raise RuntimeError(
            f"group-order engines disagree: explicit={explicit}, "
            f"schreier_sims={schreier_sims}"
        )
    return explicit


def _hard_model_row(
    table: list[list[int]],
    *,
    source_file: str,
    table_index: int,
) -> dict[str, object]:
    size = len(table)
    inverse_base = _inverse(table[0])
    displacement_generators = [
        _compose(row, inverse_base) for row in table
    ]
    group_order = _checked_group_order(table)
    displacement_order = _checked_group_order(displacement_generators)
    if group_order % displacement_order:
        raise RuntimeError("displacement order does not divide permutation-group order")
    carrier_primes = _prime_factors(size)
    group_primes = _prime_factors(group_order)
    outside_primes = tuple(
        prime for prime in group_primes if prime not in carrier_primes
    )
    lengths, common_primes, coprime_witnesses = _cycle_profile(table)
    return {
        "source_file": source_file,
        "table_index_1_based": table_index,
        "carrier_size": size,
        "permutation_group_order": group_order,
        "displacement_group_order": displacement_order,
        "permutation_group_prime_divisors": list(group_primes),
        "carrier_prime_divisors": list(carrier_primes),
        "singular_prime_divisors": list(outside_primes),
        "singular": bool(outside_primes),
        "nontrivial_cycle_lengths": list(lengths),
        "common_cycle_prime_divisors": list(common_primes),
        "coprime_cycle_witnesses": coprime_witnesses,
        "table_1_based": [
            [entry + 1 for entry in row] for row in table
        ] if outside_primes else None,
    }


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
    hard_rows = []
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
            if not _displacement_is_transitive(table, all_pairs=False):
                continue
            if not _displacement_is_transitive(table, all_pairs=True):
                raise RuntimeError("displacement generator reductions disagree")
            hard_rows.append(
                _hard_model_row(
                    table,
                    source_file=path.name,
                    table_index=table_index,
                )
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
        or len(hard_rows) != EXPECTED_HARD_COUNTS[size]
    ):
        raise RuntimeError(f"order {size}: source or hard-stratum counts changed")
    profile_counts = Counter(
        (
            int(row["permutation_group_order"]),
            int(row["displacement_group_order"]),
            tuple(row["singular_prime_divisors"]),
            tuple(row["nontrivial_cycle_lengths"]),
            tuple(row["common_cycle_prime_divisors"]),
        )
        for row in hard_rows
    )
    singular = [row for row in hard_rows if row["singular"]]
    return {
        "carrier_size": size,
        "raw_table_count": raw_count,
        "indecomposable_count": indecomposable_count,
        "displacement_transitive_count": len(hard_rows),
        "singular_hard_regime_count": len(singular),
        "file_manifest_sha256": manifest_sha256,
        "files": files,
        "group_profile_distribution": [
            {
                "permutation_group_order": group_order,
                "displacement_group_order": displacement_order,
                "singular_prime_divisors": list(outside_primes),
                "nontrivial_cycle_lengths": list(lengths),
                "common_cycle_prime_divisors": list(common_primes),
                "model_count": count,
            }
            for (
                group_order,
                displacement_order,
                outside_primes,
                lengths,
                common_primes,
            ), count in sorted(profile_counts.items())
        ],
        "singular_witnesses": singular,
    }


def _self_test() -> None:
    transposition = [1, 0, 2]
    three_cycle = [1, 2, 0]
    assert _checked_group_order([transposition, three_cycle]) == 6
    assert _checked_group_order([three_cycle]) == 3
    assert _prime_factors(72) == (2, 3)


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
    witnesses = [
        witness
        for order in orders
        for witness in order["singular_witnesses"]
    ]
    core: dict[str, object] = {
        "schema": SCHEMA,
        "source": {"repository": EXPECTED_ORIGIN, "commit": commit},
        "orders": orders,
        "aggregate": {
            "displacement_transitive_count": sum(
                row["displacement_transitive_count"] for row in orders
            ),
            "singular_hard_regime_count": len(witnesses),
            "coprime_cycle_counterexample_count": sum(
                bool(witness["coprime_cycle_witnesses"])
                for witness in witnesses
            ),
        },
        "result": (
            "singular_without_finite_primitive_level_witness_found"
            if witnesses
            else "no_singular_example_in_selected_hard_regime"
        ),
        "independent_group_order_engines": [
            "explicit_cayley_bfs",
            "sympy_schreier_sims",
        ],
        "claim_boundary": (
            "complete only for the pinned displacement-transitive order-8/9 "
            "database stratum; any positive witness is a finite construction, "
            "not a resolution of Question 30"
        ),
        "authority": "deterministic_campaign_local_group_audit",
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
        choices=sorted(EXPECTED_HARD_COUNTS),
        default=sorted(EXPECTED_HARD_COUNTS),
    )
    parser.add_argument("--progress-every", type=int, default=100_000)
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
