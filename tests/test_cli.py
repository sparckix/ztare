# SPDX-License-Identifier: MIT
"""Smoke tests for the ``ztare`` CLI entry point.

These tests exercise the dispatch surface, not the underlying control
scripts — those have their own self-tests. The contract under test:

- help, version, unknown-command, and KeyboardInterrupt behave correctly
  and return the right POSIX exit codes;
- every registered subcommand resolves to either a callable handler
  or an existing control script on disk;
- the verb routers print their own help
  and reject unknown verbs with exit code 2;
- ``doctor`` and ``completion`` are pure (read-only, no side effects);
- adding a new subcommand to ``_SUBCOMMANDS`` requires only a one-line
  edit (this is verified structurally — every subcommand has a help
  string and a callable).

Run:
    python3 tests/test_cli.py
    # or: pytest tests/test_cli.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


# Ensure src/ is on sys.path so this runs both standalone and under pytest.
_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare import cli  # noqa: E402
from ztare.reports import autoresearch_trace  # noqa: E402


def _run(argv: list[str]) -> tuple[int, str, str]:
    """Run cli.main with captured stdout/stderr; return (rc, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = cli.main(argv)
    return rc, out.getvalue(), err.getvalue()


class HelpAndVersionTests(unittest.TestCase):
    def test_no_args_prints_help_and_returns_zero(self) -> None:
        rc, out, err = _run([])
        self.assertEqual(rc, 0)
        self.assertIn("usage: ztare", out)
        self.assertIn("forecast", out)
        self.assertIn("LeanMill governed proof search", out)
        self.assertNotIn("GP-", out)
        self.assertEqual(err, "")

    def test_help_flag_short_and_long(self) -> None:
        for flag in ("-h", "--help"):
            rc, out, _ = _run([flag])
            self.assertEqual(rc, 0)
            self.assertIn("usage: ztare", out)

    def test_version_flag_returns_zero_and_prints_version(self) -> None:
        for flag in ("-V", "--version"):
            rc, out, _ = _run([flag])
            self.assertEqual(rc, 0)
            self.assertIn("ztare ", out)
            self.assertIn("python ", out)

    def test_version_subcommand_matches_flag(self) -> None:
        rc_sub, out_sub, _ = _run(["version"])
        rc_flag, out_flag, _ = _run(["--version"])
        self.assertEqual(rc_sub, 0)
        self.assertEqual(rc_flag, 0)
        self.assertEqual(out_sub, out_flag)

    def test_checkout_version_matches_pyproject(self) -> None:
        import tomllib

        pyproject = cli._repo_root() / "pyproject.toml"
        with pyproject.open("rb") as fh:
            expected = tomllib.load(fh)["project"]["version"]

        self.assertEqual(cli._ztare_version(), expected)


class UnknownCommandTests(unittest.TestCase):
    def test_unknown_top_command_returns_two_and_prints_help_on_stderr(self) -> None:
        rc, out, err = _run(["totally_made_up_command"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown command", err)
        self.assertIn("usage: ztare", out)

    def test_unknown_leanmill_verb_returns_two(self) -> None:
        rc, _, err = _run(["leanmill", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown leanmill verb", err)

    def test_unknown_bundle_verb_returns_two(self) -> None:
        rc, _, err = _run(["bundle", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown bundle verb", err)


class VerbRouterTests(unittest.TestCase):
    def test_leanmill_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["leanmill"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare leanmill <verb>", out)
        for verb in ("schedule", "run", "andon", "triage", "backlog", "source-scout", "proof-audit", "harness"):
            self.assertIn(verb, out)

    def test_bundle_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["bundle"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare bundle <verb>", out)
        for verb in ("run", "verify"):
            self.assertIn(verb, out)

    def test_forecast_help_labels_target_kind_without_project_paths(self) -> None:
        rc, out, _ = _run(["forecast"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare forecast <verb>", out)
        self.assertIn("pool", out)
        self.assertIn("public control: scripts/public/control/forecast/pool.py", out)
        self.assertIn("capability-audit", out)
        self.assertIn("package module: python -m ztare.reports.forecast_capability_audit", out)
        self.assertIn("calibration-stats", out)
        self.assertIn("package module: python -m ztare.forecasting.calibration_stats", out)
        self.assertIn("cutoff-panel-run", out)
        self.assertIn("project tool: cutoff_stage_b_dispatch_runner.py", out)
        self.assertIn("ztare doctor", out)
        self.assertNotIn("projects/llm_forecasting_calibration_program", out)

    def test_eigenquestion_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["eigenquestion"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare eigenquestion <verb>", out)
        for verb in ("propose", "validate", "status"):
            self.assertIn(verb, out)

    def test_eigenquestion_unknown_verb_returns_two(self) -> None:
        rc, _, err = _run(["eigenquestion", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown eigenquestion verb", err)

    def test_eigenquestion_validate_delegates_to_validate_explored(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["eigenquestion", "validate", "--project", "demo_project"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(
                seen["module"],
                "src.ztare.research_director.eigenquestion_generator",
            )
            self.assertEqual(seen["args"], ["--validate-explored", "--project", "demo_project"])
        finally:
            cli._delegate_module = original

    def test_eigenquestion_status_delegates_to_preflight_script(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_script
        try:
            def _fake_delegate_script(rel_path: str, args) -> int:
                seen["rel_path"] = rel_path
                seen["args"] = list(args)
                return 0

            cli._delegate_script = _fake_delegate_script
            rc, _, err = _run([
                "eigenquestion",
                "status",
                "--project",
                "demo_project",
                "--strict",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(
                seen["rel_path"],
                "scripts/public/control/preflight_eigenquestion_review.py",
            )
            self.assertEqual(seen["args"], ["demo_project", "--strict", "--json"])
        finally:
            cli._delegate_script = original

    def test_autoresearch_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["autoresearch"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare autoresearch <verb>", out)
        self.assertIn("route inversion/review calls", out)
        self.assertNotIn("GP-119", out)
        for verb in ("run", "route", "projection", "trace", "dispatch-audit", "dispatch-canary", "dispatch-parity", "subscription-outcomes", "matched-transport-pair", "hillclimb-audit", "consequence-audit", "rubric-mode-audit", "health", "operations-intelligence", "catalog-health", "fixtures", "control-demo", "hardening", "portfolio"):
            self.assertIn(verb, out)

    def test_forensic_workbench_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["forensic-workbench"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare forensic-workbench <verb>", out)
        self.assertIn("project-state", out)
        self.assertIn("apply-review", out)
        self.assertIn("save-next-step", out)
        self.assertIn("save-action", out)
        self.assertIn("scripts/public/control/forensic_workbench_state.py", out)
        self.assertIn("scripts/public/control/forensic_workbench_review.py", out)
        self.assertIn("scripts/public/control/forensic_workbench_action.py", out)

    def test_autoresearch_run_requires_project_and_rubric(self) -> None:
        rc, _, err = _run(["autoresearch", "run"])
        self.assertEqual(rc, 2)
        self.assertIn("requires --project", err)

    def test_autoresearch_route_requires_task(self) -> None:
        rc, _, err = _run(["autoresearch", "route", "--bounded-claim"])
        self.assertEqual(rc, 2)
        self.assertIn("requires --task", err)

    def test_autoresearch_route_help_names_plan_preview(self) -> None:
        rc, out, err = _run(["autoresearch", "route", "--help"])
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        self.assertIn("plan_preview", out)
        self.assertIn("deterministic preflight command", out)
        self.assertIn("fallback policy", out)

    def test_autoresearch_trace_help_names_graph_records(self) -> None:
        rc, out, err = _run(["autoresearch", "trace", "--help"])
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        self.assertIn("graph records", out)
        self.assertIn("prediction receipts", out)
        self.assertIn("recovery commands", out)

    def test_autoresearch_health_help_names_project_trace(self) -> None:
        rc, out, err = _run(["autoresearch", "health", "--help"])
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        self.assertIn("project trace", out)
        self.assertIn("raw/source typing preflight", out)

    def test_autoresearch_route_forwards_context_to_router_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run([
                "autoresearch",
                "route",
                "--task",
                "test bounded claim",
                "--project",
                "gp_example",
                "--rubric",
                "gp_example",
                "--intake",
                "gp_example_packet.json",
                "--bounded-claim",
                "--stable-evaluator",
                "--rubric-ready",
                "--artifact-surface",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(
                seen["module"],
                "ztare.research_director.autoresearch_workbench_router",
            )
            self.assertEqual(seen["args"][0], "test bounded claim")
            self.assertIn("--project", seen["args"])
            self.assertIn("gp_example", seen["args"])
            self.assertIn("--rubric", seen["args"])
            self.assertIn("--intake", seen["args"])
            self.assertIn("gp_example_packet.json", seen["args"])
            self.assertIn("--bounded-claim", seen["args"])
        finally:
            cli._delegate_module = original

    def test_autoresearch_route_can_record_action_intelligence_row(self) -> None:
        original = cli._load_action_intelligence_module
        written_rows: list[list[dict[str, object]]] = []

        class _FakeActionIntel:
            ACTION_IMPACT_LEDGER = Path("/tmp/fake_action_impact.jsonl")

            @staticmethod
            def agentic_workbench_impact_from_route_args(ns) -> dict[str, object]:
                route = json.loads(Path(ns.route_json).read_text(encoding="utf-8"))
                return {
                    "action_impact_id": "ai_route_fixture",
                    "decision_point": {
                        "decision_id": ns.decision_id,
                        "domain": "agentic_workbench",
                    },
                    "selected_action": ns.selected_action or "invoke_autoresearch",
                    "context_features": {
                        "workbench_router_decision": route["decision"],
                        "why_not_autoresearch": ns.why_not_autoresearch,
                    },
                    "source_refs": {"source_refs": [str(ns.route_json)]},
                }

            @staticmethod
            def read_jsonl(_path) -> list[dict[str, object]]:
                return []

            @staticmethod
            def write_jsonl(_path, rows: list[dict[str, object]]) -> None:
                written_rows.append(rows)

        try:
            cli._load_action_intelligence_module = lambda: _FakeActionIntel
            with tempfile.TemporaryDirectory() as td:
                route_path = Path(td) / "route.json"
                rc, out, err = _run([
                    "autoresearch",
                    "route",
                    "--task",
                    "test bounded claim",
                    "--project",
                    "gp_example",
                    "--rubric",
                    "gp_example",
                    "--bounded-claim",
                    "--stable-evaluator",
                    "--rubric-ready",
                    "--artifact-surface",
                    "--record-decision-id",
                    "decision_fixture",
                    "--route-json-out",
                    str(route_path),
                    "--selected-action",
                    "invoke_autoresearch",
                ])
                self.assertEqual(rc, 0)
                self.assertEqual(err, "")
                payload = json.loads(out)
                self.assertEqual(payload["route"]["decision"], "invoke_autoresearch")
                self.assertEqual(
                    payload["route"]["worker_metadata"]["worker_capability"],
                    "bare_llm_call",
                )
                self.assertEqual(
                    payload["route"]["worker_metadata"]["worker_state"],
                    "stateless_externalized_briefing",
                )
                plan_preview = payload["route"]["plan_preview"]
                self.assertEqual(
                    plan_preview["schema"],
                    "ztare-autoresearch-plan-preview-v1",
                )
                self.assertEqual(plan_preview["status"], "ready_for_preflight")
                self.assertIs(plan_preview["model_calls_before_confirmation"], False)
                self.assertEqual(
                    plan_preview["recommended_first_command"],
                    "ztare autoresearch run --project gp_example --rubric gp_example "
                    "--preflight-only",
                )
                self.assertEqual(
                    plan_preview["budget"]["model_fallback_policy"],
                    "disabled_by_default",
                )
                self.assertLess(
                    [step["id"] for step in plan_preview["dependency_order"]].index(
                        "preflight_only"
                    ),
                    [step["id"] for step in plan_preview["dependency_order"]].index(
                        "bounded_loop_run"
                    ),
                )
                self.assertTrue(
                    any(
                        route["card_id"] == "OP-AWR-01"
                        for route in payload["route"]["operator_card_routes"]
                    )
                )
                self.assertEqual(payload["action_impact"]["action_impact_id"], "ai_route_fixture")
                self.assertTrue(route_path.exists())
                self.assertEqual(len(written_rows), 1)
                self.assertEqual(written_rows[0][0]["decision_point"]["decision_id"], "decision_fixture")
        finally:
            cli._load_action_intelligence_module = original

    def test_autoresearch_route_can_queue_missing_surface_prep(self) -> None:
        original = cli._load_action_intelligence_module
        written_rows: list[list[dict[str, object]]] = []

        class _FakeActionIntel:
            ACTION_IMPACT_LEDGER = Path("/tmp/fake_action_impact.jsonl")

            @staticmethod
            def agentic_workbench_impact_from_route_args(ns) -> dict[str, object]:
                route = json.loads(Path(ns.route_json).read_text(encoding="utf-8"))
                return {
                    "action_impact_id": "ai_route_prepare_fixture",
                    "decision_point": {
                        "decision_id": ns.decision_id,
                        "domain": "agentic_workbench",
                    },
                    "selected_action": ns.selected_action or route["decision"],
                    "context_features": {
                        "workbench_router_decision": route["decision"],
                    },
                    "source_refs": {"source_refs": [str(ns.route_json)]},
                }

            @staticmethod
            def read_jsonl(_path) -> list[dict[str, object]]:
                return []

            @staticmethod
            def write_jsonl(_path, rows: list[dict[str, object]]) -> None:
                written_rows.append(rows)

        try:
            cli._load_action_intelligence_module = lambda: _FakeActionIntel
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                route_path = root / "route.json"
                queue_dir = root / "queue"
                rc, out, err = _run([
                    "autoresearch",
                    "route",
                    "--task",
                    "test bounded claim missing artifact",
                    "--bounded-claim",
                    "--stable-evaluator",
                    "--rubric-ready",
                    "--no-artifact-surface",
                    "--record-decision-id",
                    "decision_prepare_fixture",
                    "--route-json-out",
                    str(route_path),
                    "--queue-missing-surface",
                    "--queue-dir",
                    str(queue_dir),
                ])
                self.assertEqual(rc, 0)
                self.assertEqual(err, "")
                payload = json.loads(out)
                self.assertEqual(payload["route"]["decision"], "prepare_autoresearch_surface")
                self.assertEqual(payload["action_impact"]["action_impact_id"], "ai_route_prepare_fixture")
                queued = payload["queued_surface_prep"]
                self.assertEqual(len(queued), 1)
                self.assertEqual(queued[0]["source_action_impact_id"], "ai_route_prepare_fixture")
                self.assertEqual(queued[0]["decision_id"], "decision_prepare_fixture")
                self.assertEqual(queued[0]["requested_artifact"], "current_iteration.md or thesis.md")
                self.assertTrue((queue_dir / "pending.jsonl").exists())
                self.assertEqual(len(written_rows), 1)
        finally:
            cli._load_action_intelligence_module = original

    def test_autoresearch_route_record_blocks_stale_trace_sources(self) -> None:
        original_action_intel = cli._load_action_intelligence_module
        original_repo_root = cli._repo_root
        written_rows: list[list[dict[str, object]]] = []

        class _FakeActionIntel:
            ACTION_IMPACT_LEDGER = Path("/tmp/fake_action_impact.jsonl")

            @staticmethod
            def agentic_workbench_impact_from_route_args(ns) -> dict[str, object]:
                route = json.loads(Path(ns.route_json).read_text(encoding="utf-8"))
                return {
                    "action_impact_id": "ai_route_stale_trace_fixture",
                    "decision_point": {
                        "decision_id": ns.decision_id,
                        "domain": "agentic_workbench",
                    },
                    "selected_action": ns.selected_action or route["decision"],
                    "context_features": {
                        "workbench_router_decision": route["decision"],
                    },
                    "source_refs": {"source_refs": [str(ns.route_json)]},
                }

            @staticmethod
            def read_jsonl(_path) -> list[dict[str, object]]:
                return []

            @staticmethod
            def write_jsonl(_path, rows: list[dict[str, object]]) -> None:
                written_rows.append(rows)

        try:
            cli._load_action_intelligence_module = lambda: _FakeActionIntel
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                cli._repo_root = lambda: root
                project = root / "projects" / "stale_trace"
                workspace = project / "workspace"
                raw = project / "raw"
                rubric_dir = root / "rubrics"
                raw.mkdir(parents=True)
                workspace.mkdir()
                rubric_dir.mkdir()
                (project / "project_charter.md").write_text("charter\n", encoding="utf-8")
                (project / "thesis.md").write_text("claim\n", encoding="utf-8")
                (project / "test_model.py").write_text(
                    "def test_smoke(): pass\n",
                    encoding="utf-8",
                )
                (raw / "source.md").write_text(
                    "---\nsource_type: source_evidence\n---\ncurrent source\n",
                    encoding="utf-8",
                )
                (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
                stale_source = {
                    "source_id": "S001",
                    "path": "source.md",
                    "source_type": "source_evidence",
                    "sha256": "0" * 64,
                }
                (workspace / "workspace_meta.json").write_text(
                    json.dumps({"merge_status": "success", "source_count": 1}) + "\n",
                    encoding="utf-8",
                )
                (workspace / "source_index.json").write_text(
                    json.dumps({"sources": [stale_source]}) + "\n",
                    encoding="utf-8",
                )
                (project / "compiled_evidence_provenance.json").write_text(
                    json.dumps({"source_count": 1, "sources": [stale_source]}) + "\n",
                    encoding="utf-8",
                )
                (rubric_dir / "stale_trace.json").write_text(
                    json.dumps(
                        {
                            "dimensions": [
                                {"name": "Fit", "weight": 100, "description": "score fit"}
                            ]
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                route_path = root / "route.json"

                rc, out, err = _run([
                    "autoresearch",
                    "route",
                    "--task",
                    "test stale trace boundary",
                    "--project",
                    "stale_trace",
                    "--rubric",
                    "stale_trace",
                    "--record-decision-id",
                    "decision_stale_trace",
                    "--route-json-out",
                    str(route_path),
                ])

                self.assertEqual(rc, 0)
                self.assertEqual(err, "")
                payload = json.loads(out)
                self.assertEqual(payload["route"]["decision"], "prepare_autoresearch_surface")
                self.assertIn(
                    "autoresearch trace blocks run readiness: source_index_stale",
                    payload["route"]["source_contract_errors"],
                )
                self.assertIn(
                    "autoresearch trace blocks run readiness: evidence_compile_stale",
                    payload["route"]["source_contract_errors"],
                )
                self.assertTrue(route_path.exists())
                self.assertEqual(len(written_rows), 1)
        finally:
            cli._load_action_intelligence_module = original_action_intel
            cli._repo_root = original_repo_root

    def test_autoresearch_route_record_blocks_packet_contract_failures(self) -> None:
        original_action_intel = cli._load_action_intelligence_module
        original_repo_root = cli._repo_root
        original_trace = autoresearch_trace.build_autoresearch_trace
        written_rows: list[list[dict[str, object]]] = []

        class _FakeActionIntel:
            ACTION_IMPACT_LEDGER = Path("/tmp/fake_action_impact.jsonl")

            @staticmethod
            def agentic_workbench_impact_from_route_args(ns) -> dict[str, object]:
                route = json.loads(Path(ns.route_json).read_text(encoding="utf-8"))
                return {
                    "action_impact_id": "ai_route_packet_block_fixture",
                    "decision_point": {
                        "decision_id": ns.decision_id,
                        "domain": "agentic_workbench",
                    },
                    "selected_action": ns.selected_action or route["decision"],
                    "context_features": {
                        "workbench_router_decision": route["decision"],
                    },
                    "source_refs": {"source_refs": [str(ns.route_json)]},
                }

            @staticmethod
            def read_jsonl(_path) -> list[dict[str, object]]:
                return []

            @staticmethod
            def write_jsonl(_path, rows: list[dict[str, object]]) -> None:
                written_rows.append(rows)

        def _blocked_trace(**kwargs):
            self.assertEqual(kwargs["project"], "packet_block")
            self.assertEqual(kwargs["rubric"], "packet_block")
            self.assertEqual(kwargs["packet"], "packet_block.json")
            return {
                "readiness": "blocked_on_project_packet",
                "readiness_canonical": "blocked_on_project_intake",
                "blocking_missing": ["project_packet"],
                "recovery_actions": [],
                "kernel_entry": {
                    "can_enter_kernel": False,
                    "readiness": "blocked_on_project_packet",
                    "readiness_canonical": "blocked_on_project_intake",
                    "blockers": [
                        {
                            "id": "project_packet",
                            "canonical_id": "project_intake",
                            "recovery_channel": "project_packet",
                            "canonical_recovery_channel": "project_intake",
                            "next_command": (
                                "ztare project intake validate --path packet_block.json"
                            ),
                        }
                    ],
                },
            }

        try:
            cli._load_action_intelligence_module = lambda: _FakeActionIntel
            autoresearch_trace.build_autoresearch_trace = _blocked_trace
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                cli._repo_root = lambda: root
                route_path = root / "route.json"
                rc, out, err = _run([
                    "autoresearch",
                    "route",
                    "--task",
                    "test packet boundary",
                    "--project",
                    "packet_block",
                    "--rubric",
                    "packet_block",
                    "--packet",
                    "packet_block.json",
                    "--record-decision-id",
                    "decision_packet_block",
                    "--route-json-out",
                    str(route_path),
                ])

                self.assertEqual(rc, 0)
                self.assertEqual(err, "")
                payload = json.loads(out)
                self.assertEqual(payload["route"]["decision"], "prepare_autoresearch_surface")
                self.assertIn(
                    "autoresearch trace blocks run readiness: project_packet",
                    payload["route"]["source_contract_errors"],
                )
                self.assertIn(
                    (
                        "autoresearch run-readiness recovery[project_packet]: "
                        "ztare project intake validate --path packet_block.json"
                    ),
                    payload["route"]["source_contract_errors"],
                )
                self.assertEqual(
                    payload["action_impact"]["context_features"]["workbench_router_decision"],
                    "prepare_autoresearch_surface",
                )
                self.assertTrue(route_path.exists())
                self.assertEqual(len(written_rows), 1)
        finally:
            cli._load_action_intelligence_module = original_action_intel
            cli._repo_root = original_repo_root
            autoresearch_trace.build_autoresearch_trace = original_trace

    def test_autoresearch_route_queue_missing_surface_rejects_ready_route(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            route_path = Path(td) / "route.json"
            rc, _, err = _run([
                "autoresearch",
                "route",
                "--task",
                "test bounded claim",
                "--bounded-claim",
                "--stable-evaluator",
                "--rubric-ready",
                "--artifact-surface",
                "--record-decision-id",
                "decision_ready_fixture",
                "--route-json-out",
                str(route_path),
                "--queue-missing-surface",
            ])
            self.assertEqual(rc, 2)
            self.assertIn("only applies when the router returns prepare_autoresearch_surface", err)

    def test_autoresearch_run_forwards_agent_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "run",
                "--project",
                "gp_example",
                "--rubric",
                "gp_example",
                "--agent-mutator",
                "--agent-judge",
                "--agent-inverter",
                "--agent-runtime",
                "codex",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "experiment-loop")
            vars_ = seen["vars"]
            self.assertEqual(vars_["AGENT_MUTATOR"], "1")
            self.assertEqual(vars_["AGENT_JUDGE"], "1")
            self.assertEqual(vars_["AGENT_COMMITTEE"], "")
            self.assertEqual(vars_["AGENT_INVERTER"], "1")
            self.assertEqual(vars_["AGENT_RUNTIME"], "codex")
        finally:
            cli._delegate_make = original

    def test_autoresearch_run_forwards_preflight_only_make_flag(self) -> None:
        seen: dict[str, object] = {}
        original_delegate = cli._delegate_make
        original_blocker = cli._autoresearch_run_packet_blocker
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            cli._autoresearch_run_packet_blocker = lambda **_kwargs: None
            rc, _, err = _run([
                "autoresearch",
                "run",
                "--project",
                "gp_example",
                "--rubric",
                "gp_example",
                "--intake",
                "gp_example_packet.json",
                "--preflight-only",
            ])

            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "experiment-loop")
            vars_ = seen["vars"]
            self.assertEqual(vars_["INTAKE"], "gp_example_packet.json")
            self.assertEqual(vars_["PREFLIGHT_ONLY"], "1")
        finally:
            cli._delegate_make = original_delegate
            cli._autoresearch_run_packet_blocker = original_blocker

    def test_autoresearch_run_rejects_conflicting_intake_aliases(self) -> None:
        rc, _, err = _run([
            "autoresearch",
            "run",
            "--project",
            "gp_example",
            "--rubric",
            "gp_example",
            "--intake",
            "one.json",
            "--packet",
            "two.json",
        ])

        self.assertEqual(rc, 2)
        self.assertIn("use either --intake or --packet", err)

    def test_autoresearch_run_inherits_packet_run_defaults_when_flags_omitted(self) -> None:
        seen: dict[str, object] = {}
        original_delegate = cli._delegate_make
        original_blocker = cli._autoresearch_run_packet_blocker
        original_repo_root = cli._repo_root
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                packet_path = root / "packet.json"
                packet_path.write_text(
                    json.dumps({
                        "expected_command": (
                            "ztare autoresearch run --project gp_example "
                            "--rubric gp_example --iters 3 --mutator kimi --judge grok"
                        ),
                    }),
                    encoding="utf-8",
                )

                cli._repo_root = lambda: root
                cli._delegate_make = _fake_delegate_make
                cli._autoresearch_run_packet_blocker = lambda **_kwargs: None
                rc, _, err = _run([
                    "autoresearch",
                    "run",
                    "--project",
                    "gp_example",
                    "--rubric",
                    "gp_example",
                    "--packet",
                    "packet.json",
                    "--preflight-only",
                ])

            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "experiment-loop")
            vars_ = seen["vars"]
            self.assertEqual(vars_["ITERS"], "3")
            self.assertEqual(vars_["MUTATOR_MODEL"], "kimi")
            self.assertEqual(vars_["JUDGE_MODEL"], "grok")
            self.assertEqual(vars_["PREFLIGHT_ONLY"], "1")
        finally:
            cli._delegate_make = original_delegate
            cli._autoresearch_run_packet_blocker = original_blocker
            cli._repo_root = original_repo_root

    def test_autoresearch_run_explicit_flags_override_packet_run_defaults(self) -> None:
        seen: dict[str, object] = {}
        original_delegate = cli._delegate_make
        original_blocker = cli._autoresearch_run_packet_blocker
        original_repo_root = cli._repo_root
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                packet_path = root / "packet.json"
                packet_path.write_text(
                    json.dumps({
                        "expected_command": (
                            "ztare autoresearch run --project gp_example "
                            "--rubric gp_example --iters 3 --mutator kimi --judge grok"
                        ),
                    }),
                    encoding="utf-8",
                )

                cli._repo_root = lambda: root
                cli._delegate_make = _fake_delegate_make
                cli._autoresearch_run_packet_blocker = lambda **_kwargs: None
                rc, _, err = _run([
                    "autoresearch",
                    "run",
                    "--project",
                    "gp_example",
                    "--rubric",
                    "gp_example",
                    "--packet",
                    "packet.json",
                    "--iters",
                    "1",
                    "--mutator",
                    "deepseek",
                    "--judge",
                    "gpt4.1",
                ])

            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "experiment-loop")
            vars_ = seen["vars"]
            self.assertEqual(vars_["ITERS"], "1")
            self.assertEqual(vars_["MUTATOR_MODEL"], "deepseek")
            self.assertEqual(vars_["JUDGE_MODEL"], "gpt4.1")
            self.assertEqual(vars_["MODEL_FALLBACK"], "")
        finally:
            cli._delegate_make = original_delegate
            cli._autoresearch_run_packet_blocker = original_blocker
            cli._repo_root = original_repo_root

    def test_autoresearch_run_model_fallback_is_explicit_opt_in(self) -> None:
        seen: dict[str, object] = {}
        original_delegate = cli._delegate_make
        original_blocker = cli._autoresearch_run_packet_blocker
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            cli._autoresearch_run_packet_blocker = lambda **_kwargs: None
            rc, _, err = _run([
                "autoresearch",
                "run",
                "--project",
                "gp_example",
                "--rubric",
                "gp_example",
                "--allow-model-fallback",
            ])

            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "experiment-loop")
            self.assertEqual(seen["vars"]["MODEL_FALLBACK"], "1")
        finally:
            cli._delegate_make = original_delegate
            cli._autoresearch_run_packet_blocker = original_blocker

    def test_autoresearch_run_with_packet_blocks_before_make_when_contract_fails(self) -> None:
        original_delegate = cli._delegate_make
        original_blocker = cli._autoresearch_run_packet_blocker
        calls: list[str] = []
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                calls.append(target)
                return 0

            def _fake_blocker(*, project: str, rubric: str, packet: str) -> str | None:
                self.assertEqual(project, "gp_example")
                self.assertEqual(rubric, "gp_example")
                self.assertEqual(packet, "gp_example_packet.json")
                return (
                    "ztare: `autoresearch run --intake` blocked by run-readiness contract\n"
                    "blockers:\n"
                    "  - project_packet (project_packet)"
                )

            cli._delegate_make = _fake_delegate_make
            cli._autoresearch_run_packet_blocker = _fake_blocker
            rc, _, err = _run([
                "autoresearch",
                "run",
                "--project",
                "gp_example",
                "--rubric",
                "gp_example",
                "--intake",
                "gp_example_packet.json",
            ])

            self.assertEqual(rc, 2)
            self.assertIn("blocked by run-readiness contract", err)
            self.assertEqual(calls, [])
        finally:
            cli._delegate_make = original_delegate
            cli._autoresearch_run_packet_blocker = original_blocker

    def test_autoresearch_run_packet_blocker_surfaces_new_kernel_blockers(self) -> None:
        original_trace = autoresearch_trace.build_autoresearch_trace
        try:
            def _fake_trace(**kwargs):
                self.assertEqual(kwargs["project"], "gp_example")
                self.assertEqual(kwargs["rubric"], "gp_example")
                self.assertEqual(kwargs["packet"], "gp_example_packet.json")
                return {
                    "readiness": "blocked_on_project_surfaces",
                    "blocking_missing": [
                        "source_index_receipt_stale",
                        "evidence_output_stale",
                    ],
                    "kernel_entry": {
                        "readiness": "blocked_on_project_surfaces",
                        "can_enter_kernel": False,
                        "blockers": [
                            {
                                "id": "source_index_receipt_stale",
                                "recovery_channel": "project_surface",
                                "next_command": (
                                    "ztare project source-index --project gp_example"
                                ),
                            },
                            {
                                "id": "evidence_output_stale",
                                "recovery_channel": "evidence_prepare",
                                "next_command": (
                                    "make evidence-prepare PROJECT=gp_example MODEL=gemini"
                                ),
                            },
                        ],
                    },
                }

            autoresearch_trace.build_autoresearch_trace = _fake_trace
            blocked = cli._autoresearch_run_packet_blocker(
                project="gp_example",
                rubric="gp_example",
                packet="gp_example_packet.json",
            )

            self.assertIsNotNone(blocked)
            assert blocked is not None
            self.assertIn("source_index_receipt_stale (project_surface)", blocked)
            self.assertIn("ztare project source-index --project gp_example", blocked)
            self.assertIn("evidence_output_stale (evidence_prepare)", blocked)
            self.assertIn("make evidence-prepare PROJECT=gp_example MODEL=gemini", blocked)
        finally:
            autoresearch_trace.build_autoresearch_trace = original_trace

    def test_autoresearch_run_with_packet_delegates_when_contract_passes(self) -> None:
        seen: dict[str, object] = {}
        original_delegate = cli._delegate_make
        original_blocker = cli._autoresearch_run_packet_blocker
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            cli._autoresearch_run_packet_blocker = lambda **_kwargs: None
            rc, _, err = _run([
                "autoresearch",
                "run",
                "--project",
                "gp_example",
                "--rubric",
                "gp_example",
                "--packet",
                "gp_example_packet.json",
                "--iters",
                "3",
                "--inverter",
                "kimi",
            ])

            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "experiment-loop")
            self.assertEqual(seen["vars"]["PROJECT"], "gp_example")
            self.assertEqual(seen["vars"]["RUBRIC"], "gp_example")
            self.assertEqual(seen["vars"]["ITERS"], "3")
            self.assertEqual(seen["vars"]["INVERTER_MODEL"], "kimi")
            self.assertEqual(seen["vars"]["INTAKE"], "gp_example_packet.json")
        finally:
            cli._delegate_make = original_delegate
            cli._autoresearch_run_packet_blocker = original_blocker

    def test_autoresearch_run_uses_packet_inverter_default(self) -> None:
        seen: dict[str, object] = {}
        original_delegate = cli._delegate_make
        original_blocker = cli._autoresearch_run_packet_blocker
        original_repo_root = cli._repo_root
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            cli._autoresearch_run_packet_blocker = lambda **_kwargs: None
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                cli._repo_root = lambda: root
                packet_path = root / "packet.json"
                packet_path.write_text(
                    json.dumps(
                        {
                            "expected_command": (
                                "ztare autoresearch run --project gp_example "
                                "--rubric gp_example --iters 2 --mutator kimi "
                                "--judge grok --inverter grok "
                                "--llm-timeout-seconds 240 --llm-retries 1"
                            )
                        }
                    ),
                    encoding="utf-8",
                )
                rc, _, err = _run([
                    "autoresearch",
                    "run",
                    "--project",
                    "gp_example",
                    "--rubric",
                    "gp_example",
                    "--packet",
                    "packet.json",
                ])

            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "experiment-loop")
            self.assertEqual(seen["vars"]["ITERS"], "2")
            self.assertEqual(seen["vars"]["MUTATOR_MODEL"], "kimi")
            self.assertEqual(seen["vars"]["JUDGE_MODEL"], "grok")
            self.assertEqual(seen["vars"]["INVERTER_MODEL"], "grok")
            self.assertEqual(seen["vars"]["AUTORESEARCH_LLM_TIMEOUT"], "240")
            self.assertEqual(seen["vars"]["AUTORESEARCH_LLM_RETRIES"], "1")
        finally:
            cli._delegate_make = original_delegate
            cli._autoresearch_run_packet_blocker = original_blocker
            cli._repo_root = original_repo_root

    def test_autoresearch_run_packet_blocker_accepts_ready_public_fixture(self) -> None:
        blocker = cli._autoresearch_run_packet_blocker(
            project="demo_claims",
            rubric="demo_claims",
            packet="examples/project_packets/ready_demo_claims_packet.json",
        )

        self.assertIsNone(blocker)

    def test_autoresearch_run_packet_blocker_rejects_malformed_public_fixture(self) -> None:
        blocker = cli._autoresearch_run_packet_blocker(
            project="demo_claims",
            rubric="demo_claims",
            packet="examples/project_packets/malformed_missing_evidence_packet.json",
        )

        self.assertIsNotNone(blocker)
        assert blocker is not None
        self.assertIn("blocked by run-readiness contract", blocker)
        self.assertIn("readiness: blocked_on_project_intake", blocker)
        self.assertIn("project_intake (project_intake)", blocker)

    def test_cli_autoresearch_record_path_uses_package_stable_imports(self) -> None:
        source = (_SRC / "ztare" / "cli.py").read_text(encoding="utf-8")

        self.assertNotIn("from ztare.research_director", source)
        self.assertNotIn("from src.ztare.research_director", source)
        self.assertIn(
            'importlib.import_module(\n                "ztare.research_director.autoresearch_workbench_router"',
            source,
        )

    def test_autoresearch_dispatch_audit_forwards_json_flag(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run(["autoresearch", "dispatch-audit", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-dispatch-validate")
            self.assertEqual(seen["vars"], {"JSON": "1"})
        finally:
            cli._delegate_make = original

    def test_autoresearch_dispatch_canary_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "dispatch-canary",
                "--call-site",
                "judge",
                "--contract",
                "mutator",
                "--runtime",
                "claude",
                "--timeout-seconds",
                "30",
                "--live",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-dispatch-canary")
            self.assertEqual(
                seen["vars"],
                {
                    "DISPATCH_CALL_SITE": "judge",
                    "CONTRACT": "mutator",
                    "AGENT_RUNTIME": "claude",
                    "AGENT_TIMEOUT": "30",
                    "LIVE": "1",
                    "FULL_AUTO": "",
                    "JSON": "1",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_dispatch_parity_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "dispatch-parity",
                "--contracts",
                "text,judge",
                "--runtime",
                "claude",
                "--timeout-seconds",
                "45",
                "--live",
                "--full-auto",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-dispatch-parity")
            self.assertEqual(
                seen["vars"],
                {
                    "CONTRACTS": "text,judge",
                    "AGENT_RUNTIME": "claude",
                    "AGENT_TIMEOUT": "45",
                    "LIVE": "1",
                    "FULL_AUTO": "1",
                    "JSON": "1",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_leaf_help_does_not_delegate(self) -> None:
        calls: list[str] = []
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                calls.append(target)
                return 0

            cli._delegate_make = _fake_delegate_make
            cases = [
                (["autoresearch", "run", "--help"], "ztare autoresearch run"),
                (["autoresearch", "dispatch-parity", "--help"], "ztare autoresearch dispatch-parity"),
                (["autoresearch", "portfolio", "--help"], "ztare autoresearch portfolio"),
            ]
            for argv, expected in cases:
                rc, out, err = _run(argv)
                self.assertEqual(rc, 0)
                self.assertEqual(err, "")
                self.assertIn(expected, out)
            self.assertEqual(calls, [])
        finally:
            cli._delegate_make = original

    def test_autoresearch_trace_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, err = _run([
                "autoresearch",
                "trace",
                "--project",
                "demo_project",
                "--rubric",
                "demo_project",
                "--intake",
                "demo_project_packet.json",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "autoresearch-trace")
            self.assertEqual(
                seen["vars"],
                {
                    "PROJECT": "demo_project",
                    "RUBRIC": "demo_project",
                    "INTAKE": "demo_project_packet.json",
                    "MODEL": "",
                    "EVIDENCE_SEARCH_BACKEND": "",
                    "FULL_HEALTH": "",
                    "BRIEF": "",
                    "JSON": "1",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_trace_forwards_model_for_recovery_commands(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, err = _run([
                "autoresearch",
                "trace",
                "--project",
                "demo_project",
                "--model",
                "deepseek",
                "--evidence-search-backend",
                "openai",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "autoresearch-trace")
            self.assertEqual(
                seen["vars"],
                {
                    "PROJECT": "demo_project",
                    "RUBRIC": "",
                    "INTAKE": "",
                    "MODEL": "deepseek",
                    "EVIDENCE_SEARCH_BACKEND": "openai",
                    "FULL_HEALTH": "",
                    "BRIEF": "",
                    "JSON": "",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_trace_forwards_full_health_flag(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, err = _run([
                "autoresearch",
                "trace",
                "--project",
                "demo_project",
                "--full-health",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "autoresearch-trace")
            self.assertEqual(seen["vars"]["FULL_HEALTH"], "1")
        finally:
            cli._delegate_make = original

    def test_autoresearch_subscription_outcomes_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "subscription-outcomes",
                "--project",
                "gp_example",
                "--min-rows",
                "2",
                "--plan-limit",
                "7",
                "--strict",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-subscription-outcome-audit")
            self.assertEqual(
                seen["vars"],
                {
                    "PROJECT": "gp_example",
                    "MIN_ROWS": "2",
                    "PLAN_LIMIT": "7",
                    "STRICT": "1",
                    "JSON": "1",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_matched_transport_pair_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, err = _run([
                "autoresearch",
                "matched-transport-pair",
                "--project",
                "gp140_ztare_discovery",
                "--rubric",
                "gp140_ztare_discovery",
                "--intake",
                "projects/gp140_ztare_discovery/packet.json",
                "--iters",
                "1",
                "--mutator",
                "kimi",
                "--judge",
                "grok",
                "--inverter",
                "deepseek",
                "--llm-timeout-seconds",
                "240",
                "--llm-retries",
                "1",
                "--pair-id",
                "pair_fixture",
                "--agent-runtime",
                "codex",
                "--agent-timeout",
                "300",
                "--model-fallback",
                "--run",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "autoresearch-matched-transport-pair")
            self.assertEqual(
                seen["vars"],
                {
                    "PROJECT": "gp140_ztare_discovery",
                    "RUBRIC": "gp140_ztare_discovery",
                    "INTAKE": "projects/gp140_ztare_discovery/packet.json",
                    "ITERS": "1",
                    "MUTATOR_MODEL": "kimi",
                    "JUDGE_MODEL": "grok",
                    "INVERTER_MODEL": "deepseek",
                    "AUTORESEARCH_LLM_TIMEOUT": "240",
                    "AUTORESEARCH_LLM_RETRIES": "1",
                    "MODEL_FALLBACK": "1",
                    "MATCHED_RUN_ID": "pair_fixture",
                    "AGENT_RUNTIME": "codex",
                    "AGENT_TIMEOUT": "300",
                    "RUN_MATCHED_PAIR": "1",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_hillclimb_audit_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "hillclimb-audit",
                "--project",
                "gp_example",
                "--stagnation-threshold",
                "3",
                "--limit",
                "10",
                "--recovery-queue",
                "--recovery-limit",
                "5",
                "--recovery-intake-status",
                "ready",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-hillclimb-audit")
            self.assertEqual(
                seen["vars"],
                {
                    "PROJECT": "gp_example",
                    "STAGNATION_THRESHOLD": "3",
                    "LIMIT": "10",
                    "RECOVERY_QUEUE": "1",
                    "RECOVERY_LIMIT": "5",
                    "RECOVERY_INTAKE_STATUS": "ready",
                    "JSON": "1",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_hillclimb_resolution_uses_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            args = [
                "autoresearch",
                "hillclimb-audit",
                "--record-resolution",
                "--workspace",
                "projects/demo/workspace",
                "--run-id",
                "run-a",
                "--iteration",
                "2",
                "--last-control-iteration",
                "2",
                "--outcome-status",
                "control_fired_without_followup",
                "--resolution-status",
                "reason_recorded",
                "--reason",
                "end-of-run control",
                "--json",
            ]
            rc, _, _ = _run(args)
            self.assertEqual(rc, 0)
            self.assertEqual(
                seen["module"],
                "ztare.reports.hill_climb_behavior_audit",
            )
            self.assertEqual(seen["args"], args[2:])
        finally:
            cli._delegate_module = original

    def test_autoresearch_catalog_health_forwards_json_flag(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run(["autoresearch", "catalog-health", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "primitive-catalog-health")
            self.assertEqual(seen["vars"], {"JSON": "1"})
        finally:
            cli._delegate_make = original

    def test_autoresearch_consequence_audit_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "consequence-audit",
                "--project",
                "gp_example",
                "--workspace",
                "projects/gp_example/workspace",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-consequence-audit")
            self.assertEqual(
                seen["vars"],
                {
                    "PROJECT": "gp_example",
                    "WORKSPACE": "projects/gp_example/workspace",
                    "JSON": "1",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_rubric_mode_audit_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "rubric-mode-audit",
                "--rubric",
                "rubrics/gp_example.json",
                "--limit",
                "5",
                "--freshness-days",
                "14",
                "--strict",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-rubric-mode-audit")
            self.assertEqual(
                seen["vars"],
                {
                    "RUBRIC": "rubrics/gp_example.json",
                    "LIMIT": "5",
                    "FRESHNESS_DAYS": "14",
                    "STRICT": "1",
                    "JSON": "1",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_fixtures_forwards_json_flag(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run(["autoresearch", "fixtures", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "inloop-fixture-validate")
            self.assertEqual(seen["vars"], {"JSON": "1"})
        finally:
            cli._delegate_make = original

    def test_autoresearch_control_demo_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "control-demo",
                "--project",
                "demo_controls",
                "--force",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-control-demo")
            self.assertEqual(
                seen["vars"],
                {"PROJECT": "demo_controls", "FORCE": "1", "JSON": "1"},
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_health_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "health",
                "--project",
                "gp_example",
                "--workspace",
                "projects/gp_example/workspace",
                "--rubric",
                "rubrics/gp_example.json",
                "--packet",
                "gp_example_packet.json",
                "--stagnation-threshold",
                "3",
                "--strict",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-kernel-health")
            self.assertEqual(
                seen["vars"],
                {
                    "PROJECT": "gp_example",
                    "WORKSPACE": "projects/gp_example/workspace",
                    "RUBRIC": "rubrics/gp_example.json",
                    "INTAKE": "gp_example_packet.json",
                    "STAGNATION_THRESHOLD": "3",
                    "STRICT": "1",
                    "JSON": "1",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_operations_intelligence_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "operations-intelligence",
                "--out",
                "/tmp/ops.json",
                "--markdown",
                "/tmp/ops.md",
                "--html",
                "/tmp/ops.html",
                "--freshness-days",
                "21",
                "--max-projects",
                "9",
                "--no-markdown",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "operations-intelligence")
            self.assertEqual(
                seen["vars"],
                {
                    "OUT": "/tmp/ops.json",
                    "MD_OUT": "/tmp/ops.md",
                    "HTML_OUT": "/tmp/ops.html",
                    "FRESHNESS_DAYS": "21",
                    "MAX_PROJECTS": "9",
                    "NO_MARKDOWN": "1",
                    "JSON": "",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_operations_intelligence_forwards_json_flag(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "operations-intelligence",
                "--json",
                "--no-markdown",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "operations-intelligence")
            self.assertEqual(seen["vars"]["JSON"], "1")
            self.assertEqual(seen["vars"]["NO_MARKDOWN"], "1")
        finally:
            cli._delegate_make = original

    def test_autoresearch_substrate_recommend_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "substrate-recommend",
                "--mode",
                "branch",
                "--n",
                "4",
                "--class",
                "formal",
                "--substrate-class",
                "proof",
                "--branch-grid",
                "grid.json",
                "--inbox",
                "tmp/inbox",
                "--model",
                "gemini-lite",
                "--raw-payload",
                "payload.json",
                "--prompt-only",
                "--agent-recommender",
                "--agent-runtime",
                "codex",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-substrate-recommend")
            self.assertEqual(
                seen["vars"],
                {
                    "RECOMMENDER_MODE": "branch",
                    "RECOMMENDER_N": "4",
                    "RECOMMENDER_CLASS": "formal",
                    "RECOMMENDER_SUBSTRATE_CLASS": "proof",
                    "BRANCH_GRID": "grid.json",
                    "INBOX": "tmp/inbox",
                    "MODEL": "gemini-lite",
                    "RAW_PAYLOAD": "payload.json",
                    "PROMPT_ONLY": "1",
                    "SKIP_LLM": "",
                    "AGENT_RECOMMENDER": "1",
                    "AGENT_RUNTIME": "codex",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_workbench_recommend_alias_forwards_to_same_make_target(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "workbench-recommend",
                "--prompt-only",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "autoresearch-substrate-recommend")
            self.assertEqual(seen["vars"]["PROMPT_ONLY"], "1")
        finally:
            cli._delegate_make = original

    def test_autoresearch_hardening_show_delegates_to_make(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run(["autoresearch", "hardening", "show"])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "gaming-vector-hardening-show")
            self.assertEqual(seen["vars"], {})
        finally:
            cli._delegate_make = original

    def test_autoresearch_hardening_run_vector_requires_vector(self) -> None:
        rc, _, err = _run(["autoresearch", "hardening", "run-vector"])
        self.assertEqual(rc, 2)
        self.assertIn("requires --vector", err)

    def test_autoresearch_hardening_run_vector_forwards_scope(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, _ = _run([
                "autoresearch",
                "hardening",
                "run-vector",
                "--vector",
                "definitional_tautology_self_confirming_metric",
                "--substrate",
                "autoresearch",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(seen["target"], "gaming-vector-hardening-run-vector")
            self.assertEqual(
                seen["vars"],
                {
                    "VECTOR": "definitional_tautology_self_confirming_metric",
                    "SUBSTRATE": "autoresearch",
                },
            )
        finally:
            cli._delegate_make = original

    def test_autoresearch_unknown_verb_returns_two(self) -> None:
        rc, _, err = _run(["autoresearch", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown autoresearch verb", err)

    def test_substrate_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["substrate"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare substrate <verb>", out)
        for verb in (
            "new",
            "prepare",
            "seal",
            "intake",
            "packet",
            "prep-ledger",
            "queue",
            "walkthrough",
            "source-init",
            "source-check",
            "source-index",
            "evidence-bind",
            "evidence-replay",
            "evidence-gap",
            "portfolio-list",
            "portfolio-scaffold",
        ):
            self.assertIn(verb, out)

    def test_project_alias_no_args_prints_project_help(self) -> None:
        rc, out, _ = _run(["project"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare project <verb>", out)
        self.assertIn("walkthrough", out)
        self.assertIn("source-init", out)
        self.assertIn("source-check", out)
        self.assertIn("source-index", out)
        self.assertIn("evidence-bind", out)
        self.assertIn("evidence-replay", out)
        self.assertIn("evidence-gap", out)
        self.assertIn("intake", out)
        self.assertIn("packet", out)

    def test_project_alias_delegates_to_intake_commands(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run([
                "project",
                "intake",
                "enqueue",
                "--path",
                "intake.json",
                "--json",
                "--queue-dir",
                "queue",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.substrate_queue")
            self.assertEqual(
                seen["args"],
                ["--queue-dir", "queue", "enqueue-packet", "--path", "intake.json", "--json"],
            )
        finally:
            cli._delegate_module = original

    def test_project_packet_legacy_alias_delegates_to_intake_commands(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run([
                "project",
                "packet",
                "enqueue",
                "--path",
                "packet.json",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.substrate_queue")
            self.assertEqual(
                seen["args"],
                ["enqueue-packet", "--path", "packet.json", "--json"],
            )
        finally:
            cli._delegate_module = original

    def test_project_alias_delegates_to_packet_falsifier(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run([
                "project",
                "packet",
                "falsify",
                "--path",
                "packet.json",
                "--remove-ref",
                "evidence_refs[1]",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.substrate_queue")
            self.assertEqual(
                seen["args"],
                [
                    "falsify-packet",
                    "--path",
                    "packet.json",
                    "--remove-ref",
                    "evidence_refs[1]",
                    "--json",
                ],
            )
        finally:
            cli._delegate_module = original

    def test_project_alias_delegates_to_packet_draft_from_compiled(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run([
                "project",
                "packet",
                "draft-from-compiled",
                "--project",
                "demo",
                "--path",
                "projects/demo/demo_packet.json",
                "--json",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.substrate_queue")
            self.assertEqual(
                seen["args"],
                [
                    "draft-from-compiled",
                    "--project",
                    "demo",
                    "--path",
                    "projects/demo/demo_packet.json",
                    "--json",
                ],
            )
        finally:
            cli._delegate_module = original

    def test_project_alias_unknown_terms_use_project_name(self) -> None:
        rc, _, err = _run(["project", "intake", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown project intake action", err)
        self.assertIn("draft-from-compiled", err)
        self.assertIn("falsify", err)

    def test_substrate_new_delegates_to_generator_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["substrate", "new", "--help"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.generate_substrate")
            self.assertEqual(seen["args"], ["--help"])
        finally:
            cli._delegate_module = original

    def test_substrate_generate_alias_delegates_to_generator_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["substrate", "generate", "--help"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.generate_substrate")
            self.assertEqual(seen["args"], ["--help"])
        finally:
            cli._delegate_module = original

    def test_substrate_prepare_requires_project_and_rubric(self) -> None:
        rc, _, err = _run(["substrate", "prepare", "--project", "gp_example"])
        self.assertEqual(rc, 2)
        self.assertIn("requires --project", err)

    def test_substrate_prepare_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, err = _run([
                "substrate",
                "prepare",
                "--project",
                "gp_example",
                "--rubric",
                "gp_example",
                "--model",
                "gpt4.1",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "setup-project")
            self.assertEqual(
                seen["vars"],
                {"PROJECT": "gp_example", "RUBRIC": "gp_example", "MODEL": "gpt4.1"},
            )
        finally:
            cli._delegate_make = original

    def test_substrate_seal_forwards_make_flags(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_make
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                seen["target"] = target
                seen["vars"] = vars_
                return 0

            cli._delegate_make = _fake_delegate_make
            rc, _, err = _run([
                "substrate",
                "seal",
                "--project",
                "gp_example",
                "--rubric",
                "gp_example",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["target"], "seal")
            self.assertEqual(seen["vars"], {"PROJECT": "gp_example", "RUBRIC": "gp_example"})
        finally:
            cli._delegate_make = original

    def test_substrate_queue_delegates_to_queue_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["substrate", "queue", "list", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.substrate_queue")
            self.assertEqual(seen["args"], ["list", "--json"])
        finally:
            cli._delegate_module = original

    def test_project_prep_ledger_alias_delegates_to_queue_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["project", "prep-ledger", "list", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.substrate_queue")
            self.assertEqual(seen["args"], ["list", "--json"])
        finally:
            cli._delegate_module = original

    def test_substrate_walkthrough_delegates_to_walkthrough_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["substrate", "walkthrough", "--demo", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.substrate_walkthrough")
            self.assertEqual(seen["args"], ["--demo", "--json"])
        finally:
            cli._delegate_module = original

    def test_project_source_init_delegates_to_source_project_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["project", "source-init", "--project", "demo", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.source_project")
            self.assertEqual(seen["args"], ["--project", "demo", "--json"])
        finally:
            cli._delegate_module = original

    def test_project_source_check_delegates_to_source_check_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["project", "source-check", "--project", "demo", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.source_check")
            self.assertEqual(seen["args"], ["--project", "demo", "--json"])
        finally:
            cli._delegate_module = original

    def test_project_source_index_delegates_to_workspace_update_index_only(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["project", "source-index", "--project", "demo"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.workspace.update_workspace")
            self.assertEqual(seen["args"], ["--index-only", "--project", "demo"])
        finally:
            cli._delegate_module = original

    def test_project_evidence_bind_delegates_to_binding_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["project", "evidence-bind", "--project", "demo", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.workspace.evidence_output_binding")
            self.assertEqual(seen["args"], ["--project", "demo", "--json"])
        finally:
            cli._delegate_module = original

    def test_project_evidence_replay_delegates_to_replay_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["project", "evidence-replay", "--project", "demo", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.workspace.evidence_replay")
            self.assertEqual(seen["args"], ["--project", "demo", "--json"])
        finally:
            cli._delegate_module = original

    def test_project_claim_support_delegates_to_claim_support_module(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run(["project", "claim-support", "--project", "demo", "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.workspace.claim_support")
            self.assertEqual(seen["args"], ["--project", "demo", "--json"])
        finally:
            cli._delegate_module = original

    def test_project_evidence_gap_delegates_to_resolution_module(self) -> None:
        seen: list[dict[str, object]] = []
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen.append({"module": module, "args": list(args)})
                return 0

            cli._delegate_module = _fake_delegate_module
            rc_list, _, err_list = _run([
                "project",
                "evidence-gap",
                "list",
                "--project",
                "demo",
                "--json",
            ])
            rc, _, err = _run([
                "project",
                "evidence-gap",
                "justify",
                "--project",
                "demo",
                "--gap-id",
                "gap1",
                "--reason",
                "Covered by the bounded packet non-claim.",
                "--json",
            ])
            self.assertEqual(rc_list, 0)
            self.assertEqual(err_list, "")
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen[0]["module"], "ztare.workspace.evidence_gap_resolutions")
            self.assertEqual(
                seen[0]["args"],
                ["list", "--project", "demo", "--json"],
            )
            self.assertEqual(seen[1]["module"], "ztare.workspace.evidence_gap_resolutions")
            self.assertEqual(
                seen[1]["args"],
                [
                    "justify",
                    "--project",
                    "demo",
                    "--gap-id",
                    "gap1",
                    "--reason",
                    "Covered by the bounded packet non-claim.",
                    "--json",
                ],
            )
        finally:
            cli._delegate_module = original

    def test_substrate_queue_accepts_queue_dir_after_action(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run([
                "substrate",
                "queue",
                "list",
                "--json",
                "--queue-dir",
                "/tmp/queue",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.substrate_queue")
            self.assertEqual(seen["args"], ["--queue-dir", "/tmp/queue", "list", "--json"])
        finally:
            cli._delegate_module = original

    def test_substrate_packet_alias_delegates_to_packet_commands(self) -> None:
        seen: dict[str, object] = {}
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen["module"] = module
                seen["args"] = list(args)
                return 0

            cli._delegate_module = _fake_delegate_module
            rc, _, err = _run([
                "substrate",
                "packet",
                "enqueue",
                "--path",
                "/tmp/packet.json",
                "--json",
                "--queue-dir",
                "/tmp/queue",
            ])
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertEqual(seen["module"], "ztare.scaffold.substrate_queue")
            self.assertEqual(
                seen["args"],
                ["--queue-dir", "/tmp/queue", "enqueue-packet", "--path", "/tmp/packet.json", "--json"],
            )
        finally:
            cli._delegate_module = original

    def test_substrate_packet_unknown_action_returns_two(self) -> None:
        rc, _, err = _run(["substrate", "packet", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown substrate packet action", err)

    def test_substrate_unknown_verb_returns_two(self) -> None:
        rc, _, err = _run(["substrate", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown substrate verb", err)

    def test_primitive_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["primitive"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare primitive <verb>", out)
        self.assertIn("health", out)

    def test_primitive_health_runs_catalog_and_atlas_checks(self) -> None:
        calls: list[tuple[str, object, object]] = []
        original_make = cli._delegate_make
        original_module = cli._delegate_module
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                calls.append(("make", target, vars_))
                return 0

            def _fake_delegate_module(module: str, args) -> int:
                calls.append(("module", module, list(args)))
                return 0

            cli._delegate_make = _fake_delegate_make
            cli._delegate_module = _fake_delegate_module
            rc, _, _ = _run(["primitive", "health", "--json", "--semantic-live", "--eval"])
            self.assertEqual(rc, 0)
            self.assertEqual(
                calls,
                [
                    ("make", "primitive-catalog-health", {"JSON": "1"}),
                    ("module", "ztare.research_director.primitive_amnesia", ["--atlas-status"]),
                    ("module", "ztare.research_director.primitive_amnesia", ["--semantic-live"]),
                    ("module", "ztare.research_director.primitive_amnesia", ["--eval"]),
                ],
            )
        finally:
            cli._delegate_make = original_make
            cli._delegate_module = original_module

    def test_primitive_leaf_help_does_not_delegate(self) -> None:
        calls: list[tuple[str, str]] = []
        original_make = cli._delegate_make
        original_module = cli._delegate_module
        try:
            def _fake_delegate_make(target: str, vars_: dict[str, str], extra_args=()) -> int:
                calls.append(("make", target))
                return 0

            def _fake_delegate_module(module: str, args) -> int:
                calls.append(("module", module))
                return 0

            cli._delegate_make = _fake_delegate_make
            cli._delegate_module = _fake_delegate_module
            cases = [
                (["primitive", "health", "--help"], "ztare primitive health"),
                (["primitive", "parent-utility", "--help"], "ztare primitive parent-utility"),
                (["primitive", "utility", "--help"], "ztare primitive utility"),
            ]
            for argv, expected in cases:
                rc, out, err = _run(argv)
                self.assertEqual(rc, 0)
                self.assertEqual(err, "")
                self.assertIn(expected, out)
            self.assertEqual(calls, [])
        finally:
            cli._delegate_make = original_make
            cli._delegate_module = original_module

    def test_primitive_unknown_verb_returns_two(self) -> None:
        rc, _, err = _run(["primitive", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown primitive verb", err)

    def test_audit_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["audit"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare audit <verb>", out)
        for verb in (
            "gates",
            "effectiveness",
            "coverage",
            "graph-capability",
            "forecast-capability",
            "move-card-router",
            "operator-card-router",
        ):
            self.assertIn(verb, out)

    def test_audit_capability_verbs_delegate_to_make_targets(self) -> None:
        seen: list[tuple[str, list[str]]] = []
        original = cli._delegate_module
        try:
            def _fake_delegate_module(module: str, args) -> int:
                seen.append((module, list(args)))
                return 0

            cli._delegate_module = _fake_delegate_module
            rc_graph, _, err_graph = _run(["audit", "graph-capability", "--json"])
            rc_forecast, _, err_forecast = _run(["audit", "forecast-capability", "--json"])
            rc_cards, _, err_cards = _run(["audit", "move-card-router", "--json"])
            rc_cards_legacy, _, err_cards_legacy = _run(["audit", "operator-card-router", "--json"])
            self.assertEqual(rc_graph, 0)
            self.assertEqual(rc_forecast, 0)
            self.assertEqual(rc_cards, 0)
            self.assertEqual(rc_cards_legacy, 0)
            self.assertEqual(err_graph, "")
            self.assertEqual(err_forecast, "")
            self.assertEqual(err_cards, "")
            self.assertEqual(err_cards_legacy, "")
            self.assertEqual(seen[0], ("ztare.reports.graph_capability_audit", ["--json"]))
            self.assertEqual(seen[1], ("ztare.reports.forecast_capability_audit", ["--json"]))
            self.assertEqual(seen[2], ("ztare.reports.operator_card_router_audit", ["--json"]))
            self.assertEqual(seen[3], ("ztare.reports.operator_card_router_audit", ["--json"]))
        finally:
            cli._delegate_module = original

    def test_audit_capability_verbs_reject_gate_only_flags(self) -> None:
        rc, _, err = _run(["audit", "graph-capability", "--strict"])
        self.assertEqual(rc, 2)
        self.assertIn("supports --json only", err)

    def test_audit_unknown_verb_returns_two(self) -> None:
        rc, _, err = _run(["audit", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown audit verb", err)

    def test_arch_validate_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["arch-validate"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare arch-validate <verb>", out)
        for verb in ("ex-ante", "ex-post"):
            self.assertIn(verb, out)

    def test_arch_validate_unknown_verb_returns_two(self) -> None:
        rc, _, err = _run(["arch-validate", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown arch-validate verb", err)

    def test_mine_no_args_prints_help_not_pipeline(self) -> None:
        """Discipline: bare `ztare mine` must NOT trigger the multi-minute
        full mining cycle. The underlying script defaults to a full run on
        no args; the CLI guards against accidental invocation."""
        rc, out, _ = _run(["mine"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare mine", out)
        self.assertIn("--index-only", out)
        self.assertIn("--run-full-cycle", out)
        # Sanity: the help text should NOT contain the mining script's
        # actual output markers (would mean we accidentally ran the pipe).
        self.assertNotIn("reflexive mine — canonical orchestrator", out)

    def test_action_intel_record_agentic_work_delegates_to_control_script(self) -> None:
        calls: list[tuple[str, list[str]]] = []
        original = cli._delegate
        try:
            def _fake_delegate(script_name: str, args) -> int:
                calls.append((script_name, list(args)))
                return 0

            cli._delegate = _fake_delegate
            rc, _, _ = _run(["action-intel", "record-agentic-work", "--help"])
        finally:
            cli._delegate = original

        self.assertEqual(rc, 0)
        self.assertEqual(calls, [("action_intelligence.py", ["record-agentic-work", "--help"])])


class DoctorTests(unittest.TestCase):
    def test_doctor_runs_and_returns_zero(self) -> None:
        rc, out, _ = _run(["doctor"])
        self.assertEqual(rc, 0)
        self.assertIn("python", out)
        self.assertIn("control", out)
        self.assertIn("external tools:", out)
        self.assertIn("environment:", out)
        self.assertIn("forecast:pool", out)
        self.assertIn("forecast:cutoff-panel-run", out)
        self.assertIn("projects/llm_forecasting_calibration_program/tools/cutoff_stage_b_dispatch_runner.py", out)

    def test_doctor_does_not_leak_api_keys(self) -> None:
        rc, out, _ = _run(["doctor"])
        self.assertEqual(rc, 0)
        for var in (
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "KIMI_API_KEY",
            "MOONSHOT_API_KEY",
            "XAI_API_KEY",
            "GROK_API_KEY",
        ):
            val = os.environ.get(var)
            if val and len(val) > 10:
                self.assertNotIn(val, out, f"doctor leaked {var}")


class CompletionTests(unittest.TestCase):
    def test_completion_bash_emits_script(self) -> None:
        rc, out, _ = _run(["completion", "bash"])
        self.assertEqual(rc, 0)
        self.assertIn("_ztare_complete", out)
        self.assertIn("f47-run", out)
        self.assertIn("route", out)
        self.assertIn("status", out)
        self.assertIn("proof-audit", out)
        self.assertIn("source-scout", out)
        self.assertIn("parent-utility", out)
        self.assertIn("coverage", out)
        self.assertIn("graph-capability", out)
        self.assertIn("forecast-capability", out)
        self.assertIn("move-card-router", out)
        self.assertIn("operator-card-router", out)
        self.assertIn("ex-post", out)
        self.assertIn("complete -F _ztare_complete ztare", out)

    def test_completion_zsh_emits_compdef(self) -> None:
        rc, out, _ = _run(["completion", "zsh"])
        self.assertEqual(rc, 0)
        self.assertIn("#compdef ztare", out)
        self.assertIn("f47-run", out)
        self.assertIn("route", out)
        self.assertIn("status", out)
        self.assertIn("proof-audit", out)
        self.assertIn("source-scout", out)
        self.assertIn("parent-utility", out)
        self.assertIn("coverage", out)
        self.assertIn("graph-capability", out)
        self.assertIn("forecast-capability", out)
        self.assertIn("move-card-router", out)
        self.assertIn("operator-card-router", out)
        self.assertIn("ex-post", out)
        self.assertIn("compdef _ztare ztare", out)

    def test_completion_fish_emits_completions(self) -> None:
        rc, out, _ = _run(["completion", "fish"])
        self.assertEqual(rc, 0)
        self.assertIn("complete -c ztare", out)
        self.assertIn("f47-run", out)
        self.assertIn("route", out)
        self.assertIn("status", out)
        self.assertIn("proof-audit", out)
        self.assertIn("source-scout", out)
        self.assertIn("parent-utility", out)
        self.assertIn("coverage", out)
        self.assertIn("graph-capability", out)
        self.assertIn("forecast-capability", out)
        self.assertIn("move-card-router", out)
        self.assertIn("operator-card-router", out)
        self.assertIn("ex-post", out)

    def test_completion_unsupported_shell_returns_two(self) -> None:
        rc, _, err = _run(["completion", "powershell"])
        self.assertEqual(rc, 2)
        self.assertIn("unsupported shell", err)


class KeyboardInterruptTests(unittest.TestCase):
    def test_keyboard_interrupt_returns_130(self) -> None:
        original = cli._SUBCOMMANDS["forecast"]
        try:
            def _raise(_rest: list[str]) -> int:
                raise KeyboardInterrupt
            cli._SUBCOMMANDS["forecast"] = (original[0], _raise)
            rc, _, err = _run(["forecast"])
            self.assertEqual(rc, 130)
            self.assertIn("interrupted", err)
        finally:
            cli._SUBCOMMANDS["forecast"] = original


class HandlerReturnTypeTests(unittest.TestCase):
    def test_none_return_treated_as_success(self) -> None:
        original = cli._SUBCOMMANDS["forecast"]
        try:
            cli._SUBCOMMANDS["forecast"] = (original[0], lambda _rest: None)
            rc, _, _ = _run(["forecast"])
            self.assertEqual(rc, 0)
        finally:
            cli._SUBCOMMANDS["forecast"] = original

    def test_non_int_return_is_failure_not_crash(self) -> None:
        original = cli._SUBCOMMANDS["forecast"]
        try:
            cli._SUBCOMMANDS["forecast"] = (original[0], lambda _rest: "not an int")
            rc, _, err = _run(["forecast"])
            self.assertEqual(rc, 1)
            self.assertIn("non-int", err)
        finally:
            cli._SUBCOMMANDS["forecast"] = original


class SubcommandRegistryStructureTests(unittest.TestCase):
    def test_every_subcommand_has_help_and_callable(self) -> None:
        for name, entry in cli._SUBCOMMANDS.items():
            self.assertEqual(len(entry), 2, f"{name!r}: entry must be (help, handler)")
            help_text, handler = entry
            self.assertIsInstance(help_text, str, f"{name!r}: help must be str")
            self.assertTrue(help_text.strip(), f"{name!r}: help must be non-empty")
            self.assertTrue(callable(handler), f"{name!r}: handler must be callable")

    def test_delegating_subcommands_resolve_to_existing_scripts(self) -> None:
        for name, (_, _, scripts) in cli._SUBCOMMANDS_METADATA.items():
            for script in scripts:
                path = cli._control_script(script)
                self.assertTrue(path.is_file(), f"{name!r}: {script} missing")


def _self_test() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(_self_test())
