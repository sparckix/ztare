# SPDX-License-Identifier: MIT
"""``ztare`` — the adversarial-reasoning engine's operator CLI.

A thin entry point that wraps the existing operator scripts under
``scripts/public/control/`` so the apparatus is callable as a single
command instead of ``cd repo && python scripts/public/control/<name>.py``.

**Scope of this CLI.** ZTARE the engine, not the operator's tenant
overlay. The subcommands cover the adversarial-reasoning kernel —
forecast pool, LeanMill, bundle gates, project charter, RD routine
review, action intelligence — and the substrate's research-side
operations. The governance / org side (roles, mandates, role daemons,
closure daemons, OKR-tree polling) belongs to ``cognitive-firm`` and is
deliberately *not* exposed here; operators who want those primitives
should install ``cognitive-firm`` alongside ZTARE.

Design notes:

- Stdlib-only (``argparse`` + ``subprocess``). No new runtime deps.
- Subprocess delegation preserves each underlying script's full
  argument surface; pass ``--help`` to any subcommand to see what the
  underlying script accepts (e.g. ``ztare forecast --help``).
- The CLI assumes a ZTARE checkout is the working directory (the
  scripts read ledgers by relative path). Repo-root detection walks up
  from the current file location and falls back to the cwd; set
  ``ZTARE_REPO`` to override.

Current subcommands: ``forecast``, ``leanmill``, ``bundle``,
``charter``, ``routine-review``, ``action-intel``, plus the
self-describing ``version``, ``doctor``, and ``completion``. The set is
deliberately small. Add new subcommands by extending ``_SUBCOMMANDS``
and writing a thin handler that delegates to a control script.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable


# ---------------------------------------------------------------------------
# Repo / script-root discovery
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()


def _repo_root() -> Path:
    """Find the repo root containing ``scripts/public/control/``.

    Walks up from this file's location; falls back to the current
    working directory so a ``pip install -e .`` checkout still works.
    """
    env_root = os.environ.get("ZTARE_REPO")
    if env_root:
        root = Path(env_root).resolve()
        if (root / "scripts" / "public" / "control").is_dir():
            return root
    for parent in [_THIS_FILE, *_THIS_FILE.parents]:
        if (parent / "scripts" / "public" / "control").is_dir():
            return parent
    cwd = Path.cwd()
    if (cwd / "scripts" / "public" / "control").is_dir():
        return cwd
    raise RuntimeError(
        "ztare: cannot locate the repository root with "
        "`scripts/public/control/` — invoke the CLI from a ZTARE "
        "checkout, or set ZTARE_REPO to point at one."
    )


def _control_script(name: str) -> Path:
    """Return the absolute path to a control script, asserting it exists."""
    path = _repo_root() / "scripts" / "public" / "control" / name
    if not path.is_file():
        raise SystemExit(
            f"ztare: control script not found: {path}\n"
            "If you renamed or moved it, update the CLI dispatch table."
        )
    return path


def _delegate(script_name: str, args: Iterable[str]) -> int:
    """Run a control script with the given args; return its exit code."""
    script = _control_script(script_name)
    argv = [sys.executable, str(script), *args]
    sys.stdout.flush()
    sys.stderr.flush()
    completed = subprocess.run(argv, check=False)
    return completed.returncode


# ---------------------------------------------------------------------------
# Verb router factory (used by subcommands with verb-style sub-dispatch)
# ---------------------------------------------------------------------------


def _make_verb_router(name: str, verb_map: dict[str, str]) -> Callable[[list[str]], int]:
    """Build a router that dispatches ``ztare <name> <verb> [args...]`` to
    the script named in ``verb_map``. Returns a handler suitable for
    insertion into ``_SUBCOMMANDS``.

    The router prints its own help when called with no verb or
    ``-h`` / ``--help``, listing every known verb and the script it
    targets.
    """

    def router(rest: list[str]) -> int:
        if not rest or rest[0] in ("-h", "--help"):
            print(f"ztare {name} <verb> [args...]\n\nVerbs:")
            width = max(len(v) for v in verb_map) + 2
            for verb, script in verb_map.items():
                print(f"  {verb:<{width}}→ scripts/public/control/{script}")
            print(f"\nFor any verb's own --help, run:\n  ztare {name} <verb> --help")
            return 0
        verb, *args = rest
        script = verb_map.get(verb)
        if not script:
            print(
                f"ztare: unknown {name} verb {verb!r}. "
                f"Known: {', '.join(verb_map)}",
                file=sys.stderr,
            )
            return 2
        return _delegate(script, args)

    return router


# `ztare forecast <verb>` — verb router over the forecast operator surface.
# Mixed delegation: control scripts under scripts/public/control/, a
# repo-relative analytics script, and two registered console-script
# modules under `ztare.forecasting`. Each tuple is (kind, target):
#   ("control", "<name>.py")        → scripts/public/control/<name>.py
#   ("script",  "<rel/path.py>")    → <repo_root>/<rel/path.py>
#   ("module",  "<dotted.path>")    → python -m <dotted.path>
_FORECAST_VERBS: dict[str, tuple[str, str]] = {
    "pool":              ("control", "forecast/pool.py"),
    "resolve":           ("control", "forecast/resolve_from_json.py"),
    "calibration-stats": ("module",  "ztare.forecasting.calibration_stats"),
    "calibration-db":    ("module",  "ztare.forecasting.calibration_db"),
    "score":             ("control", "forecast/score_prediction_ledger_calibration.py"),
    "ingest-smoke":      ("control", "forecast/ingest_smoke_jsonl.py"),
    "elo-refresh":       ("control", "forecast/compute_elo_by_corpus.py"),
    "brier-elo":         ("control", "forecast/brier_elo_report.py"),
    "resolve-open-metaculus": ("control", "forecast/resolve_open_metaculus.py"),
}


def _cmd_forecast_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print("ztare forecast <verb> [args...]\n\nVerbs:")
        width = max(len(v) for v in _FORECAST_VERBS) + 2
        for verb, (kind, target) in _FORECAST_VERBS.items():
            if kind == "control":
                shown = f"scripts/public/control/{target}"
            elif kind == "script":
                shown = target
            else:
                shown = f"python -m {target}"
            print(f"  {verb:<{width}}→ {shown}")
        print("\nFor any verb's own --help, run:\n  ztare forecast <verb> --help")
        return 0
    verb, *args = rest
    entry = _FORECAST_VERBS.get(verb)
    if entry is None:
        print(
            f"ztare: unknown forecast verb {verb!r}. "
            f"Known: {', '.join(_FORECAST_VERBS)}",
            file=sys.stderr,
        )
        return 2
    kind, target = entry
    if kind == "control":
        return _delegate(target, args)
    if kind == "script":
        return _delegate_script(target, args)
    if kind == "module":
        return _delegate_module(target, args)
    print(f"ztare: bug — unknown forecast verb kind {kind!r}", file=sys.stderr)
    return 1


_cmd_leanmill_router = _make_verb_router(
    "leanmill",
    {
        # control plane
        "schedule":    "leanmill/station_scheduler.py",
        "run":         "leanmill/24x7_runner.py",
        "andon":       "leanmill/andon_cord.py",
        "triage":      "leanmill/post_probe_triage.py",
        "backlog":     "leanmill/backlog_replenisher.py",
        # supervisor + lifecycle
        "watchdog":    "leanmill/watchdog.py",
        "shutdown":    "leanmill/shutdown.py",
        "restart-gate": "leanmill/restart_gate.py",
        # corpus + sourcing
        "mandate":     "leanmill/corpus_mandate_registry.py",
        "source-scout":"leanmill/source_scout_worker.py",
        "source-search":"leanmill/source_search_worker.py",
        "source-review":"leanmill/source_review_worker.py",
        "source-bind": "leanmill/source_binding_probe_worker.py",
        # families + probes
        "family-gate": "leanmill/family_spec_gate.py",
        "family-birth":"leanmill/family_birth_miner.py",
        "seeder":      "leanmill/learning_work_seeder.py",
        "probe":       "leanmill/probe_worker.py",
        # solver (Lane A direct attack)
        "solver":      "leanmill/solver_lane_worker.py",
        "slice-prep":  "leanmill/c_discriminating_slice_prep.py",
        "slice-emit":  "leanmill/emit_spectral_apn_solver_slice.py",
        "apn-candidates": "leanmill/emit_apn_lane_b_candidates.py",
        # Canonical name: `external-proof-audit` (batch audit of pre-cooked
        # external Lean proofs through the L1+L2+L3 stack). `lane-b-audit`
        # kept as alias for back-compat with operator muscle memory.
        "external-proof-audit": "leanmill/external_proof_audit.py",
        "lane-b-audit":   "leanmill/external_proof_audit.py",
        # `proof-audit` is the GENERAL canonical L1+L2+L3 audit (compile +
        # axiom_allowlist + L3 anti-pattern gates from v33_*). Takes --target
        # for any Lean file; consumed by every audit lane (Lane B / future
        # Erdős / OEIS / NS Track B heldout).
        "proof-audit":    "leanmill/proof_audit.py",
        # governance + audit (Lane B)
        "governance":  "leanmill/governance_worker.py",
        "infra-gate":  "leanmill/infra_freeze_gate.py",
        "heldout-gate":"leanmill/heldout_receipt_gate.py",
        "harness":     "leanmill/evaluation_harness_runner.py",
        # read-models + intel
        "ui-state":    "leanmill/ui_state_dump.py",
        "corpus":      "leanmill/external_corpus_ingest.py",
        "intel":       "leanmill/factory_intelligence.py",
        "credit":      "leanmill/c_supply_credit.py",
        "growth":      "leanmill/c_supply_growth_controller.py",
        "convert":     "leanmill/c_supply_conversion_prioritizer.py",
    },
)


_cmd_bundle_router = _make_verb_router(
    "bundle",
    {
        "run": "bundle_run.py",
        "verify": "bundle_verify.py",
    },
)


# ---------------------------------------------------------------------------
# Thin shells over Python modules / scripts / Make targets.
# Discipline: do not reimplement what the Makefile or a script already does.
# The CLI is a catalog over those entry points — `gh` for the apparatus.
# ---------------------------------------------------------------------------


def _run_subprocess(argv: list[str], cwd: Path | None = None) -> int:
    """Run a subprocess, returning its exit code. Centralizes the stdout/err
    flush + the cwd handling for the Make / module shells below."""
    sys.stdout.flush()
    sys.stderr.flush()
    completed = subprocess.run(argv, cwd=cwd, check=False)
    return completed.returncode


def _delegate_module(module: str, args: Iterable[str]) -> int:
    """Run `python -m <module> [args]` from the repo root. Used for modules
    that already have a CLI but are not under scripts/public/control/."""
    root = _repo_root()
    argv = [sys.executable, "-m", module, *args]
    return _run_subprocess(argv, cwd=root)


def _delegate_script(rel_path: str, args: Iterable[str]) -> int:
    """Run `python <repo_root>/<rel_path> [args]`. Used for scripts that
    sit outside scripts/public/control/."""
    root = _repo_root()
    script = root / rel_path
    if not script.is_file():
        raise SystemExit(
            f"ztare: script not found: {script}\n"
            "If you renamed or moved it, update the CLI dispatch table."
        )
    argv = [sys.executable, str(script), *args]
    return _run_subprocess(argv, cwd=root)


def _delegate_make(target: str, vars_: dict[str, str], extra_args: Iterable[str] = ()) -> int:
    """Run `make <target> KEY=VALUE ...` from the repo root. Used for
    pipeline orchestrators where the Makefile is the canonical definition;
    the CLI provides only a stable, discoverable invocation surface."""
    root = _repo_root()
    argv = ["make", target]
    for k, v in vars_.items():
        if v is not None and v != "":
            argv.append(f"{k}={v}")
    argv.extend(extra_args)
    return _run_subprocess(argv, cwd=root)


# `ztare eigenquestion <verb>` — wraps the eigenquestion-generator module.
# `propose` calls the LLM; `validate` only lints the explored-classes
# JSONL for the §14 (negative-evidence backpressure) discipline.
def _cmd_eigenquestion_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare eigenquestion <verb> [args...]\n\n"
            "Verbs:\n"
            "  propose   →  generate a fresh advisory eigenquestion (LLM call)\n"
            "  validate  →  lint workspace/explored_primitive_classes.jsonl for\n"
            "               falsified rows missing or pointing at nonexistent\n"
            "               evidence_path (§14 caveat lint; no LLM call)\n\n"
            "Both verbs require --project <slug>. For full flags, run\n"
            "  ztare eigenquestion <verb> --help"
        )
        return 0
    verb, *args = rest
    module = "src.ztare.research_director.eigenquestion_generator"
    if verb == "propose":
        return _delegate_module(module, args)
    if verb == "validate":
        return _delegate_module(module, ["--validate-explored", *args])
    print(
        f"ztare: unknown eigenquestion verb {verb!r}. Known: propose, validate",
        file=sys.stderr,
    )
    return 2


# `ztare mine` — the weekly reflexive-mining run.
# Bare invocation prints help rather than triggering the full pipeline:
# the underlying script defaults to a full cycle on no args, which is
# a multi-minute LLM-dispatching run; CLI discipline says destructive
# / expensive commands must be explicit.
def _cmd_mine(rest: list[str]) -> int:
    if not rest:
        print(
            "ztare mine [--index-only] [--skip-dashboard] [--resume-after-rating]\n\n"
            "Weekly reflexive-mining run. Bare invocation requires explicit\n"
            "intent — pass one of the flags above, or `--run-full-cycle` to\n"
            "run the entire pipeline (which may dispatch LLM calls and take\n"
            "minutes).\n\n"
            "For the underlying script's own --help (full flag list):\n"
            "  ztare mine --help\n"
        )
        return 0
    if rest == ["--run-full-cycle"]:
        rest = []  # convert the explicit-intent sentinel into the script's default
    return _delegate_script("scripts/public/mining/run_reflexive_mine.py", rest)


# `ztare autoresearch <verb>` — thin shell over the Makefile pipeline.
# Does NOT reimplement: the Makefile is canonical. CLI provides
# discovery + a stable invocation surface for RD-agents.
def _cmd_autoresearch_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare autoresearch <verb> [args...]\n\n"
            "Verbs:\n"
            "  run       →  run a full experiment-loop on a project + rubric\n"
            "               (shells to `make experiment-loop`)\n"
            "  portfolio →  run a substrate-portfolio sweep\n"
            "               (shells to `make portfolio-run`)\n\n"
            "`run` flags:\n"
            "  --project <slug>   required\n"
            "  --rubric <name>    required (name or path)\n"
            "  --iters <n>        optional (default per Makefile)\n"
            "  --mutator <model>  optional\n"
            "  --judge <model>    optional\n\n"
            "`portfolio` flags:\n"
            "  --iters <n>        optional (default 5)\n"
            "  --mutator <model>  optional (default gpt4.1)\n"
            "  --judge <model>    optional (default gpt4.1)\n"
            "  --only <substrate> optional (restrict to one substrate)\n"
        )
        return 0
    verb, *args = rest
    if verb == "run":
        kv = _parse_kv_flags(args, allowed={"--project", "--rubric", "--iters",
                                             "--mutator", "--judge"})
        if not kv.get("--project") or not kv.get("--rubric"):
            print("ztare: `autoresearch run` requires --project <slug> --rubric <name>",
                  file=sys.stderr)
            return 2
        return _delegate_make("experiment-loop", {
            "PROJECT": kv.get("--project", ""),
            "RUBRIC": kv.get("--rubric", ""),
            "ITERS": kv.get("--iters", ""),
            "MUTATOR": kv.get("--mutator", ""),
            "JUDGE": kv.get("--judge", ""),
        })
    if verb == "portfolio":
        kv = _parse_kv_flags(args, allowed={"--iters", "--mutator", "--judge", "--only"})
        return _delegate_make("portfolio-run", {
            "ITERS": kv.get("--iters", ""),
            "MUTATOR": kv.get("--mutator", ""),
            "JUDGE": kv.get("--judge", ""),
            "ONLY": kv.get("--only", ""),
        })
    print(
        f"ztare: unknown autoresearch verb {verb!r}. Known: run, portfolio",
        file=sys.stderr,
    )
    return 2


# `ztare audit <verb>` — verb router over the audit-gate-* Make targets.
def _cmd_audit_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare audit <verb> [--strict] [--json] [--verbose]\n\n"
            "Verbs:\n"
            "  gates|effectiveness  →  audit-gate-effectiveness\n"
            "  coverage             →  audit-gate-coverage\n"
            "\nAll flags pass through to the underlying audit script.\n"
        )
        return 0
    verb, *args = rest
    flags = _parse_bool_flags(args, allowed={"--strict", "--json", "--verbose"})
    if verb in ("gates", "effectiveness"):
        target = "audit-gate-effectiveness"
    elif verb == "coverage":
        target = "audit-gate-coverage"
    else:
        print(
            f"ztare: unknown audit verb {verb!r}. "
            "Known: gates, effectiveness, coverage",
            file=sys.stderr,
        )
        return 2
    return _delegate_make(target, {
        "STRICT": "1" if flags.get("--strict") else "",
        "JSON": "1" if flags.get("--json") else "",
        "VERBOSE": "1" if flags.get("--verbose") else "",
    })


# `ztare arch-validate <verb>` — wraps the GP-101 arch-map drift check.
def _cmd_arch_validate_router(rest: list[str]) -> int:
    if not rest or rest[0] in ("-h", "--help"):
        print(
            "ztare arch-validate <verb> [--only <map>]\n\n"
            "Verbs:\n"
            "  ex-ante  →  arch-validate-ex-ante (run before editing)\n"
            "  ex-post  →  arch-validate (run after editing; default)\n\n"
            "Optional: --only <label> restricts scope to one map\n"
            "(per MAP_REGISTRY in the validator).\n"
        )
        return 0
    verb, *args = rest
    kv = _parse_kv_flags(args, allowed={"--only"})
    if verb == "ex-ante":
        return _delegate_make("arch-validate-ex-ante", {"ARCH_MAP": kv.get("--only", "")})
    if verb == "ex-post":
        return _delegate_make("arch-validate", {"ARCH_MAP": kv.get("--only", "")})
    print(
        f"ztare: unknown arch-validate verb {verb!r}. Known: ex-ante, ex-post",
        file=sys.stderr,
    )
    return 2


def _parse_kv_flags(args: list[str], allowed: set[str]) -> dict[str, str]:
    """Parse a list of `--key value` flag pairs into a dict. Unknown flags
    are ignored silently so the shell-out target can complain itself."""
    out: dict[str, str] = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a in allowed and i + 1 < len(args):
            out[a] = args[i + 1]
            i += 2
        else:
            i += 1
    return out


def _parse_bool_flags(args: list[str], allowed: set[str]) -> dict[str, bool]:
    """Parse a list of boolean flags into a dict of {flag: True} for the
    ones present in ``allowed``."""
    return {flag: True for flag in args if flag in allowed}


# ---------------------------------------------------------------------------
# Self-describing subcommands (no script delegation)
# ---------------------------------------------------------------------------


def _ztare_version() -> str:
    """Resolve the installed ZTARE version from package metadata, falling
    back to the ``[project].version`` field in ``pyproject.toml`` for a
    developer checkout, then to ``unknown``. Never raises."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("ztare")
    except PackageNotFoundError:
        pass
    try:
        import tomllib

        root = _repo_root()
        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
            return data.get("project", {}).get("version", "unknown")
    except (RuntimeError, OSError, tomllib.TOMLDecodeError):
        pass
    return "unknown"


def _git_commit_short() -> str:
    """Short git HEAD for the repo; ``unknown`` if git is unavailable."""
    try:
        root = _repo_root()
    except RuntimeError:
        return "unknown"
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _cmd_version(_rest: list[str]) -> int:
    print(
        f"ztare {_ztare_version()} "
        f"(git {_git_commit_short()}, "
        f"python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})"
    )
    return 0


# ---------------------------------------------------------------------------
# `ztare doctor` — environment health check
# ---------------------------------------------------------------------------


def _which(binary: str) -> str | None:
    """Resolve a binary on PATH; ``None`` if not found."""
    from shutil import which

    return which(binary)


def _cmd_doctor(_rest: list[str]) -> int:
    """Report the apparatus's runtime environment honestly. Never mutates
    anything; always exits 0 (doctor reports, the operator decides). The
    output is plain text so it is greppable and pipeable."""
    print(f"ztare {_ztare_version()}  (git {_git_commit_short()})")
    print(f"python  : {sys.version.splitlines()[0]}")
    print(f"platform: {sys.platform}")
    try:
        root = _repo_root()
        print(f"repo    : {root}")
    except RuntimeError as exc:
        print(f"repo    : NOT FOUND — {exc}")
        return 0
    control = root / "scripts" / "public" / "control"
    print(f"control : {control}  ({'ok' if control.is_dir() else 'MISSING'})")

    # Python floor — pyproject.toml pins requires-python = ">=3.11"
    print()
    py_ok = sys.version_info >= (3, 11)
    print(f"python floor (>=3.11): {'ok' if py_ok else f'FAIL (have {sys.version_info.major}.{sys.version_info.minor})'}")

    # Package importability — if any of these fail, the apparatus is broken
    print()
    print("package imports:")
    for mod in ("ztare", "ztare.cli", "ztare.leanmill.work_queue",
                "ztare.leanmill.paths", "ztare.leanmill.policy",
                "ztare.leanmill.common"):
        try:
            __import__(mod)
            print(f"  {mod:<30} ok")
        except Exception as exc:  # noqa: BLE001 — doctor is read-only and must not raise
            print(f"  {mod:<30} FAIL — {type(exc).__name__}: {exc}")

    # Per-subcommand dispatch resolution
    print()
    print("subcommand → script (resolution check):")
    for name, (_, _handler, scripts) in _SUBCOMMANDS_METADATA.items():
        if not scripts:
            print(f"  {name:<14} (built-in)")
            continue
        for script in scripts:
            present = (control / script).is_file()
            mark = "ok" if present else "MISSING"
            print(f"  {name:<14}{script:<40} {mark}")

    # External CLIs the apparatus may shell out to
    print()
    print("external tools:")
    for binary in ("lean", "lake", "codex", "claude", "git"):
        found = _which(binary)
        print(f"  {binary:<8} {found or '(not on PATH)'}")

    # Env vars the apparatus reads
    print()
    print("environment:")
    for var in ("ZTARE_REPO", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        val = os.environ.get(var)
        if not val:
            shown = "(unset)"
        elif var.endswith("_API_KEY"):
            shown = f"set ({len(val)} chars)"
        else:
            shown = val
        print(f"  {var:<24} {shown}")
    return 0


# ---------------------------------------------------------------------------
# `ztare completion` — shell completion script emitter
# ---------------------------------------------------------------------------


_COMPLETION_SHELLS = ("bash", "zsh", "fish")


def _cmd_completion(rest: list[str]) -> int:
    """Emit a completion script for the named shell to stdout.

    Usage:  ztare completion <bash|zsh|fish>

    The scripts complete the top-level subcommands and the two verb
    routers (``leanmill``, ``bundle``). They do not introspect the
    underlying control scripts' own flags — pipe to the right rc file
    and reload.
    """
    if not rest or rest[0] in ("-h", "--help"):
        print(f"ztare completion <{('|').join(_COMPLETION_SHELLS)}>")
        print("\nEmit a shell-completion script to stdout. Source the output:")
        print("  bash:  ztare completion bash  > ~/.local/share/bash-completion/completions/ztare")
        print("  zsh :  ztare completion zsh   > \"${fpath[1]}/_ztare\"")
        print("  fish:  ztare completion fish  > ~/.config/fish/completions/ztare.fish")
        return 0
    shell = rest[0].lower()
    if shell not in _COMPLETION_SHELLS:
        print(f"ztare: unsupported shell {shell!r}. Supported: {', '.join(_COMPLETION_SHELLS)}", file=sys.stderr)
        return 2
    commands = " ".join(_SUBCOMMANDS.keys())
    leanmill_verbs = "schedule run andon triage backlog"
    bundle_verbs = "run verify"
    if shell == "bash":
        print(_BASH_COMPLETION_TEMPLATE.format(
            commands=commands,
            leanmill_verbs=leanmill_verbs,
            bundle_verbs=bundle_verbs,
        ))
    elif shell == "zsh":
        print(_ZSH_COMPLETION_TEMPLATE.format(
            commands=commands,
            leanmill_verbs=leanmill_verbs,
            bundle_verbs=bundle_verbs,
        ))
    elif shell == "fish":
        # Fish format: one completion per line. Build commands then verbs.
        lines = ["# ztare completion (fish)"]
        for cmd in _SUBCOMMANDS:
            help_text = _SUBCOMMANDS[cmd][0].splitlines()[0]
            lines.append(f"complete -c ztare -f -n '__fish_use_subcommand' -a '{cmd}' -d {help_text!r}")
        for verb in leanmill_verbs.split():
            lines.append(f"complete -c ztare -f -n '__fish_seen_subcommand_from leanmill' -a '{verb}'")
        for verb in bundle_verbs.split():
            lines.append(f"complete -c ztare -f -n '__fish_seen_subcommand_from bundle' -a '{verb}'")
        print("\n".join(lines))
    return 0


_BASH_COMPLETION_TEMPLATE = r"""# bash completion for ztare
_ztare_complete() {{
  local cur prev cmds leanmill_v bundle_v
  COMPREPLY=()
  cur="${{COMP_WORDS[COMP_CWORD]}}"
  prev="${{COMP_WORDS[COMP_CWORD-1]}}"
  cmds="{commands}"
  leanmill_v="{leanmill_verbs}"
  bundle_v="{bundle_verbs}"
  if [ "$COMP_CWORD" -eq 1 ]; then
    COMPREPLY=( $(compgen -W "$cmds" -- "$cur") )
    return 0
  fi
  if [ "$COMP_CWORD" -eq 2 ]; then
    case "$prev" in
      leanmill) COMPREPLY=( $(compgen -W "$leanmill_v" -- "$cur") ) ;;
      bundle)   COMPREPLY=( $(compgen -W "$bundle_v"   -- "$cur") ) ;;
    esac
  fi
}}
complete -F _ztare_complete ztare
"""


_ZSH_COMPLETION_TEMPLATE = r"""#compdef ztare
# zsh completion for ztare
_ztare() {{
  local -a commands leanmill_verbs bundle_verbs
  commands=({commands})
  leanmill_verbs=({leanmill_verbs})
  bundle_verbs=({bundle_verbs})
  if (( CURRENT == 2 )); then
    compadd -- "${{commands[@]}}"
    return
  fi
  case "${{words[2]}}" in
    leanmill) compadd -- "${{leanmill_verbs[@]}}" ;;
    bundle)   compadd -- "${{bundle_verbs[@]}}"   ;;
  esac
}}
compdef _ztare ztare
"""


# ---------------------------------------------------------------------------
# Subcommand registry
# ---------------------------------------------------------------------------


_SUBCOMMANDS: dict[str, tuple[str, Callable[[list[str]], int]]] = {
    "forecast": (
        "Forecast operations (GP-230): pool | resolve | calibration-stats | calibration-db | score.",
        _cmd_forecast_router,
    ),
    "leanmill": (
        "LeanMill orchestration (GP-225): schedule | run | andon | triage | backlog.",
        _cmd_leanmill_router,
    ),
    "bundle": (
        "Sealed-bundle gates: run | verify.",
        _cmd_bundle_router,
    ),
    "charter": (
        "Project-charter commit (pre-registered hypothesis).",
        lambda rest: _delegate("charter_commit.py", rest),
    ),
    "routine-review": (
        "RD routine reviews (the standing reconciliation loop).",
        lambda rest: _delegate("rd_routine_review.py", rest),
    ),
    "action-intel": (
        "Action intelligence read surface (GP-243).",
        lambda rest: _delegate("action_intelligence.py", rest),
    ),
    "eigenquestion": (
        "Eigenquestion generator (GP-228): propose | validate.",
        _cmd_eigenquestion_router,
    ),
    "mine": (
        "Weekly reflexive-mining run (the canonical orchestrator).",
        _cmd_mine,
    ),
    "autoresearch": (
        "Autoresearch pipeline (in-loop validator): run | portfolio. Shells to Make.",
        _cmd_autoresearch_router,
    ),
    "audit": (
        "Gate / coverage audits: gates | effectiveness | coverage. Shells to Make.",
        _cmd_audit_router,
    ),
    "arch-validate": (
        "GP-101 arch-map drift check: ex-ante | ex-post. Shells to Make.",
        _cmd_arch_validate_router,
    ),
    "version": (
        "Print ZTARE version, git commit, and Python version.",
        _cmd_version,
    ),
    "doctor": (
        "Environment health check (paths, scripts, external tools, env vars).",
        _cmd_doctor,
    ),
    "completion": (
        "Emit shell completion script (bash | zsh | fish).",
        _cmd_completion,
    ),
}


# Metadata used by `doctor` to verify each subcommand's underlying script
# exists. Built-in subcommands (no script delegation) have an empty tuple.
_SUBCOMMANDS_METADATA: dict[str, tuple[str, Callable[[list[str]], int], tuple[str, ...]]] = {
    # doctor only verifies scripts under scripts/public/control/; the
    # `score` verb (analytics_shared) and module verbs are intentionally
    # excluded from the control-script presence check.
    "forecast": (_SUBCOMMANDS["forecast"][0], _SUBCOMMANDS["forecast"][1], (
        "forecast_pool.py", "forecast_resolve_from_json.py",
    )),
    "leanmill": (_SUBCOMMANDS["leanmill"][0], _SUBCOMMANDS["leanmill"][1], (
        "leanmill/station_scheduler.py", "leanmill/24x7_runner.py",
        "leanmill/andon_cord.py", "leanmill/post_probe_triage.py",
        "leanmill/backlog_replenisher.py",
    )),
    "bundle": (_SUBCOMMANDS["bundle"][0], _SUBCOMMANDS["bundle"][1], ("bundle_run.py", "bundle_verify.py")),
    "charter": (_SUBCOMMANDS["charter"][0], _SUBCOMMANDS["charter"][1], ("charter_commit.py",)),
    "routine-review": (_SUBCOMMANDS["routine-review"][0], _SUBCOMMANDS["routine-review"][1], ("rd_routine_review.py",)),
    "action-intel": (_SUBCOMMANDS["action-intel"][0], _SUBCOMMANDS["action-intel"][1], ("action_intelligence.py",)),
    # Non-control-script shells: empty tuple per the doctor-check contract
    # (doctor only verifies scripts/public/control/*.py existence; module
    # and Make targets are checked by their own validators / by Make itself).
    "eigenquestion": (_SUBCOMMANDS["eigenquestion"][0], _SUBCOMMANDS["eigenquestion"][1], ()),
    "mine": (_SUBCOMMANDS["mine"][0], _SUBCOMMANDS["mine"][1], ()),
    "autoresearch": (_SUBCOMMANDS["autoresearch"][0], _SUBCOMMANDS["autoresearch"][1], ()),
    "audit": (_SUBCOMMANDS["audit"][0], _SUBCOMMANDS["audit"][1], ()),
    "arch-validate": (_SUBCOMMANDS["arch-validate"][0], _SUBCOMMANDS["arch-validate"][1], ()),
    "version": (_SUBCOMMANDS["version"][0], _SUBCOMMANDS["version"][1], ()),
    "doctor": (_SUBCOMMANDS["doctor"][0], _SUBCOMMANDS["doctor"][1], ()),
    "completion": (_SUBCOMMANDS["completion"][0], _SUBCOMMANDS["completion"][1], ()),
}


# ---------------------------------------------------------------------------
# Top-level help + main
# ---------------------------------------------------------------------------


def _print_top_help() -> None:
    print(
        "usage: ztare COMMAND [args...]\n\n"
        "ZTARE — adversarial scientific-reasoning engine.\n"
        "Subcommands wrap the apparatus's operator scripts.\n\n"
        "Commands:"
    )
    name_width = max(len(name) for name in _SUBCOMMANDS) + 2
    for name, (help_text, _) in _SUBCOMMANDS.items():
        print(f"  {name:<{name_width}}{help_text}")
    print(
        "\nFor a subcommand's full options, run `ztare COMMAND --help` — the\n"
        "flag flows through to the underlying control script."
    )


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        _print_top_help()
        return 0
    if argv[0] in ("-V", "--version"):
        return _cmd_version([])
    cmd, *rest = argv
    if cmd not in _SUBCOMMANDS:
        print(f"ztare: unknown command {cmd!r}\n", file=sys.stderr)
        _print_top_help()
        return 2
    try:
        result = _SUBCOMMANDS[cmd][1](rest)
    except KeyboardInterrupt:
        print("ztare: interrupted", file=sys.stderr)
        return 130
    # Handlers may return None (treated as success) or int. Anything else is
    # a programming error and should surface loudly rather than be coerced.
    if result is None:
        return 0
    if not isinstance(result, int):
        print(
            f"ztare: handler for {cmd!r} returned non-int {type(result).__name__}; "
            "treating as failure",
            file=sys.stderr,
        )
        return 1
    return result


if __name__ == "__main__":
    raise SystemExit(main())
