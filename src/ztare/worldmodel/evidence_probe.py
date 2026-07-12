"""Governed evidence probe: leaf-authored observation code, kernel-executed.

Observation-sort dual of the carrier-repair path (law sort): a probe never
proposes a law — it runs read-only analysis over the typed episode evidence
and returns a receipt to the commissioning surface. Executing a probe is
zero-credit: an observation neither survives nor is killed.

Contract: ``probe_source`` is self-contained python defining
``probe(episodes) -> dict`` where ``episodes`` is ``{"visible": [...]}`` and,
in DISCOVERY/HARNESS_DEBUG runs, also ``{"holdout": [...]}`` (holdout is a
sealed test set in EVALUATION and is not exposed there). Each list holds
transition dicts ``{"t", "a", "s", "s_next"}``. The only whitelisted import is
``from ztare.worldmodel.evidence_quotients import ...`` (exemplar quotients
as library calls). Source is content-addressed under
``workspace/evidence_probes/<sha>.py`` and executed in a subprocess sandbox.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RECEIPT_SCHEMA = "ztare-evidence-probe-receipt-v1"
PAYLOAD_CHAR_CAP = 20_000
STDERR_PREFIX_CHARS = 500

# Module-level episode-file cache: (project_root, run_role, episode_file_key) -> serialized JSON path.
# Invalidated when any episode file's mtime changes. The cached file lives in the system
# temp dir (auto-cleaned on reboot); key is content-addressed by mtime fingerprint.
# ponytail: simple dict, never needs eviction (episode files rarely change mid-run; one
# entry per project per role in practice)
_EPISODE_CACHE: dict[str, str] = {}


def _episode_cache_key(project_dir: Path, run_role: str) -> tuple[str, str]:
    """(fingerprint, cache_key_str) for the episode files of this project+role."""
    episodes_dir = project_dir / "raw" / "episodes"
    parts: list[str] = [str(project_dir.resolve()), run_role]
    for ep in sorted(episodes_dir.glob("*.jsonl")):
        try:
            parts.append(f"{ep.name}:{ep.stat().st_mtime}")
        except OSError:
            parts.append(ep.name)
    fingerprint = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return fingerprint, "|".join(parts[:2])  # (fingerprint, identity key prefix)

# The only ztare module a probe may import (exemplar quotients as library
# calls). Everything else in ztare is off-limits — a probe observes, it does
# not reach into the kernel.
QUOTIENT_MODULE = "ztare.worldmodel.evidence_quotients"
QUOTIENT_IMPORT_PREFIX = f"from {QUOTIENT_MODULE} import"

# Import allowlist (NOT a blocklist — a blocklist is trivially bypassed via
# `import os`, `__import__`, `urllib`, `io.open`, etc.). Only pure, side-effect-
# free stdlib for arithmetic/aggregation over the typed evidence.
_ALLOWED_STDLIB = frozenset(
    {"math", "itertools", "collections", "statistics", "functools", "heapq", "bisect"}
)
# Builtins a probe may never call — the classic exec/import/introspection escapes.
_FORBIDDEN_CALLS = frozenset(
    {"__import__", "eval", "exec", "compile", "open", "input", "breakpoint", "globals", "vars"}
)

# The runner itself may open files; the probe source may not (purity-gated).
_RUNNER = (
    "import json, sys\n"
    "with open(sys.argv[1], encoding='utf-8') as fh:\n"
    "    source = fh.read()\n"
    "with open(sys.argv[2], encoding='utf-8') as fh:\n"
    "    episodes = json.load(fh)\n"
    "namespace = {'__name__': 'ztare_evidence_probe'}\n"
    "exec(compile(source, '<evidence_probe>', 'exec'), namespace)\n"
    "probe = namespace.get('probe')\n"
    "if not callable(probe):\n"
    "    raise SystemExit('probe_source must define probe(episodes)')\n"
    "print(json.dumps(probe(episodes), sort_keys=True, default=str))\n"
)


def probe_purity_error(probe_source: str) -> "str | None":
    """Return an error naming the violation, or None if the probe is admissible.

    AST allowlist, not a substring blocklist: imports are restricted to the
    quotient module plus a pure-stdlib set; ``__import__``/eval/exec/open and
    dunder-attribute introspection (the ``().__class__.__bases__`` escape) are
    rejected outright. A probe that parses clean here cannot reach the
    filesystem, network, process table, or interpreter internals by construction.
    """
    try:
        tree = ast.parse(probe_source)
    except SyntaxError as exc:
        return f"probe_source is not valid python: {exc}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                if alias.name != QUOTIENT_MODULE and top not in _ALLOWED_STDLIB:
                    return (
                        f"import not allowed: {alias.name!r}; probes may import only "
                        f"{QUOTIENT_MODULE} or pure stdlib {sorted(_ALLOWED_STDLIB)}"
                    )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            top = mod.split(".", 1)[0]
            if mod != QUOTIENT_MODULE and top not in _ALLOWED_STDLIB:
                return (
                    f"import not allowed: from {mod!r}; probes may import only "
                    f"{QUOTIENT_MODULE} or pure stdlib {sorted(_ALLOWED_STDLIB)}"
                )
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _FORBIDDEN_CALLS:
                return f"forbidden call {node.func.id!r}: probes are read-only over the typed evidence"
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                return (
                    f"forbidden dunder attribute {node.attr!r}: interpreter "
                    "introspection is not available to probes"
                )
        elif isinstance(node, ast.Name) and node.id == "__builtins__":
            return "forbidden reference to __builtins__"
    return None


def _error_receipt(probe_sha: str, error: str) -> dict:
    return {"schema": RECEIPT_SCHEMA, "probe_sha": probe_sha, "status": "error", "error": error}


def _pack_run_role(project_dir: Path) -> str:
    # The pack stages MANIFEST.json.run_role (see briefing_pack.build_briefing_pack);
    # holdout staging keys off the same signal. Absent/unreadable manifest fails
    # closed to EVALUATION so holdout stays sealed unless a run explicitly says
    # DISCOVERY/HARNESS_DEBUG.
    for name in ("MANIFEST.json", "visible_manifest.json"):
        path = Path(project_dir) / name
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(manifest, dict) and str(manifest.get("run_role") or "").strip():
            return str(manifest["run_role"]).strip().upper()
    return "EVALUATION"


def _load_episodes(project_dir: Path) -> dict:
    # Holdout is the sealed test set for the rollout gate. In EVALUATION it stays
    # kernel-side (exposing it to a leaf probe would let the leaf read the answer
    # and defeat the gate). In DISCOVERY/HARNESS_DEBUG the holdout is intentionally
    # consumable counterexample evidence — the same signal that gates pack holdout
    # staging (briefing_pack holdout_visibility) — so the probe sees it too.
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.evidence_quotients import resolve_episode_ref
    from ztare.worldmodel.grid_dsl import grid_to_lists

    def _transitions(ref: str) -> list:
        path = resolve_episode_ref(project_dir, ref)
        return [
            {"t": tr.t, "a": tr.a, "s": grid_to_lists(tr.s), "s_next": grid_to_lists(tr.s_next)}
            for tr in EpisodeLog.read_jsonl(path)
        ]

    episodes = {"visible": _transitions("visible")}
    if _pack_run_role(project_dir) in {"DISCOVERY", "HARNESS_DEBUG"}:
        try:
            episodes["holdout"] = _transitions("holdout")
        except (ValueError, OSError):
            # DISCOVERY intends holdout to be consumable, but a pack may not have
            # staged it; leave holdout absent rather than fail the whole probe.
            pass
    return episodes


def run_evidence_probe(
    project_dir: "Path | str", probe_source: str, *, timeout_seconds: int = 60
) -> dict:
    """Sandbox-execute ``probe(episodes)`` and return a typed receipt."""
    project = Path(project_dir)
    source = str(probe_source or "")
    probe_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if not source.strip():
        return _error_receipt(probe_sha, "probe_source is empty")
    purity = probe_purity_error(source)
    if purity is not None:
        return _error_receipt(probe_sha, purity)
    # --- episode-file cache -------------------------------------------------
    # Serialize episodes to a stable content-addressed file once per
    # (project, run_role, episode-file mtime set); reuse across probe calls.
    run_role = _pack_run_role(project)
    fp, _ck = _episode_cache_key(project, run_role)
    cached_ep_path: str | None = _EPISODE_CACHE.get(fp)
    if cached_ep_path and not Path(cached_ep_path).exists():
        # Cached file was cleaned from /tmp (e.g. reboot); invalidate.
        cached_ep_path = None
        del _EPISODE_CACHE[fp]

    if cached_ep_path is None:
        try:
            episodes = _load_episodes(project)
        except ValueError as exc:
            return _error_receipt(probe_sha, f"episode evidence unavailable: {exc}")
        # Write to a stable named temp file (not auto-deleted).
        fd, cached_ep_path = tempfile.mkstemp(suffix="_ztare_episodes.json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(episodes, fh)
        except Exception:
            try:
                os.unlink(cached_ep_path)
            except OSError:
                pass
            raise
        _EPISODE_CACHE[fp] = cached_ep_path
    else:
        import logging as _logging
        _logging.getLogger(__name__).debug("episode cache hit for project %s", project)
    episodes_path = cached_ep_path
    # --- end episode-file cache ---------------------------------------------

    probe_path = project / "workspace" / "evidence_probes" / f"{probe_sha}.py"
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    probe_path.write_text(source + "\n", encoding="utf-8")

    # SCRUBBED env — do NOT inherit the parent process environment (API keys,
    # tokens, cwd hooks). The sandbox gets exactly PATH + a PYTHONPATH pointing
    # only at the ztare source so the whitelisted quotient import resolves; the
    # AST gate has already guaranteed no other import can exploit it.
    ztare_src = str(Path(__file__).resolve().parents[2])
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": ztare_src,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _RUNNER, str(probe_path), episodes_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return _error_receipt(probe_sha, f"probe timed out after {timeout_seconds}s")

    stderr_prefix = (proc.stderr or "").strip()[:STDERR_PREFIX_CHARS]
    if proc.returncode != 0:
        return _error_receipt(
            probe_sha, f"probe exited {proc.returncode}; stderr: {stderr_prefix or '<empty>'}"
        )
    stdout = (proc.stdout or "").strip()
    if not stdout:
        return _error_receipt(
            probe_sha,
            "probe produced empty stdout (probe(episodes) must return a "
            f"JSON-serializable dict); stderr: {stderr_prefix or '<empty>'}",
        )
    try:
        payload = json.loads(stdout)
    except ValueError:
        return _error_receipt(probe_sha, f"probe stdout is not JSON: {stdout[:200]!r}")
    if not isinstance(payload, dict):
        return _error_receipt(
            probe_sha, f"probe returned {type(payload).__name__}, not a dict"
        )
    receipt: dict = {"schema": RECEIPT_SCHEMA, "probe_sha": probe_sha, "status": "ok"}
    payload_json = json.dumps(payload, sort_keys=True, default=str)
    if len(payload_json) > PAYLOAD_CHAR_CAP:
        receipt["payload"] = payload_json[:PAYLOAD_CHAR_CAP]
        receipt["payload_truncated"] = (
            f"payload JSON is {len(payload_json)} chars; kept first "
            f"{PAYLOAD_CHAR_CAP}, dropped {len(payload_json) - PAYLOAD_CHAR_CAP}"
        )
    else:
        receipt["payload"] = payload
    return receipt
