# SPDX-License-Identifier: MIT
"""Smoke tests for the ``ztare`` CLI entry point.

These tests exercise the dispatch surface, not the underlying control
scripts — those have their own self-tests. The contract under test:

- help, version, unknown-command, and KeyboardInterrupt behave correctly
  and return the right POSIX exit codes;
- every registered subcommand resolves to either a callable handler
  or an existing control script on disk;
- the two verb routers (``leanmill``, ``bundle``) print their own help
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
        for verb in ("schedule", "run", "andon", "triage", "backlog"):
            self.assertIn(verb, out)

    def test_bundle_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["bundle"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare bundle <verb>", out)
        for verb in ("run", "verify"):
            self.assertIn(verb, out)

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
        for verb in ("run", "route", "projection", "dispatch-audit", "dispatch-canary", "dispatch-parity", "subscription-outcomes", "matched-transport-pair", "hillclimb-audit", "consequence-audit", "rubric-mode-audit", "health", "operations-intelligence", "catalog-health", "fixtures", "control-demo", "hardening", "portfolio"):
            self.assertIn(verb, out)

    def test_autoresearch_run_requires_project_and_rubric(self) -> None:
        rc, _, err = _run(["autoresearch", "run"])
        self.assertEqual(rc, 2)
        self.assertIn("requires --project", err)

    def test_autoresearch_route_requires_task(self) -> None:
        rc, _, err = _run(["autoresearch", "route", "--bounded-claim"])
        self.assertEqual(rc, 2)
        self.assertIn("requires --task", err)

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
                self.assertEqual(payload["action_impact"]["action_impact_id"], "ai_route_fixture")
                self.assertTrue(route_path.exists())
                self.assertEqual(len(written_rows), 1)
                self.assertEqual(written_rows[0][0]["decision_point"]["decision_id"], "decision_fixture")
        finally:
            cli._load_action_intelligence_module = original

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

    def test_cli_autoresearch_record_path_uses_package_stable_imports(self) -> None:
        source = (_SRC / "ztare" / "cli.py").read_text(encoding="utf-8")

        self.assertNotIn("from ztare.research_director", source)
        self.assertIn("from src.ztare.research_director", source)

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
                "--iters",
                "1",
                "--pair-id",
                "pair_fixture",
                "--agent-runtime",
                "codex",
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
                    "ITERS": "1",
                    "MATCHED_RUN_ID": "pair_fixture",
                    "AGENT_RUNTIME": "codex",
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
                    "JSON": "1",
                },
            )
        finally:
            cli._delegate_make = original

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

    def test_primitive_unknown_verb_returns_two(self) -> None:
        rc, _, err = _run(["primitive", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown primitive verb", err)

    def test_audit_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["audit"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare audit <verb>", out)
        for verb in ("gates", "effectiveness", "coverage"):
            self.assertIn(verb, out)

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

    def test_doctor_does_not_leak_api_keys(self) -> None:
        rc, out, _ = _run(["doctor"])
        self.assertEqual(rc, 0)
        for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
            val = os.environ.get(var)
            if val and len(val) > 10:
                self.assertNotIn(val, out, f"doctor leaked {var}")


class CompletionTests(unittest.TestCase):
    def test_completion_bash_emits_script(self) -> None:
        rc, out, _ = _run(["completion", "bash"])
        self.assertEqual(rc, 0)
        self.assertIn("_ztare_complete", out)
        self.assertIn("complete -F _ztare_complete ztare", out)

    def test_completion_zsh_emits_compdef(self) -> None:
        rc, out, _ = _run(["completion", "zsh"])
        self.assertEqual(rc, 0)
        self.assertIn("#compdef ztare", out)
        self.assertIn("compdef _ztare ztare", out)

    def test_completion_fish_emits_completions(self) -> None:
        rc, out, _ = _run(["completion", "fish"])
        self.assertEqual(rc, 0)
        self.assertIn("complete -c ztare", out)

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
