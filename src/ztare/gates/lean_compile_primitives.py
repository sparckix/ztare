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
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


def _run_lake_with_group_kill(
    cmd: list[str], cwd: str, *, timeout_s: int,
) -> tuple[int | None, str, str, bool]:
    """Spawn `cmd` in a new process group; on TimeoutExpired kill the WHOLE
    group via SIGKILL (so lake's lean child does not get reparented to init).
    Returns (returncode, stdout, stderr, timed_out)."""
    proc = subprocess.Popen(
        cmd, cwd=cwd, text=True,
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
LEAN_ERROR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)
_BARE_ERROR_RE = re.compile(r"(?m)^\s*error:")


def _is_compile_ok(rc: "int | None", output: str) -> bool:
    """Single compile oracle. A clean compile requires exit 0 AND no error
    line (positional OR bare/non-positional) AND no `sorry` warning. Lean
    emits "declaration uses 'sorry'" as a WARNING with exit 0, so a
    sorry-backed proof would otherwise read as a clean compile — fail it."""
    if rc != 0:
        return False
    if LEAN_ERROR_RE.search(output) or _BARE_ERROR_RE.search(output):
        return False
    if "uses 'sorry'" in output:
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
    ok, tail = run_lake_compile_source(
        augmented, lean_root, timeout_s=timeout_s,
        prefix="leanmill_axiom_probe_",
    )
    return parse_axiom_output(tail), tail[-1500:]
