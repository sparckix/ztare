"""Canonical Lean compile + axiom-probe primitives.

Shared low-level primitives for any audit lane that needs to compile Lean
sources and parse axiom output. Consolidated 2026-05-29 to remove the
duplication between `scripts/public/control/leanmill/proof_audit.py` and
`src/ztare/gates/lean_proof_gate.py`. New code should import from here;
existing call sites are migrated in-place.

Subprocess discipline (2026-05-29 fix):
  All `lake env lean` invocations spawn into a NEW PROCESS GROUP via
  `start_new_session=True`, and on `TimeoutExpired` the whole group is
  killed via `os.killpg(... SIGKILL)`. Without this, lake's `lean` child
  gets reparented to init on timeout and runs indefinitely. This is the
  mechanized fix for the orphan-lake-process leak the audit campaign hit.

Public surface (the only API external code should depend on):
  - parse_axiom_output(output) -> dict[name, list[axioms]]
  - run_lake_compile(target_path, lean_root, timeout_s) -> dict
  - run_lake_compile_source(source_text, lean_root, timeout_s, *, prefix)
        -> tuple[bool, str]
  - LEAN_ERROR_RE, AXIOM_OUTPUT_RE, DECL_START_RE  (re-exported)

Out of scope here (lives in `lean_proof_gate.py` for the NS Track B closure
flow and in `leanmill_proof_audit.py` for the canonical L1+L2+L3 audit):
verdict assembly, axiom allowlist policy lookup, anti-pattern dispatch.
"""
from __future__ import annotations
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

# SINGLE SOURCE OF TRUTH for the kernel axiom allowlist (re-analysis F3, 2026-06-05). Was triplicated
# (agentic_leaf.AXIOM_ALLOWLIST, verify_lean_stub.ALLOWED_AXIOMS, proof_surveyability_gate.
# DEFAULT_ALLOWED_AXIOMS) — identical today, but a policy widening one would silently diverge the
# supposed-ONE kernel. All three now import this. Lives in the lowest-level compile primitive (imports
# none of those, so no cycle). frozenset = immutable; widen the policy in exactly one place.
AXIOM_ALLOWLIST = frozenset({"propext", "Classical.choice", "Quot.sound"})


@lru_cache(maxsize=1)
def _elan_bin_dir() -> str | None:
    """Locate the elan bin dir (holds lake/lean/leanc). Non-login and nohup
    shells do NOT source ~/.profile, so ~/.elan/bin is often absent from PATH;
    every `lake` call then dies with FileNotFoundError and is mis-recorded as a
    compile failure. This finds it deterministically so no shell setup is ever
    required (mechanized fix for the recurring `lake_not_on_PATH` bug)."""
    cand = Path(os.environ.get("ELAN_HOME", str(Path.home() / ".elan"))) / "bin"
    if (cand / "lake").exists():
        return str(cand)
    # already on PATH?
    found = shutil.which("lake")
    if found:
        return str(Path(found).parent)
    return None


def ensure_elan_on_path() -> str | None:
    """Idempotently prepend the elan bin dir to THIS process's PATH so every
    child (deterministic `lake` compiles AND dispatched agents that shell out to
    `lake env lean` themselves) inherits it. Call once at worker/daemon startup.
    Returns the elan bin dir if found, else None. Safe to call repeatedly."""
    binp = _elan_bin_dir()
    if binp and binp not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = binp + os.pathsep + os.environ.get("PATH", "")
    return binp


def _lake_env() -> dict[str, str]:
    """Subprocess env with the elan bin dir guaranteed on PATH, so both `lake`
    AND the `lean`/`leanc` children it spawns resolve regardless of the
    launching shell (login, nohup, cron, ssh-exec)."""
    env = dict(os.environ)
    binp = _elan_bin_dir()
    if binp:
        env["PATH"] = binp + os.pathsep + env.get("PATH", "")
    return env


def _resolve_cmd(cmd: list[str]) -> list[str]:
    """Rewrite a bare `lake`/`lean`/`leanc` argv[0] to its absolute elan path so
    the call works even when the binary is not on the inherited PATH."""
    if not cmd:
        return cmd
    binp = _elan_bin_dir()
    if binp and cmd[0] in ("lake", "lean", "leanc"):
        abs_bin = Path(binp) / cmd[0]
        if abs_bin.exists():
            return [str(abs_bin), *cmd[1:]]
    return cmd


def _run_lake_with_group_kill(
    cmd: list[str], cwd: str, *, timeout_s: int,
) -> tuple[int | None, str, str, bool]:
    """Spawn `cmd` in a new process group; on TimeoutExpired kill the WHOLE
    group via SIGKILL (so lake's lean child does not get reparented to init).
    Returns (returncode, stdout, stderr, timed_out)."""
    proc = subprocess.Popen(
        _resolve_cmd(cmd), cwd=cwd, text=True, env=_lake_env(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,  # spawns into its own process group
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
        return proc.returncode, stdout or "", stderr or "", False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            try:
                proc.kill()
            except Exception:
                pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:
            stdout, stderr = "", ""
        return None, stdout or "", stderr or "", True


def run_lake_subprocess(
    cmd: list[str], cwd: str, *, timeout_s: int,
) -> subprocess.CompletedProcess:
    """Drop-in for `subprocess.run([...lake...], timeout=timeout_s)` that spawns
    into a NEW PROCESS GROUP and SIGKILLs the whole group on timeout, so lake's
    `lean` child is not orphaned/reparented to init. Raises
    `subprocess.TimeoutExpired` on timeout (exactly like `subprocess.run(...,
    timeout=)`), so existing call sites keep their except branches unchanged.
    """
    rc, out, err, timed_out = _run_lake_with_group_kill(cmd, cwd, timeout_s=timeout_s)
    if timed_out:
        raise subprocess.TimeoutExpired(cmd, timeout_s, output=out, stderr=err)
    return subprocess.CompletedProcess(cmd, rc, stdout=out, stderr=err)


# ── Regexes (canonical) ─────────────────────────────────────────────────
DECL_START_RE = re.compile(
    r"(?m)^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(?:theorem|lemma)\s+([^\s:]+)"
)
AXIOM_OUTPUT_RE = re.compile(
    r"'([^']+)'\s+depends on axioms:\s+\[([^\]]*)\]",
    re.MULTILINE | re.DOTALL,
)
# Lean prints THIS form (not the bracketed one) for an axiom-FREE declaration —
# the cleanest possible result. Without parsing it, an axiom-free theorem yields
# an empty axiom_map and is mis-graded `axiom_probe_inconclusive` (the 2026-05-31
# bug that left the auditor's verdict inconclusive even on clean proofs).
AXIOM_NONE_RE = re.compile(r"'([^']+)'\s+does not depend on any axioms", re.MULTILINE)
LEAN_ERROR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)
_BARE_ERROR_RE = re.compile(r"(?m)^\s*error:")


def _is_compile_ok(rc: "int | None", output: str) -> bool:
    """Single compile oracle. A clean compile requires exit 0 AND no error
    line (positional OR bare/non-positional) AND no `sorry` warning. Lean
    emits ``declaration uses `sorry``` (BACKTICKS, not straight quotes) as a
    WARNING with exit 0, so a sorry-backed proof would otherwise read as a
    clean compile — fail it. `admit` produces the same warning. We match the
    quote-agnostic forms plus the bare phrase and `sorryAx` so the oracle is
    robust to Lean's quoting and to #print-axioms output."""
    if rc != 0:
        return False
    if LEAN_ERROR_RE.search(output) or _BARE_ERROR_RE.search(output):
        return False
    if re.search(r"uses [`'\"]sorry[`'\"]", output) or "declaration uses" in output:
        return False
    if "sorryAx" in output:
        return False
    return True


def parse_axiom_output(output: str) -> dict[str, list[str]]:
    """Parse `'X' depends on axioms: [a, b, c]` lines into {name: [axiom,...]}."""
    parsed: dict[str, list[str]] = {}
    for match in AXIOM_OUTPUT_RE.finditer(output):
        theorem = match.group(1).strip()
        axioms = [
            part.strip()
            for part in re.split(r",|\n", match.group(2))
            if part.strip()
        ]
        parsed[theorem] = axioms
    # axiom-free declarations (Lean's "does not depend on any axioms" form) → []
    for match in AXIOM_NONE_RE.finditer(output):
        parsed.setdefault(match.group(1).strip(), [])
    return parsed


def _relative_to_or_self(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def run_lake_compile(target: Path, lean_root: Path, *, timeout_s: int) -> dict[str, Any]:
    """Run `lake env lean <target>` from `lean_root` and return a compile
    receipt with ok / returncode / elapsed / axioms / stdout_tail / stderr_tail.

    Same shape as `leanmill_proof_audit.run_compile` (which this replaces).
    """
    started = time.time()
    rel = _relative_to_or_self(target, lean_root)
    rc, stdout, stderr, timed_out = _run_lake_with_group_kill(
        ["lake", "env", "lean", rel], cwd=str(lean_root), timeout_s=timeout_s,
    )
    output = stdout + "\n" + stderr
    if timed_out:
        return {
            "command": ["lake", "env", "lean", rel],
            "cwd": str(lean_root),
            "returncode": None,
            "elapsed_s": round(time.time() - started, 3),
            "ok": False,
            "timed_out": True,
            "axioms": {},
            "stdout_tail": stdout[-1200:],
            "stderr_tail": stderr[-1200:],
        }
    return {
        "command": ["lake", "env", "lean", rel],
        "cwd": str(lean_root),
        "returncode": rc,
        "elapsed_s": round(time.time() - started, 3),
        "ok": _is_compile_ok(rc, output),
        "axioms": parse_axiom_output(output),
        "stdout_tail": stdout[-1200:],
        "stderr_tail": stderr[-1200:],
    }


def audit_axioms_subset(lean_source: str, target_name: str, lean_path: Path, lean_root: Path,
                        *, timeout_s: int = 180) -> "tuple[bool, bool, list[str]]":
    """Compile `lean_source` with a `#print axioms <target_name>` directive and check the TARGET's axioms ⊆
    AXIOM_ALLOWLIST ({propext, Classical.choice, Quot.sound}). This is the soundness gate that catches
    `native_decide`'s `Lean.ofReduceBool` (the trust-the-compiler escape) and any smuggled axiom — the audit
    that was MISSING on the cascade + `composite_ratify` closure paths (only the warm leaf ran it; bug-hunt
    #84 F1+F2).

    MASKING-SAFE: keys on `target_name`, so a DECOY `#print axioms helper` (clean) cannot hide a dirty target
    (the multi-`#print` masking trick).

    Returns (clean, confirmed_bad, axioms):
      • clean        — the target's axioms ⊆ the allowlist (a genuine, axiom-clean closure).
      • confirmed_bad — the target's axioms were FOUND and contain a BANNED axiom ⇒ the caller fails CLOSED.
      • axioms       — the sorted axiom list (for the receipt).
    A tooling error (target line absent ⇒ compile/directive failure) returns (False, False, []) so the caller
    fails OPEN — don't credit unaudited, but don't block a valid closure on a tooling hiccup (the kernel's
    fail-open-on-crash philosophy; a SUCCESSFUL compile always yields the line, so native_decide is caught)."""
    src = lean_source if f"#print axioms {target_name}" in (lean_source or "") else (
        (lean_source or "").rstrip() + f"\n#print axioms {target_name}\n")
    axioms_by_name: "dict | None" = None
    # WARM FAST PATH (2026-06-19): the cold `lake env lean` below RE-IMPORTS Mathlib (~100s+) on EVERY closure
    # audit — the recurring verify-starvation cost on a heavy campaign theory (a sub-lemma proof compiles, then
    # this audit re-elaborates Mathlib from scratch). #66 warm-routed `_compile_probe`/firewall but this audit
    # leg (added to composite_ratify + the cascade by #101) was missed. Route through the warm REPL when usable;
    # the RAW #print-axioms output is parsed by the SAME `parse_axiom_output` as cold ⇒ the F1/F2 allowlist gate
    # is byte-IDENTICAL (warm only amortizes elaboration, never relaxes the audit). `lean_root` is the sandbox the
    # warm REPL is keyed on. Falls back to cold on None (flag off / toolchain mismatch / dead REPL / non-compile).
    try:
        from ztare.formal.repl_compile import axioms_raw_via_repl
        _raw = axioms_raw_via_repl(src, target_name, Path(lean_root), timeout=timeout_s)
        if _raw is not None:
            axioms_by_name = parse_axiom_output(_raw)
    except Exception:  # noqa: BLE001 — warm path is best-effort; a failure just falls through to cold
        axioms_by_name = None
    if axioms_by_name is None:                # COLD FALLBACK — authoritative `lake env lean` audit
        try:
            Path(lean_path).write_text(src, encoding="utf-8")
            rec = run_lake_compile(Path(lean_path), Path(lean_root), timeout_s=timeout_s)
        except Exception:  # noqa: BLE001 — tooling error ⇒ inconclusive (caller fails OPEN)
            return (False, False, [])
        axioms_by_name = rec.get("axioms") or {}
    if target_name not in axioms_by_name:
        return (False, False, [])   # the directive produced no line for the target ⇒ inconclusive
    ax = set(axioms_by_name.get(target_name) or [])
    clean = ax.issubset(AXIOM_ALLOWLIST)
    return (clean, (not clean), sorted(ax))


def run_lake_compile_source(
    source: str, lean_root: Path, *, timeout_s: int,
    prefix: str = "leanmill_lake_compile_",
) -> tuple[bool | None, str]:
    """Write `source` to a scratch .lean file under the system tempdir,
    compile via `lake env lean`, return (compile_ok, output_tail).

    System tempdir is used (no hardcoded /private/tmp). Same semantics as
    `leanmill_proof_audit._run_temp_lean`.
    """
    with tempfile.TemporaryDirectory(prefix=prefix) as td:
        path = Path(td) / "Probe.lean"
        path.write_text(source, encoding="utf-8")
        try:
            rc, stdout, stderr, timed_out = _run_lake_with_group_kill(
                ["lake", "env", "lean", str(path)],
                cwd=str(lean_root), timeout_s=timeout_s,
            )
        except FileNotFoundError as exc:
            return False, f"lake not on PATH: {exc!s}"
        if timed_out:
            return False, "lake env lean timed out (process group killed)"
        output = stdout + "\n" + stderr
        ok = _is_compile_ok(rc, output)
        return ok, output[-1200:]


def probe_axioms_via_augment(
    source_text: str,
    declarations: list,
    lean_root: Path,
    *,
    timeout_s: int,
) -> tuple[dict[str, list[str]], str]:
    """Augment source with `#print axioms <name>` lines for each declaration
    and compile to extract axiom usage. Used when the source itself doesn't
    declare `#print axioms` directives (e.g. third-party proofs routed
    through the canonical external audit).

    `declarations` must be an iterable of objects with `.name` attributes
    (or string names; we accept both for flexibility). Returns (axiom_map,
    output_tail).
    """
    if not declarations:
        return {}, ""
    names = [getattr(d, "name", d) for d in declarations]
    print_lines = "\n".join(f"#print axioms {n}" for n in names)
    augmented = (
        source_text.rstrip()
        + "\n\n-- canonical axiom probe (lean_compile_primitives) --\n"
        + print_lines + "\n"
    )
    # FULL-OUTPUT axiom parse (char-length sibling sweep, RCA 2026-06-23): a MULTI-declaration probe emits one
    # `#print axioms <name>` block per decl; on a length-TRUNCATED tail (the old `run_lake_compile_source`
    # returned `output[-1200:]`) the EARLIEST blocks fall outside the window and silently drop from the audit —
    # the same truncated-baseline class as the anti-laundering `enriched_goal` hijack false-positive. Route
    # through the SAME full-output compile the live `audit_axioms_subset` uses (`run_lake_compile` parses
    # `rec["axioms"]` from the COMPLETE stdout+stderr, never a tail), so every probed decl is parsed regardless
    # of how many precede it. (A dropped block can only ever read as inconclusive — the closing-`]` regex +
    # fail-open posture mean truncation can never FALSE-PASS — but a complete audit is the correct primitive.)
    import tempfile as _tempfile
    with _tempfile.TemporaryDirectory(prefix="leanmill_axiom_probe_") as _td:
        _p = Path(_td) / "Probe.lean"
        _p.write_text(augmented, encoding="utf-8")
        rec = run_lake_compile(_p, Path(lean_root), timeout_s=timeout_s)
    _disp = ((rec.get("stdout_tail") or "") + (rec.get("stderr_tail") or ""))[-1500:]
    return (rec.get("axioms") or {}), _disp
