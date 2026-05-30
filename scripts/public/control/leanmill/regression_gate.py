#!/usr/bin/env python3
"""Fast regression gate for LeanMill curated repair templates.

This does not run Lean. It protects the mill control plane: row-scoped repair
templates must still compile into the expected packet shape, and registry rows
that previously ratified must not silently lose their executable canary route.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from leanmill_paths import REPAIR_FAMILY_REGISTRY as DEFAULT_REGISTRY

DEFAULT_COMPILER = "scripts/public/control/leanmill/search/path_c_residual_compiler.py"


def _load_compiler(path: str):
    spec = importlib.util.spec_from_file_location("leansearch_path_c_residual_compiler", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load compiler: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}


def build(args: argparse.Namespace) -> dict[str, Any]:
    compiler = _load_compiler(args.compiler)
    templates: dict[str, list[dict[str, Any]]] = compiler.CURATED_REPAIR_TEMPLATES
    failures: list[dict[str, Any]] = []
    packet_ids: set[str] = set()
    curated_rows_checked = 0

    for row_id, row_templates in sorted(templates.items()):
        curated_rows_checked += 1
        kinds = [str(t.get("test_kind") or "") for t in row_templates]
        if "positive" not in kinds:
            failures.append({"row_id": row_id, "failure": "missing_positive_template"})
        if "negative_control" not in kinds:
            failures.append({"row_id": row_id, "failure": "missing_negative_control_template"})
        rec = {"lane": "regression_gate", "row_id": row_id, "residual_class": "source_action_mismatch"}
        test, decision = compiler._compile_one(rec, static_filter="regression_static_filter.json")
        if not test or decision.get("decision") != "executable_curated_repair_canary":
            failures.append({
                "row_id": row_id,
                "failure": "curated_row_no_longer_compiles_to_executable_canary",
                "decision": decision,
            })
        for template in row_templates:
            packet_id = compiler._packet_id(
                rec,
                str(template.get("packet_id_suffix") or ""),
                repair_family=str(template.get("repair_family") or ""),
            )
            if packet_id in packet_ids:
                failures.append({"row_id": row_id, "failure": "duplicate_packet_id", "packet_id": packet_id})
            packet_ids.add(packet_id)

    registry = _read(Path(args.registry))
    registry_rows_checked = 0
    for family in registry.get("families") or []:
        for row_id in family.get("ratified_rows") or []:
            row_id = str(row_id)
            if row_id not in templates:
                continue
            registry_rows_checked += 1
            test, decision = compiler._compile_one(
                {
                    "lane": "registry_replay",
                    "row_id": row_id,
                    "residual_class": "source_action_mismatch",
                },
                static_filter="regression_static_filter.json",
            )
            if not test or decision.get("decision") != "executable_curated_repair_canary":
                failures.append({
                    "row_id": row_id,
                    "family": family.get("family"),
                    "failure": "ratified_registry_row_lost_curated_canary_route",
                    "decision": decision,
                })

    payload = {
        "schema": "leanmill-regression-gate-v1",
        "curated_rows_checked": curated_rows_checked,
        "registry_rows_checked": registry_rows_checked,
        "packet_ids_checked": len(packet_ids),
        "failure_count": len(failures),
        "failures": failures,
        "status": "pass" if not failures else "fail",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    payload = build(argparse.Namespace(compiler=DEFAULT_COMPILER, registry="/tmp/no_such_registry.json", out=None))
    assert payload["curated_rows_checked"] > 0, payload
    assert payload["failure_count"] == 0, payload
    print("leanmill_regression_gate self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compiler", default=DEFAULT_COMPILER)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({
        "status": payload["status"],
        "failure_count": payload["failure_count"],
        "curated_rows_checked": payload["curated_rows_checked"],
        "registry_rows_checked": payload["registry_rows_checked"],
        "out": args.out,
    }, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
