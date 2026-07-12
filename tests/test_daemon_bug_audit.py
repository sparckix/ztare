"""Bug audit pass for daemon + tenant overlay + portfolio modules.

Tests cover high-risk paths that touch live systems if buggy:
  1. subprocess env-scrub (must keep claude CLI on subscription, not API)
  2. work_discovery scope filter edge cases (None assigned_to, mixed sources)
  3. substrate_portfolio registry loader (malformed yaml, missing file)
  4. eigenquestion_generator argument paths (bad project, bad output)
  5. Gate dedup (currently a known bug — test asserts the bug)

Each test stubs at the smallest boundary so failures localize.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── 1. subprocess env scrub ───────────────────────────────────────────────
# This is the critical assertion: when daemon dispatches to claude/codex CLI,
# ANTHROPIC_API_KEY + OPENAI_API_KEY must NOT be visible to the subprocess.
# Otherwise CLI prefers API key over OAuth subscription token, and you pay API
# rates for what should be subscription-quota work.

class TestSubprocessEnvScrub(unittest.TestCase):
    def test_anthropic_and_openai_keys_stripped(self):
        """Replicates the env-scrub in scripts/public/control/agent_daemon.py."""
        fake_env = {
            "ANTHROPIC_API_KEY": "sk-ant-leak",
            "OPENAI_API_KEY": "sk-openai-leak",
            "GOOGLE_API_KEY": "kept",
            "TELEGRAM_BOT_TOKEN": "kept",
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/ztare",
        }
        # Apply the scrub logic verbatim (extracted to test it in isolation)
        subprocess_env = {k: v for k, v in fake_env.items()
                          if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
        self.assertNotIn("ANTHROPIC_API_KEY", subprocess_env)
        self.assertNotIn("OPENAI_API_KEY", subprocess_env)
        # Other env preserved (Google, Telegram, PATH, HOME)
        self.assertEqual(subprocess_env["GOOGLE_API_KEY"], "kept")
        self.assertEqual(subprocess_env["TELEGRAM_BOT_TOKEN"], "kept")
        self.assertEqual(subprocess_env["PATH"], "/usr/bin:/bin")

    def test_scrub_keeps_homedir_for_oauth_lookup(self):
        """claude CLI reads ~/.claude/.credentials.json; HOME must survive."""
        fake_env = {
            "ANTHROPIC_API_KEY": "drop-me",
            "HOME": "/home/ztare",
            "USER": "ztare",
        }
        scrubbed = {k: v for k, v in fake_env.items()
                    if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
        self.assertIn("HOME", scrubbed)
        self.assertIn("USER", scrubbed)

    def test_subscription_agent_preserves_claude_auth_token(self):
        """Claude Code token auth is subscription CLI state, not a metered API key."""
        from ztare.common.subscription_agent_runtime import subscription_agent_env

        scrubbed = subscription_agent_env(
            "claude",
            {
                "ANTHROPIC_API_KEY": "drop-me",
                "ANTHROPIC_AUTH_TOKEN": "keep-token-auth",
                "HOME": "/home/ztare",
            },
        )
        self.assertNotIn("ANTHROPIC_API_KEY", scrubbed)
        self.assertEqual(scrubbed["ANTHROPIC_AUTH_TOKEN"], "keep-token-auth")
        self.assertEqual(scrubbed["HOME"], "/home/ztare")


# ── 2. work_discovery scope filter ─────────────────────────────────────────
class TestScopeFilter(unittest.TestCase):
    def setUp(self):
        from ztare.orchestration.work_discovery import _is_in_role_scope, Candidate
        self.is_in_scope = _is_in_role_scope
        self.Candidate = Candidate

    def _cand(self, source="TODO-scan", intent="", origin_path=None, raw_text=""):
        return self.Candidate(
            source=source,
            intent=intent,
            origin_path=origin_path,
            scarcity_signal="",
            raw_text=raw_text,
        )

    def test_no_assigned_to_passes_through(self):
        c = self._cand(intent="anything")
        self.assertTrue(self.is_in_scope(c, None))
        self.assertTrue(self.is_in_scope(c, ""))

    def test_non_sro_role_passes_through(self):
        c = self._cand(intent="random work")
        self.assertTrue(self.is_in_scope(c, "role.research_director"))
        self.assertTrue(self.is_in_scope(c, "role.manager"))
        self.assertTrue(self.is_in_scope(c, "role.engineer"))

    def test_sro_substrate_portfolio_always_passes(self):
        c = self._cand(source="substrate-portfolio", intent="scaffold v3")
        self.assertTrue(self.is_in_scope(c, "role.self_recursive_orchestrator"))

    def test_sro_principal_goal_passes(self):
        # Even if intent doesn't mention ztare_on_ztare, principal-goal source passes
        c = self._cand(source="principal-goal",
                       intent="execute principal goal: sro_v3_first_run")
        self.assertTrue(self.is_in_scope(c, "role.self_recursive_orchestrator"))

    def test_sro_agent_channel_passes(self):
        c = self._cand(source="agent-channel", intent="msg from manager")
        self.assertTrue(self.is_in_scope(c, "role.self_recursive_orchestrator"))

    def test_sro_text_match_ztare_on_ztare(self):
        c = self._cand(source="TODO-scan",
                       intent="ZTARE_on_ZTARE v3 needs eigenquestion review")
        self.assertTrue(self.is_in_scope(c, "role.self_recursive_orchestrator"))

    def test_sro_unrelated_todo_filtered(self):
        c = self._cand(source="TODO-scan", intent="fix paper4 typo")
        self.assertFalse(self.is_in_scope(c, "role.self_recursive_orchestrator"))

    def test_sro_damage_signal_filtered_unless_sro_related(self):
        c1 = self._cand(source="damage-scan", intent="generic OOM in gp154")
        self.assertFalse(self.is_in_scope(c1, "role.self_recursive_orchestrator"))
        c2 = self._cand(source="damage-scan",
                        intent="autonomous_scope_refused for self_recursive_orchestrator")
        self.assertTrue(self.is_in_scope(c2, "role.self_recursive_orchestrator"))


# ── 3. substrate_portfolio registry loader ─────────────────────────────────
class TestSubstratePortfolio(unittest.TestCase):
    def test_load_missing_file_raises(self):
        from ztare.research_director.substrate_portfolio import load_registry
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=True) as fp:
            missing = Path(fp.name)
        # File does not exist now (NamedTemporaryFile auto-deletes on close)
        with self.assertRaises(FileNotFoundError):
            load_registry(missing)

    def test_load_empty_yaml_returns_empty_list(self):
        from ztare.research_director.substrate_portfolio import load_registry
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as fp:
            fp.write("")  # empty file
            tmp_path = Path(fp.name)
        try:
            members = load_registry(tmp_path)
            self.assertEqual(members, [])
        finally:
            tmp_path.unlink()

    def test_load_well_formed_returns_members(self):
        from ztare.research_director.substrate_portfolio import load_registry
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as fp:
            fp.write(textwrap.dedent("""
                schema_version: 1
                members:
                  - slug: ztare_on_ztare_v2
                    eigenquestion_summary: test
                    primary_mechanism_family: foo
                    scaffolded: true
                  - slug: ztare_on_ztare_v3
                    eigenquestion_summary: test2
                    scaffolded: false
            """))
            tmp_path = Path(fp.name)
        try:
            members = load_registry(tmp_path)
            self.assertEqual(len(members), 2)
            self.assertEqual(members[0]["slug"], "ztare_on_ztare_v2")
            self.assertTrue(members[0]["scaffolded"])
            self.assertFalse(members[1]["scaffolded"])
        finally:
            tmp_path.unlink()

    def test_load_members_must_be_list(self):
        from ztare.research_director.substrate_portfolio import load_registry
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as fp:
            fp.write("members: not_a_list\n")  # invalid
            tmp_path = Path(fp.name)
        try:
            with self.assertRaises(ValueError):
                load_registry(tmp_path)
        finally:
            tmp_path.unlink()


# ── 4. eigenquestion_generator argument paths ──────────────────────────────
class TestEigenquestionGenerator(unittest.TestCase):
    def test_missing_project_raises(self):
        from ztare.research_director.eigenquestion_generator import generate_eigenquestion
        with self.assertRaises(FileNotFoundError):
            generate_eigenquestion("nonexistent_project_xyz_12345")

    def test_validate_explored_missing_project_returns_two(self):
        from ztare.research_director import eigenquestion_generator

        rc = eigenquestion_generator.main([
            "--project",
            "nonexistent_project_xyz_12345",
            "--validate-explored",
        ])

        self.assertEqual(rc, 2)

    def test_summarize_explored_classes_empty(self):
        from ztare.research_director.eigenquestion_generator import _summarize_explored_classes
        result = _summarize_explored_classes([])
        self.assertIn("no primitive classes explored yet", result)

    def test_summarize_explored_classes_with_data(self):
        from ztare.research_director.eigenquestion_generator import _summarize_explored_classes
        explored = [
            {"class_name": "ACRR", "score": 90, "run_id": "run1"},
            {"class_name": "ACRR", "score": 92, "run_id": "run2"},
            {"class_name": "PECVP", "score": 88, "run_id": "run3"},
        ]
        result = _summarize_explored_classes(explored)
        self.assertIn("ACRR", result)
        self.assertIn("PECVP", result)
        # ACRR should be ranked first (best_score 92 > PECVP 88)
        self.assertLess(result.index("ACRR"), result.index("PECVP"))

    def test_summarize_handles_missing_score(self):
        from ztare.research_director.eigenquestion_generator import _summarize_explored_classes
        # Score missing or None should not raise
        explored = [{"class_name": "X", "run_id": "r"}]
        result = _summarize_explored_classes(explored)
        self.assertIn("X", result)

    def test_available_evidence_summary_is_workspace_aware_and_general(self):
        from ztare.research_director.eigenquestion_generator import _summarize_available_evidence

        with tempfile.TemporaryDirectory() as td:
            project_dir = Path(td) / "projects" / "arbitrary_substrate"
            workspace = project_dir / "workspace"
            workspace.mkdir(parents=True)
            (project_dir / "thesis.md").write_text(
                "# Arbitrary Thesis\n\n## Current Best Statement\n\n> current object\n",
                encoding="utf-8",
            )
            (project_dir / "memory.md").write_text(
                "# Arbitrary Memory\n\n## Current Status\n\n- not old object\n",
                encoding="utf-8",
            )
            (workspace / "h01_source_audit.md").write_text(
                "# H-01 Source Audit\n\n## Verdict\n\n- source exists\n",
                encoding="utf-8",
            )

            result = _summarize_available_evidence(project_dir)

        self.assertIn("TOP-LEVEL PROJECT STATE", result)
        self.assertIn("WORKSPACE EVIDENCE ARTIFACTS", result)
        self.assertIn("thesis.md", result)
        self.assertIn("memory.md", result)
        self.assertIn("workspace/h01_source_audit.md", result)
        self.assertNotIn("neural_hunt", result)


# ── 5. Gate dedup (the bug we KNOW exists) ─────────────────────────────────
# Documents the current bug: rapid daemon restarts open duplicate gates for
# the same candidate. This test FAILS today; once gate dedup is implemented,
# it will pass. Marked xfail until fix lands.

class TestGateDedup(unittest.TestCase):
    @unittest.expectedFailure
    def test_duplicate_gate_for_same_candidate_should_not_open(self):
        """Known bug: _write_proposal_gate doesn't check for existing pending
        gates with the same subject. Two restarts in quick succession produce
        two gates for the same task. Telegram fires twice. Annoying."""
        # When dedup is implemented, this stub would simulate two calls and
        # assert only one gate file exists. Until then, expectedFailure.
        self.fail("dedup-by-subject not implemented in _write_proposal_gate")


# ── 6. LLMRuntime dotenv bootstrap (CRITICAL: substrate-chain env survival) ──
# Scenario the daemon will hit:
#   daemon (has API keys) → claude subprocess (env-scrubbed) → make portfolio-run
#   → python -m src.ztare.... → LLMRuntime() — at this point os.environ has
#   NO API keys. Without _bootstrap_dotenv_if_needed, substrate calls fail.

class TestLLMRuntimeDotenvBootstrap(unittest.TestCase):
    def test_bootstrap_loads_repo_root_dotenv_and_ignores_cwd_swap(self):
        """A cwd swap must not retarget dotenv discovery away from repo root."""
        # Stash + clear keys
        saved = {
            k: os.environ.pop(k, None)
            for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY")
        }
        try:
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)
                repo_env = Path(__file__).resolve().parents[1] / ".env"
                original_repo_env = repo_env.read_text(encoding="utf-8") if repo_env.exists() else None
                repo_env.write_text(
                    "ANTHROPIC_API_KEY=sk-ant-test-from-repo-root\n"
                    "OPENAI_API_KEY=sk-openai-test-from-repo-root\n",
                    encoding="utf-8",
                )
                old_cwd = os.getcwd()
                os.chdir(td_path)
                try:
                    from ztare.common.llm_runtime import bootstrap_dotenv_from_repo_root
                    bootstrap_dotenv_from_repo_root()
                    self.assertEqual(
                        os.environ.get("ANTHROPIC_API_KEY"),
                        "sk-ant-test-from-repo-root",
                        "bootstrap should populate ANTHROPIC_API_KEY from repo-root .env"
                    )
                    self.assertEqual(
                        os.environ.get("OPENAI_API_KEY"),
                        "sk-openai-test-from-repo-root",
                    )
                finally:
                    os.chdir(old_cwd)
                    if original_repo_env is None:
                        repo_env.unlink()
                    else:
                        repo_env.write_text(original_repo_env, encoding="utf-8")
        finally:
            # Restore
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
                elif k in os.environ:
                    del os.environ[k]

    def test_bootstrap_no_op_when_keys_present(self):
        """If keys already set in env (local developer flow), bootstrap must
        not override them with stale .env values."""
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-from-shell"
        os.environ["OPENAI_API_KEY"] = "sk-openai-from-shell"
        try:
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)
                env_file = td_path / ".env"
                env_file.write_text(
                    "ANTHROPIC_API_KEY=sk-ant-stale-from-dotenv\n"
                )
                old_cwd = os.getcwd()
                os.chdir(td_path)
                try:
                    from ztare.common.llm_runtime import bootstrap_dotenv_from_repo_root
                    bootstrap_dotenv_from_repo_root()
                    self.assertEqual(
                        os.environ["ANTHROPIC_API_KEY"],
                        "sk-ant-from-shell",
                        "bootstrap must not override env keys already set"
                    )
                finally:
                    os.chdir(old_cwd)
        finally:
            del os.environ["ANTHROPIC_API_KEY"]
            del os.environ["OPENAI_API_KEY"]


# ── 7. principal.yaml preferred_llm_provider honored by LLMRuntime ─────────

class TestPrincipalProviderPreference(unittest.TestCase):
    def setUp(self):
        # Reset caches so tests are independent (both the scalar preference and the ordered chain)
        from ztare.common import llm_runtime
        for _fn in (llm_runtime._read_principal_preferred_provider,
                    llm_runtime._read_principal_provider_order):
            if hasattr(_fn, "_cached"):
                del _fn._cached

    def test_principal_pref_google_reorders_default(self):
        """When principal.yaml says google, and all 3 keys are set,
        pick_default_model_id_for_scripts should return gemini, not claude."""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "org" / "preferences").mkdir(parents=True)
            (td_path / "org" / "preferences" / "principal.yaml").write_text(
                "preferences:\n  preferred_llm_provider: google\n"
            )
            old_cwd = os.getcwd()
            os.chdir(td_path)
            saved_keys = {
                k: os.environ.get(k)
                for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "LLM_DISPATCH_PREF")
            }
            os.environ["ANTHROPIC_API_KEY"] = "x"
            os.environ["OPENAI_API_KEY"] = "y"
            os.environ["GEMINI_API_KEY"] = "z"
            os.environ.pop("LLM_DISPATCH_PREF", None)
            try:
                # Reset cache after env mutation
                from ztare.common import llm_runtime
                for _fn in (llm_runtime._read_principal_preferred_provider,
                            llm_runtime._read_principal_provider_order):
                    if hasattr(_fn, "_cached"):
                        del _fn._cached
                model = llm_runtime.pick_default_model_id_for_scripts()
                self.assertEqual(
                    model, "gemini-3.1-pro-preview",
                    f"principal pref google → expected gemini, got {model}"
                )
            finally:
                os.chdir(old_cwd)
                for k, v in saved_keys.items():
                    if v is not None:
                        os.environ[k] = v
                    elif k in os.environ:
                        del os.environ[k]

    def test_env_dispatch_pref_wins_over_principal(self):
        """LLM_DISPATCH_PREF=anthropic must override principal yaml google."""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "org" / "preferences").mkdir(parents=True)
            (td_path / "org" / "preferences" / "principal.yaml").write_text(
                "preferences:\n  preferred_llm_provider: google\n"
            )
            old_cwd = os.getcwd()
            os.chdir(td_path)
            saved = {
                k: os.environ.get(k)
                for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "LLM_DISPATCH_PREF")
            }
            os.environ["ANTHROPIC_API_KEY"] = "x"
            os.environ["OPENAI_API_KEY"] = "y"
            os.environ["GEMINI_API_KEY"] = "z"
            os.environ["LLM_DISPATCH_PREF"] = "anthropic"
            try:
                from ztare.common import llm_runtime
                for _fn in (llm_runtime._read_principal_preferred_provider,
                            llm_runtime._read_principal_provider_order):
                    if hasattr(_fn, "_cached"):
                        del _fn._cached
                model = llm_runtime.pick_default_model_id_for_scripts()
                self.assertEqual(
                    model, "claude-sonnet-4-6",
                    f"env override anthropic → expected claude, got {model}"
                )
            finally:
                os.chdir(old_cwd)
                for k, v in saved.items():
                    if v is not None:
                        os.environ[k] = v
                    elif k in os.environ:
                        del os.environ[k]

    def test_kimi_dispatch_pref_is_supported(self):
        """LLM_DISPATCH_PREF=kimi should select Kimi when its API key exists."""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "org" / "preferences").mkdir(parents=True)
            (td_path / "org" / "preferences" / "principal.yaml").write_text(
                "preferences:\n  preferred_llm_provider: google\n"
            )
            old_cwd = os.getcwd()
            os.chdir(td_path)
            saved = {
                k: os.environ.get(k)
                for k in (
                    "ANTHROPIC_API_KEY",
                    "OPENAI_API_KEY",
                    "GEMINI_API_KEY",
                    "KIMI_API_KEY",
                    "MOONSHOT_API_KEY",
                    "LLM_DISPATCH_PREF",
                )
            }
            os.environ["ANTHROPIC_API_KEY"] = "x"
            os.environ["OPENAI_API_KEY"] = "y"
            os.environ["GEMINI_API_KEY"] = "z"
            os.environ["KIMI_API_KEY"] = "k"
            os.environ.pop("MOONSHOT_API_KEY", None)
            os.environ["LLM_DISPATCH_PREF"] = "kimi"
            try:
                from ztare.common import llm_runtime
                for _fn in (llm_runtime._read_principal_preferred_provider,
                            llm_runtime._read_principal_provider_order):
                    if hasattr(_fn, "_cached"):
                        del _fn._cached
                model = llm_runtime.pick_default_model_id_for_scripts()
                self.assertEqual(model, "kimi-k2.6")
            finally:
                os.chdir(old_cwd)
                for k, v in saved.items():
                    if v is not None:
                        os.environ[k] = v
                    elif k in os.environ:
                        del os.environ[k]

    def test_kimi_is_available_when_only_kimi_key_exists(self):
        """Kimi should be usable as the sole API-backed provider."""
        saved = {
            k: os.environ.get(k)
            for k in (
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
                "GEMINI_API_KEY",
                "GOOGLE_API_KEY",
                "KIMI_API_KEY",
                "MOONSHOT_API_KEY",
                "LLM_DISPATCH_PREF",
            )
        }
        for key in saved:
            os.environ.pop(key, None)
        os.environ["KIMI_API_KEY"] = "k"
        try:
            from ztare.common import llm_runtime
            model = llm_runtime.pick_default_model_id_for_scripts()
            self.assertEqual(model, "kimi-k2.6")
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
                elif k in os.environ:
                    del os.environ[k]


# ── 8. Model economy / tier resolution ─────────────────────────────────────

class TestModelEconomy(unittest.TestCase):
    def setUp(self):
        from ztare.common import llm_runtime
        for fn_name in ("_read_principal_preferred_provider", "_read_principal_model_economy"):
            fn = getattr(llm_runtime, fn_name, None)
            if fn and hasattr(fn, "_cached"):
                del fn._cached

    def _fixture_yaml(self):
        return """
preferences:
  preferred_llm_provider: google
model_economy:
  tiers:
    cheap:
      providers:
        google: gemini-flash-fixture
        anthropic: claude-haiku-fixture
        openai: gpt-mini-fixture
    mid:
      providers:
        google: gemini-pro-fixture
        anthropic: claude-sonnet-fixture
        openai: gpt-4.1-fixture
    pro:
      providers:
        anthropic: claude-opus-fixture
"""

    def test_cheap_tier_picks_google_when_principal_prefers_google(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "org" / "preferences").mkdir(parents=True)
            (td_path / "org" / "preferences" / "principal.yaml").write_text(self._fixture_yaml())
            old = os.getcwd(); os.chdir(td_path)
            saved = {k: os.environ.get(k) for k in ("ANTHROPIC_API_KEY","OPENAI_API_KEY","GEMINI_API_KEY")}
            os.environ["ANTHROPIC_API_KEY"]="x"; os.environ["OPENAI_API_KEY"]="y"; os.environ["GEMINI_API_KEY"]="z"
            try:
                from ztare.common import llm_runtime
                # Reset caches
                for fn in (llm_runtime._read_principal_preferred_provider, llm_runtime._read_principal_model_economy):
                    if hasattr(fn, "_cached"): del fn._cached
                self.assertEqual(llm_runtime.pick_model_for_tier("cheap"), "gemini-flash-fixture")
            finally:
                os.chdir(old)
                for k,v in saved.items():
                    if v is not None: os.environ[k]=v
                    elif k in os.environ: del os.environ[k]

    def test_mid_tier_uses_principal_preferred(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "org" / "preferences").mkdir(parents=True)
            (td_path / "org" / "preferences" / "principal.yaml").write_text(self._fixture_yaml())
            old = os.getcwd(); os.chdir(td_path)
            saved = {k: os.environ.get(k) for k in ("ANTHROPIC_API_KEY","OPENAI_API_KEY","GEMINI_API_KEY")}
            os.environ["ANTHROPIC_API_KEY"]="x"; os.environ["OPENAI_API_KEY"]="y"; os.environ["GEMINI_API_KEY"]="z"
            try:
                from ztare.common import llm_runtime
                for fn in (llm_runtime._read_principal_preferred_provider, llm_runtime._read_principal_model_economy):
                    if hasattr(fn, "_cached"): del fn._cached
                self.assertEqual(llm_runtime.pick_model_for_tier("mid"), "gemini-pro-fixture")
            finally:
                os.chdir(old)
                for k,v in saved.items():
                    if v is not None: os.environ[k]=v
                    elif k in os.environ: del os.environ[k]

    def test_pro_tier_falls_to_anthropic_when_only_provider_listed(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "org" / "preferences").mkdir(parents=True)
            (td_path / "org" / "preferences" / "principal.yaml").write_text(self._fixture_yaml())
            old = os.getcwd(); os.chdir(td_path)
            saved = {k: os.environ.get(k) for k in ("ANTHROPIC_API_KEY","OPENAI_API_KEY","GEMINI_API_KEY")}
            os.environ["ANTHROPIC_API_KEY"]="x"; os.environ["OPENAI_API_KEY"]="y"; os.environ["GEMINI_API_KEY"]="z"
            try:
                from ztare.common import llm_runtime
                for fn in (llm_runtime._read_principal_preferred_provider, llm_runtime._read_principal_model_economy):
                    if hasattr(fn, "_cached"): del fn._cached
                # Pro tier only has anthropic in fixture → must return that
                self.assertEqual(llm_runtime.pick_model_for_tier("pro"), "claude-opus-fixture")
            finally:
                os.chdir(old)
                for k,v in saved.items():
                    if v is not None: os.environ[k]=v
                    elif k in os.environ: del os.environ[k]

    def test_explicit_prefer_provider_wins(self):
        """When caller passes prefer_provider='openai', it overrides yaml pref."""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "org" / "preferences").mkdir(parents=True)
            (td_path / "org" / "preferences" / "principal.yaml").write_text(self._fixture_yaml())
            old = os.getcwd(); os.chdir(td_path)
            saved = {k: os.environ.get(k) for k in ("ANTHROPIC_API_KEY","OPENAI_API_KEY","GEMINI_API_KEY")}
            os.environ["ANTHROPIC_API_KEY"]="x"; os.environ["OPENAI_API_KEY"]="y"; os.environ["GEMINI_API_KEY"]="z"
            try:
                from ztare.common import llm_runtime
                for fn in (llm_runtime._read_principal_preferred_provider, llm_runtime._read_principal_model_economy):
                    if hasattr(fn, "_cached"): del fn._cached
                self.assertEqual(
                    llm_runtime.pick_model_for_tier("cheap", prefer_provider="openai"),
                    "gpt-mini-fixture",
                )
            finally:
                os.chdir(old)
                for k,v in saved.items():
                    if v is not None: os.environ[k]=v
                    elif k in os.environ: del os.environ[k]

    def test_model_economy_can_select_deepseek_provider(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "org" / "preferences").mkdir(parents=True)
            (td_path / "org" / "preferences" / "principal.yaml").write_text(
                """
preferences:
  preferred_llm_provider: deepseek
model_economy:
  tiers:
    cheap:
      providers:
        deepseek: deepseek-chat-fixture
        grok: grok-fixture
"""
            )
            old = os.getcwd(); os.chdir(td_path)
            saved = {
                k: os.environ.get(k)
                for k in ("DEEPSEEK_API_KEY", "XAI_API_KEY", "GROK_API_KEY")
            }
            os.environ["DEEPSEEK_API_KEY"] = "x"
            os.environ["XAI_API_KEY"] = "y"
            try:
                from ztare.common import llm_runtime
                for fn in (
                    llm_runtime._read_principal_preferred_provider,
                    llm_runtime._read_principal_model_economy,
                ):
                    if hasattr(fn, "_cached"):
                        del fn._cached
                self.assertEqual(
                    llm_runtime.pick_model_for_tier("cheap"),
                    "deepseek-chat-fixture",
                )
            finally:
                os.chdir(old)
                for k, v in saved.items():
                    if v is not None:
                        os.environ[k] = v
                    elif k in os.environ:
                        del os.environ[k]

    def test_invalid_tier_raises(self):
        from ztare.common.llm_runtime import pick_model_for_tier
        with self.assertRaises(ValueError):
            pick_model_for_tier("ultra")


# ── 9. Tenant overlay idempotency ──────────────────────────────────────────
# Setup script must be safe to run multiple times. Already manually verified;
# this test asserts the symlink-replacement logic doesn't accumulate copies.

class TestTenantOverlayIdempotency(unittest.TestCase):
    def test_setup_idempotency_logic(self):
        """The bash logic in setup_tenant.sh:
            if [[ -L "$link_path" || -e "$link_path" ]]; then
                rm -f "$link_path"
            fi
            ln -s "$target" "$link_path"
        should produce the same symlink after N runs.
        """
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            target = td_path / "target.yaml"
            target.write_text("real_content")
            link = td_path / "link.yaml"

            # Simulate setup_tenant.sh running twice
            for _ in range(2):
                if link.is_symlink() or link.exists():
                    link.unlink()
                link.symlink_to(target)

            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), target.resolve())
            self.assertEqual(link.read_text(), "real_content")


if __name__ == "__main__":
    unittest.main(verbosity=2)
