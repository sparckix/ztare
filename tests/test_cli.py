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
import os
import sys
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
        for verb in ("propose", "validate"):
            self.assertIn(verb, out)

    def test_eigenquestion_unknown_verb_returns_two(self) -> None:
        rc, _, err = _run(["eigenquestion", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown eigenquestion verb", err)

    def test_autoresearch_no_args_prints_help(self) -> None:
        rc, out, _ = _run(["autoresearch"])
        self.assertEqual(rc, 0)
        self.assertIn("ztare autoresearch <verb>", out)
        for verb in ("run", "portfolio"):
            self.assertIn(verb, out)

    def test_autoresearch_run_requires_project_and_rubric(self) -> None:
        rc, _, err = _run(["autoresearch", "run"])
        self.assertEqual(rc, 2)
        self.assertIn("requires --project", err)

    def test_autoresearch_unknown_verb_returns_two(self) -> None:
        rc, _, err = _run(["autoresearch", "wibble"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown autoresearch verb", err)

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
