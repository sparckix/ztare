"""Data-plugin catalog and authoring services shared by the scenario CLI."""
from __future__ import annotations

import json
import re
from typing import Any


def safe_name(name: str) -> str:
    slug = re.sub(r"\s+", "-", str(name or "").strip().lower())
    return re.sub(r"[^a-z0-9_-]", "", slug)[:64]


def scenario_rows() -> list[dict[str, Any]]:
    from ztare.scenarios.loader import list_scenarios, load_scenario

    rows: list[dict[str, Any]] = []
    for name in list_scenarios():
        try:
            scenario = load_scenario(name)
            rows.append({
                "name": scenario.name or name,
                "description": (scenario.description or "").strip(),
                "rubric": scenario.rubric,
                "evidence_sources": list(scenario.evidence_sources),
                "renderer": scenario.renderer,
                "rechecks": list(scenario.rechecks),
                "workbench_panels": list(scenario.workbench_panels),
                "deliverables": list(scenario.deliverables),
                "deliverable_specs": [spec.model_dump(mode="json") for spec in scenario.deliverable_specs],
            })
        except Exception as exc:  # noqa: BLE001 - one broken manifest remains visible.
            rows.append({"name": name, "description": "", "invalid": f"{type(exc).__name__}: {exc}"})
    return rows


def catalog(*, reload: bool = False) -> dict[str, Any]:
    from ztare.common.paths import RUBRICS_DIR
    from ztare.scenarios import registry

    if reload:
        registry.reload()
    scenarios = scenario_rows()
    return {
        "ok": True,
        "scenarios": [row.get("name") for row in scenarios],
        "scenario_details": {str(row.get("name") or ""): row for row in scenarios if row.get("name")},
        "rubrics": sorted(path.stem for path in RUBRICS_DIR.glob("*.json")),
        "capabilities": registry.installed(),
        "capability_details": registry.descriptors(),
        "plugin_errors": registry.diagnostics().get("load_errors", []),
        "plugin_dirs": registry.plugin_dirs(),
    }


def detail(kind: str, name: str) -> dict[str, Any]:
    from ztare.common.paths import RUBRICS_DIR, SCENARIOS_DIR
    from ztare.scenarios.config import ScenarioConfig

    slug = safe_name(name)
    try:
        if kind == "scenario":
            scenario = ScenarioConfig.load(SCENARIOS_DIR / f"{slug}.yaml")
            spec = {"description": scenario.description, "rubric": scenario.rubric, "iters": scenario.iters,
                    "dynamic": scenario.dynamic, "mutator_model": scenario.mutator_model,
                    "judge_model": scenario.judge_model, "gate_package": list(scenario.gate_package),
                    "goal_type": scenario.goal_type, "solvers": list(scenario.solvers),
                    "evidence_sources": list(scenario.evidence_sources), "renderer": scenario.renderer,
                    "rechecks": list(scenario.rechecks), "workbench_panels": list(scenario.workbench_panels),
                    "deliverables": list(scenario.deliverables),
                    "deliverable_specs": [item.model_dump(mode="json") for item in scenario.deliverable_specs]}
        elif kind == "rubric":
            spec = json.loads((RUBRICS_DIR / f"{slug}.json").read_text(encoding="utf-8"))
        else:
            return {"ok": False, "error": f"unknown plugin kind '{kind}'"}
    except Exception as exc:  # noqa: BLE001 - missing or invalid data is a typed authoring error.
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "kind": kind, "name": slug, "spec": spec}


def install(kind: str, name: str, spec: dict[str, Any], *, overwrite: bool = False) -> dict[str, Any]:
    from ztare.common.paths import RUBRICS_DIR, SCENARIOS_DIR
    from ztare.scenarios import registry
    from ztare.scenarios.config import ScenarioConfig

    slug = safe_name(name)
    if not slug:
        return {"ok": False, "error": "invalid name (need letters, numbers, dash, or underscore)"}
    try:
        if kind == "scenario":
            import yaml
            body = {
                "name": slug,
                "description": str(spec.get("description") or "").strip(),
                "rubric": safe_name(spec.get("rubric") or slug),
                "iters": int(spec.get("iters") or 8),
                "dynamic": bool(spec.get("dynamic", True)),
                "mutator_model": str(spec.get("mutator_model") or ""),
                "judge_model": str(spec.get("judge_model") or ""),
                "gate_package": list(spec.get("gate_package") or []),
                "goal_type": str(spec.get("goal_type") or ""),
                "solvers": list(spec.get("solvers") or []),
                "evidence_sources": list(spec.get("evidence_sources") or ["local_files"]),
                "renderer": str(spec.get("renderer") or "markdown"),
                "rechecks": list(spec.get("rechecks") or []),
                "workbench_panels": list(spec.get("workbench_panels") or []),
                "deliverables": list(spec.get("deliverables") or []),
                "deliverable_specs": list(spec.get("deliverable_specs") or []),
            }
            path = SCENARIOS_DIR / f"{slug}.yaml"
            if path.exists() and not overwrite:
                return {"ok": False, "conflict": True,
                        "error": f"scenario '{slug}' already exists; open it from Installed to edit"}
            ScenarioConfig(**body)
            SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
            staged = path.with_name(f".{path.name}.tmp")
            staged.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
            staged.replace(path)
        elif kind == "rubric":
            dimensions = spec.get("dimensions") or []
            total = sum(int(row.get("weight", 0)) for row in dimensions if isinstance(row, dict))
            if not dimensions or total != 100:
                return {"ok": False, "error": f"scoring guide weights must sum to 100 (got {total})"}
            payload = dict(spec)
            payload.setdefault("rubric_mode", "calibration")
            path = RUBRICS_DIR / f"{slug}.json"
            if path.exists() and not overwrite:
                return {"ok": False, "conflict": True,
                        "error": f"scoring guide '{slug}' already exists; open it from Installed to edit"}
            RUBRICS_DIR.mkdir(parents=True, exist_ok=True)
            staged = path.with_name(f".{path.name}.tmp")
            staged.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            staged.replace(path)
        else:
            return {"ok": False, "error": f"unknown plugin kind '{kind}' (scenario | rubric)"}
    except Exception as exc:  # noqa: BLE001 - validation is returned without a partial install.
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    registry.reload()
    return {"ok": True, "kind": kind, "name": slug, "path": str(path), "installed": catalog()}
