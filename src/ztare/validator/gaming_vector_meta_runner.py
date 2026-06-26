"""Contract-governed promotion runner for GP-086 gaming vectors.

This is the GP-086 successor to the historical V4 hardening-board runner:
the old runner governed six evaluator-hardening stages; this one governs
individual gaming-vector promotions from ``open`` to ``gated``.

It deliberately does not edit ``gaming_vector_catalog.jsonl``. A PASS verdict
is a promotion receipt; the registry flip is a separate, explicit operation.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from ztare.common.kernel_hardener import CATALOG, GamingVector, content_hash, load_catalog
from ztare.common.paths import PROJECTS_DIR

ContractVerdict = Literal["pass", "fail", "blocked"]
Priority = Literal["P0", "P1"]

DEFAULT_PROJECT = "gaming_vector_hardening"
EXPECTED_PROMOTION_CONTRACT = "gaming_vector_promotion_contract_v1"

FALLBACK_OPEN_AUTORESEARCH_VECTOR_QUEUE = [
    "undeclared_parameters_body",
    "audit_partition_seed_fingerprint",
]


@dataclass
class ContractResult:
    verdict: ContractVerdict
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageSpec:
    name: str
    item_number: int
    priority: Priority
    contract_name: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaRunnerState:
    current_stage: int = 0
    last_verdict: ContractVerdict | None = None
    last_report: list[str] = field(default_factory=list)
    completed_stages: list[str] = field(default_factory=list)


@dataclass
class GamingVectorMetaRunner:
    project_dir: Path
    queue: list[StageSpec]
    state: MetaRunnerState
    state_path: Path
    contracts: dict[str, Callable[[Path, StageSpec], ContractResult]]

    def current(self) -> StageSpec:
        if not self.queue:
            raise RuntimeError("Gaming-vector meta-runner queue is empty.")
        if self.state.current_stage >= len(self.queue):
            raise RuntimeError("Gaming-vector meta-runner has no remaining active stage.")
        return self.queue[self.state.current_stage]

    def run_stage(self) -> ContractResult:
        stage = self.current()
        contract = self.contracts[stage.contract_name]
        result = contract(self.project_dir, stage)
        self.state.last_verdict = result.verdict
        self.state.last_report = result.reasons
        if result.verdict == "pass" and stage.name not in self.state.completed_stages:
            self.state.completed_stages.append(stage.name)
        self.save_state()
        return result

    def advance(self) -> None:
        if self.state.last_verdict != "pass":
            raise RuntimeError("Cannot advance: current stage has not passed its promotion contract.")
        if self.state.current_stage >= len(self.queue) - 1:
            raise RuntimeError("Cannot advance: already at final stage.")
        self.state.current_stage += 1
        self.state.last_verdict = None
        self.state.last_report = []
        self.save_state()

    def reset(self) -> None:
        self.state = MetaRunnerState()
        self.save_state()

    def save_state(self) -> None:
        self.state_path.write_text(
            json.dumps(
                {
                    "current_stage": self.state.current_stage,
                    "last_verdict": self.state.last_verdict,
                    "last_report": self.state.last_report,
                    "completed_stages": self.state.completed_stages,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def _catalog_path() -> Path:
    return Path(os.environ.get("ZTARE_GAMING_VECTOR_CATALOG", str(CATALOG)))


def project_dir(project: str) -> Path:
    if project == DEFAULT_PROJECT:
        return _catalog_path().parent / "gaming_vector_hardening_board"
    return PROJECTS_DIR / project


def plan_path(base: Path) -> Path:
    return base / "meta_runner_plan.json"


def state_path(base: Path) -> Path:
    return base / "meta_runner_state.json"


def evidence_path(base: Path, vector_name: str) -> Path:
    return base / "evidence" / f"{vector_name}.json"


def promotion_evidence_dir() -> Path:
    return _catalog_path().parent / "gaming_vector_promotion_evidence"


def open_vector_names(substrate: str = "autoresearch") -> list[str]:
    try:
        vectors = load_catalog(_catalog_path())
    except FileNotFoundError:
        if substrate == "autoresearch":
            return list(FALLBACK_OPEN_AUTORESEARCH_VECTOR_QUEUE)
        return []
    names: list[str] = []
    for vector in vectors:
        if vector.substrate != substrate:
            continue
        if vector.status == "open" and not vector.already_gated_by:
            names.append(vector.name)
    return names


def default_queue(vector_names: list[str] | None = None) -> list[dict[str, Any]]:
    vectors = vector_names if vector_names is not None else open_vector_names("autoresearch")
    return [
        {
            "name": f"promote_{vector}",
            "item_number": idx + 1,
            "priority": "P0" if idx < 4 else "P1",
            "contract_name": EXPECTED_PROMOTION_CONTRACT,
            "details": {
                "substrate": "autoresearch",
                "vector": vector,
                "evidence_path": f"evidence/{vector}.json",
                "promotion_path": f"gaming_vector:autoresearch:{vector}",
            },
        }
        for idx, vector in enumerate(vectors)
    ]


def expected_plan() -> dict[str, Any]:
    return {"queue": default_queue()}


def plan_vector_names(plan: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in plan.get("queue", []):
        details = item.get("details") or {}
        if details.get("substrate", "autoresearch") == "autoresearch" and details.get("vector"):
            names.append(str(details["vector"]))
    return names


def plan_drift(base: Path) -> list[str]:
    p_path = plan_path(base)
    if not p_path.exists():
        return ["meta_runner_plan.json is missing"]
    try:
        current_plan = json.loads(p_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"meta_runner_plan.json is invalid JSON: {exc}"]
    current = plan_vector_names(current_plan)
    expected = open_vector_names("autoresearch")
    reasons: list[str] = []
    if current != expected:
        reasons.append(f"plan queue drift: current={current} expected_open_registry={expected}")
    return reasons


def sync_plan(base: Path) -> None:
    ensure_project(base)
    plan_path(base).write_text(json.dumps(expected_plan(), indent=2) + "\n", encoding="utf-8")
    state_data = json.loads(state_path(base).read_text(encoding="utf-8"))
    new_stage_names = {item["name"] for item in expected_plan()["queue"]}
    completed = [name for name in state_data.get("completed_stages", []) if name in new_stage_names]
    queue_len = len(expected_plan()["queue"])
    current_stage = int(state_data.get("current_stage", 0) or 0)
    if queue_len == 0:
        current_stage = 0
    else:
        current_stage = min(current_stage, queue_len - 1)
    state_path(base).write_text(
        json.dumps(
            {
                "current_stage": current_stage,
                "last_verdict": state_data.get("last_verdict"),
                "last_report": state_data.get("last_report", []),
                "completed_stages": completed,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def ensure_project(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / "evidence").mkdir(parents=True, exist_ok=True)
    promotion_evidence_dir().mkdir(parents=True, exist_ok=True)
    p_path = plan_path(base)
    if not p_path.exists():
        p_path.write_text(json.dumps({"queue": default_queue()}, indent=2) + "\n", encoding="utf-8")
    s_path = state_path(base)
    if not s_path.exists():
        s_path.write_text(
            json.dumps(
                {
                    "current_stage": 0,
                    "last_verdict": None,
                    "last_report": [],
                    "completed_stages": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def _load_stage(item: dict[str, Any]) -> StageSpec:
    return StageSpec(
        name=item["name"],
        item_number=int(item["item_number"]),
        priority=item["priority"],
        contract_name=item["contract_name"],
        details=dict(item.get("details") or {}),
    )


def load_runner(project: str = DEFAULT_PROJECT) -> GamingVectorMetaRunner:
    base = project_dir(project)
    ensure_project(base)
    plan = expected_plan() if project == DEFAULT_PROJECT else json.loads(plan_path(base).read_text(encoding="utf-8"))
    state_data = json.loads(state_path(base).read_text(encoding="utf-8"))
    queue_items = plan.get("queue", [])
    current_stage = int(state_data.get("current_stage", 0) or 0)
    if queue_items:
        current_stage = min(current_stage, len(queue_items) - 1)
    else:
        current_stage = 0
    return GamingVectorMetaRunner(
        project_dir=base,
        queue=[_load_stage(item) for item in queue_items],
        state=MetaRunnerState(
            current_stage=current_stage,
            last_verdict=state_data.get("last_verdict"),
            last_report=list(state_data.get("last_report", [])),
            completed_stages=list(state_data.get("completed_stages", [])),
        ),
        state_path=state_path(base),
        contracts=CONTRACT_REGISTRY,
    )


def _find_vector(substrate: str, name: str) -> GamingVector | None:
    for vector in load_catalog(_catalog_path()):
        if vector.substrate == substrate and vector.name == name:
            return vector
    return None


def _load_evidence(base: Path, stage: StageSpec) -> tuple[dict[str, Any] | None, str]:
    rel = stage.details.get("evidence_path") or f"evidence/{stage.details.get('vector')}.json"
    raw_path = Path(rel)
    path = raw_path if raw_path.is_absolute() else base / raw_path
    candidates = [path]
    if not path.exists() and raw_path.name:
        candidates.append(promotion_evidence_dir() / raw_path.name)
    path = next((candidate for candidate in candidates if candidate.exists()), path)
    if not path.exists():
        return None, " or ".join(str(candidate) for candidate in candidates)
    try:
        return json.loads(path.read_text(encoding="utf-8")), str(path)
    except json.JSONDecodeError as exc:
        return {"__invalid_json__": str(exc)}, str(path)


def _artifact_paths(evidence: dict[str, Any]) -> list[Path]:
    out: list[Path] = []
    for row in evidence.get("exposing_artifacts", []):
        if isinstance(row, str):
            out.append(Path(row))
        elif isinstance(row, dict) and row.get("path"):
            out.append(Path(row["path"]))
    return out


def _check_artifact_hashes(evidence: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for row in evidence.get("exposing_artifacts", []):
        if not isinstance(row, dict) or not row.get("path"):
            continue
        path = Path(row["path"])
        if not path.exists():
            reasons.append(f"exposing artifact missing: {path}")
            continue
        expected = row.get("sha")
        if expected and expected != content_hash(path):
            reasons.append(f"sha mismatch for {path}: expected {expected}, got {content_hash(path)}")
    return reasons


def _mine_vectors(substrate: str, artifacts: list[Path]) -> tuple[set[str], str]:
    if substrate == "autoresearch":
        from ztare.validator.autoresearch_hardener import AutoresearchHardener

        hardener = AutoresearchHardener()
        return {v.name for v in hardener.mine(artifacts, incremental=False)}, "AutoresearchHardener"
    if substrate == "leanmill":
        from ztare.leanmill.solver.leanmill_hardener import LeanmillHardener

        hardener = LeanmillHardener()
        names: set[str] = set()
        for artifact in artifacts:
            names.update(v.name for v in hardener.mine(artifact, incremental=False))
        return names, "LeanmillHardener"
    return set(), f"unsupported substrate {substrate!r}"


def _detector_finds_vector(substrate: str, vector_name: str, evidence: dict[str, Any]) -> tuple[bool, str]:
    artifacts = _artifact_paths(evidence)
    if not artifacts:
        return False, "no exposing_artifacts declared"
    found, detector_name = _mine_vectors(substrate, artifacts)
    return vector_name in found, f"{detector_name} mined {sorted(found)}"


def _require_bool(evidence: dict[str, Any], dotted_key: str, reasons: list[str]) -> None:
    cur: Any = evidence
    for part in dotted_key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            reasons.append(f"missing required evidence field: {dotted_key}")
            return
        cur = cur[part]
    if cur is not True:
        reasons.append(f"required evidence field is not true: {dotted_key}")


def _validate_judge_carrier_receipt(vector_name: str, evidence: dict[str, Any]) -> list[str]:
    receipt = evidence.get("carrier_receipt")
    if not isinstance(receipt, dict):
        return ["judge_carrier evidence requires carrier_receipt object"]
    reasons: list[str] = []
    if receipt.get("vector") != vector_name:
        reasons.append(f"carrier_receipt.vector={receipt.get('vector')!r} does not match {vector_name!r}")
    required = {
        "carrier_type": "semantic_gaming_carrier",
        "module": "ztare.gates.semantic_gaming_carrier",
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            reasons.append(f"carrier_receipt.{key} must be {expected!r}")
    for key in ("gate_name", "review_role", "fixture"):
        if not receipt.get(key):
            reasons.append(f"carrier_receipt.{key} is required")
    if receipt.get("fixture_detected") is not True:
        reasons.append("carrier_receipt.fixture_detected must be true")
    if receipt.get("good_control_passed") is not True:
        reasons.append("carrier_receipt.good_control_passed must be true")
    return reasons


def _gaming_vector_promotion_contract(base: Path, stage: StageSpec) -> ContractResult:
    substrate = str(stage.details.get("substrate") or "autoresearch")
    vector_name = str(stage.details.get("vector") or "").strip()
    expected_path = str(stage.details.get("promotion_path") or f"gaming_vector:{substrate}:{vector_name}")
    if not vector_name:
        return ContractResult("fail", ["stage has no details.vector"])

    vector = _find_vector(substrate, vector_name)
    if vector is None:
        return ContractResult("fail", [f"catalog row missing for {substrate}:{vector_name}"])
    if vector.status == "gated" or vector.already_gated_by:
        return ContractResult(
            "blocked",
            [f"{substrate}:{vector_name} is already marked gated by {vector.already_gated_by or vector.status}; no promotion needed"],
        )

    evidence, e_path = _load_evidence(base, stage)
    if evidence is None:
        return ContractResult(
            "blocked",
            [f"promotion evidence missing: {e_path}", "create evidence JSON before this vector can promote"],
        )
    if "__invalid_json__" in evidence:
        return ContractResult("fail", [f"promotion evidence invalid JSON: {evidence['__invalid_json__']}"])

    fail_reasons: list[str] = []
    blocked_reasons: list[str] = []
    pass_reasons: list[str] = []

    if evidence.get("vector") != vector_name:
        fail_reasons.append(f"evidence.vector={evidence.get('vector')!r} does not match stage vector {vector_name!r}")
    if evidence.get("substrate") != substrate:
        fail_reasons.append(f"evidence.substrate={evidence.get('substrate')!r} does not match {substrate!r}")
    if evidence.get("promotion_path") != expected_path:
        fail_reasons.append(
            f"promotion_path={evidence.get('promotion_path')!r} does not match scoped path {expected_path!r}"
        )

    hash_reasons = _check_artifact_hashes(evidence)
    fail_reasons.extend(hash_reasons)

    if evidence.get("evidence_mode") == "deterministic_detector":
        found, msg = _detector_finds_vector(substrate, vector_name, evidence)
        if found:
            pass_reasons.append(f"detector recognizes exposing artifact: {msg}")
        else:
            fail_reasons.append(f"detector does not recognize exposing artifact for {vector_name}: {msg}")
    elif evidence.get("evidence_mode") in {"config_fix", "judge_carrier"}:
        pass_reasons.append(f"evidence mode accepted: {evidence.get('evidence_mode')}")
        if evidence.get("evidence_mode") == "judge_carrier":
            fail_reasons.extend(_validate_judge_carrier_receipt(vector_name, evidence))
    else:
        blocked_reasons.append("evidence_mode must be deterministic_detector, config_fix, or judge_carrier")

    required_true_fields = [
        "runtime_enforcement.wired",
        "regression.exposing_fixture_blocked",
        "regression.good_controls_passed",
        "scope.vector_only",
        "test_result.passed",
        "promotion_recommendation",
    ]
    for field_name in required_true_fields:
        _require_bool(evidence, field_name, blocked_reasons)

    gate_name = (evidence.get("runtime_enforcement") or {}).get("name")
    if not gate_name:
        blocked_reasons.append("runtime_enforcement.name is required")

    if fail_reasons:
        return ContractResult("fail", fail_reasons + pass_reasons, {"evidence_path": e_path})
    if blocked_reasons:
        return ContractResult("blocked", pass_reasons + blocked_reasons, {"evidence_path": e_path})
    pass_reasons.append(f"promotion contract satisfied for {substrate}:{vector_name}")
    pass_reasons.append("registry may now be updated from open to gated in a separate explicit change")
    return ContractResult("pass", pass_reasons, {"evidence_path": e_path, "gate_name": gate_name})


CONTRACT_REGISTRY: dict[str, Callable[[Path, StageSpec], ContractResult]] = {
    EXPECTED_PROMOTION_CONTRACT: _gaming_vector_promotion_contract,
}


def print_status(runner: GamingVectorMetaRunner, result: ContractResult | None = None) -> None:
    print("Gaming Vector Meta-Runner")
    print(f"Project dir: {runner.project_dir}")
    print(f"Current stage index: {runner.state.current_stage}")
    print(f"Last verdict: {runner.state.last_verdict}")
    if result is not None:
        print(f"Current verdict: {result.verdict}")
        for reason in result.reasons:
            print(f"- {reason}")
    elif runner.state.last_report:
        print("Last report:")
        for reason in runner.state.last_report:
            print(f"- {reason}")
    print(f"Completed stages: {', '.join(runner.state.completed_stages) if runner.state.completed_stages else 'none'}")
    drift = plan_drift(runner.project_dir)
    if drift:
        print("Materialized plan drift:")
        for reason in drift:
            print(f"- {reason}")
    print("")
    for idx, stage in enumerate(runner.queue):
        marker = "*" if idx == runner.state.current_stage else " "
        vector = stage.details.get("vector", "?")
        substrate = stage.details.get("substrate", "?")
        print(f"{marker} stage {stage.item_number}: {stage.name} [{stage.priority}] substrate={substrate} vector={vector}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Contract-governed GP-086 gaming-vector promotion runner.")
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show", help="Show current queue and state.")
    subparsers.add_parser("check-plan", help="Fail if the board plan differs from live open registry rows.")
    subparsers.add_parser("sync-plan", help="Rewrite the board plan from live open registry rows.")
    subparsers.add_parser("run-current", help="Evaluate the current vector promotion contract.")
    run_vector = subparsers.add_parser("run-vector", help="Evaluate one vector promotion contract by substrate/vector.")
    run_vector.add_argument("substrate")
    run_vector.add_argument("vector")
    subparsers.add_parser("advance", help="Advance after a pass verdict.")
    subparsers.add_parser("reset", help="Reset state to stage 0.")
    subparsers.add_parser("selftest", help="Run local self-tests.")
    return parser


def _selftest() -> int:
    import tempfile

    fails: list[str] = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    tmp = Path(tempfile.mkdtemp())
    cat = tmp / "catalog.jsonl"
    os.environ["ZTARE_GAMING_VECTOR_CATALOG"] = str(cat)
    vector = GamingVector(
        name="definitional_tautology_self_confirming_metric",
        substrate="autoresearch",
        category="NOVEL:non_falsifiable_self_confirmation",
        mechanism="self-confirming metric",
        status="open",
    )
    cat.write_text(json.dumps(vector.to_dict()) + "\n", encoding="utf-8")
    ensure_project(tmp)
    art = tmp / "fixture.py"
    art.write_text("Z = 1\nscore = Z + 1\nassert Z > 0\nassert score > 1\n", encoding="utf-8")
    ev = {
        "vector": vector.name,
        "substrate": "autoresearch",
        "promotion_path": f"gaming_vector:autoresearch:{vector.name}",
        "evidence_mode": "deterministic_detector",
        "exposing_artifacts": [{"path": str(art), "sha": content_hash(art)}],
        "runtime_enforcement": {"name": "test_gate", "wired": True},
        "regression": {"exposing_fixture_blocked": True, "good_controls_passed": True},
        "scope": {"vector_only": True},
        "test_result": {"passed": True},
        "promotion_recommendation": True,
    }
    evidence_path(tmp, vector.name).write_text(json.dumps(ev, indent=2) + "\n", encoding="utf-8")
    stage = StageSpec(
        name="promote_test",
        item_number=1,
        priority="P0",
        contract_name=EXPECTED_PROMOTION_CONTRACT,
        details={
            "substrate": "autoresearch",
            "vector": vector.name,
            "evidence_path": f"evidence/{vector.name}.json",
            "promotion_path": f"gaming_vector:autoresearch:{vector.name}",
        },
    )
    result = _gaming_vector_promotion_contract(tmp, stage)
    ok("valid evidence passes", result.verdict == "pass")
    ev["promotion_path"] = "gaming_vector:autoresearch:wrong"
    evidence_path(tmp, vector.name).write_text(json.dumps(ev, indent=2) + "\n", encoding="utf-8")
    result = _gaming_vector_promotion_contract(tmp, stage)
    ok("wrong promotion path fails", result.verdict == "fail")

    del os.environ["ZTARE_GAMING_VECTOR_CATALOG"]
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "selftest":
        return _selftest()
    base = project_dir(args.project)
    if args.command == "sync-plan":
        sync_plan(base)
        runner = load_runner(args.project)
        print_status(runner)
        return 0
    runner = load_runner(args.project)
    if args.command == "show":
        print_status(runner)
        return 0
    if args.command == "check-plan":
        drift = plan_drift(runner.project_dir)
        if drift:
            for reason in drift:
                print(reason)
            return 1
        print("gaming vector hardening plan matches live open registry rows")
        return 0
    drift = plan_drift(runner.project_dir)
    if drift and args.command in {"advance"}:
        print("gaming vector hardening materialized plan is stale; run `sync-plan` before advancing board state")
        for reason in drift:
            print(f"- {reason}")
        return 1
    if args.command == "run-current":
        result = runner.run_stage()
        print_status(runner, result)
        return 0 if result.verdict == "pass" else 1
    if args.command == "run-vector":
        stage = StageSpec(
            name=f"promote_{args.vector}",
            item_number=0,
            priority="P0",
            contract_name=EXPECTED_PROMOTION_CONTRACT,
            details={
                "substrate": args.substrate,
                "vector": args.vector,
                "evidence_path": f"evidence/{args.vector}.json",
                "promotion_path": f"gaming_vector:{args.substrate}:{args.vector}",
            },
        )
        result = _gaming_vector_promotion_contract(runner.project_dir, stage)
        print_status(runner, result)
        return 0 if result.verdict == "pass" else 1
    if args.command == "advance":
        runner.advance()
        print_status(runner)
        return 0
    if args.command == "reset":
        runner.reset()
        print_status(runner)
        return 0
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
