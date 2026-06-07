"""Canonical SANDBOXED-PYTHON execution — the ONE home for "run Python out-of-process" across ZTARE
(autoresearch + leanmill), 2026-06-07. Seeded from leanmill's `symbolic_witness.run_solver_script`.

Two execution shapes, ONE module (so neither subsystem rolls its own subprocess wrapper again):

  * run_guarded_script(script)  — run an UNTRUSTED (model-written) self-contained script STRING in an
    ISOLATED (`-I`) subprocess behind a STATIC import-whitelist (`script_is_safe`: only sympy/json/math/…,
    no os/subprocess/socket/open/eval). Used by leanmill's witness/counterexample transport (SymPy snippets).
    The import guard is the actual sandbox — it holds regardless of the env. Parses the LAST JSON line.

  * run_python_file / run_python_module  — run a TRUSTED on-disk `.py` file or `-m module` (e.g.
    autoresearch's generated `test_model.py` / the bridge evaluators). No import guard (the file is ours,
    not an untrusted snippet); a thin shared wrapper over `subprocess.run` so the bridge runners stop each
    re-implementing it.

SMT/Z3 would extend the guarded path here (absent today). See `reference_sympy_capability_no_smt`.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

# ── Static import-whitelist guard (for the UNTRUSTED guarded-script path) ──────────────────────────
_ALLOWED_IMPORTS = {"sympy", "json", "math", "fractions", "itertools", "functools", "re"}
# Forbidden bare tokens (the dangerous capabilities). NB: `locals`/`globals` are NOT here — they collide with
# the benign `sympify(..., locals=…)` kwarg and are only dangerous as CALLS, which require eval/exec/import
# (all blocked) to do anything. eval(/exec( call-forms are caught below.
_FORBIDDEN = re.compile(r"\b(?:os|sys|subprocess|socket|shutil|pathlib|open|__import__|"
                        r"input|importlib|urllib|requests|http|ctypes|pickle)\b")
_FORBIDDEN_CALL = re.compile(r"\b(?:eval|exec|compile)\s*\(")


def script_is_safe(script: str) -> bool:
    """Cheap STATIC guard before executing a (possibly model-written) script: every `import X`/`from X` must
    be in the allow-list, and no forbidden token (os/subprocess/socket/open/eval/…) may appear anywhere."""
    if not script or not script.strip():
        return False
    for m in re.finditer(r"^\s*(?:from\s+([\w.]+)|import\s+([\w.]+(?:\s*,\s*[\w.]+)*))", script, re.MULTILINE):
        mods = (m.group(1) or m.group(2) or "")
        for mod in re.split(r"\s*,\s*", mods):
            if mod.split(".")[0].strip() not in _ALLOWED_IMPORTS:
                return False
    return _FORBIDDEN.search(script) is None and _FORBIDDEN_CALL.search(script) is None


def run_guarded_script(script: str, timeout_s: int = 10, python_bin: "str | None" = None) -> "dict | None":
    """Run an UNTRUSTED self-contained script in a bounded, import-whitelisted, ISOLATED (`-I`) subprocess;
    return the LAST JSON object it prints to stdout (or None: unsafe / timeout / no JSON / error). Script
    contract: print one JSON object, e.g. `{"ok": true, "witnesses": ["6"]}`. The env is INHERITED (stripping
    it broke SymPy's solve under `-I` and gave no real isolation — the import guard IS the sandbox)."""
    if not script_is_safe(script):
        return None
    import tempfile  # local: only needed on the execute path
    py = python_bin or sys.executable
    try:
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run([py, "-I", "-c", script], capture_output=True, text=True,
                                  timeout=max(1, timeout_s), cwd=td)
    except (subprocess.TimeoutExpired, OSError):
        return None
    out = (proc.stdout or "").strip()
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                d = json.loads(line)
                return d if isinstance(d, dict) else None
            except json.JSONDecodeError:
                continue
    return None


def run_python_file(path, cwd=None, timeout_s: "int | None" = None,
                    python_bin: "str | None" = None) -> "subprocess.CompletedProcess[str]":
    """Run a TRUSTED on-disk `.py` file (e.g. a generated `test_model.py`) and capture stdout/stderr. No import
    guard — the file is ours. Shared so the autoresearch bridge/meta runners stop re-implementing this."""
    from pathlib import Path
    p = Path(path)
    return subprocess.run([python_bin or sys.executable, str(p)],
                          cwd=str(cwd) if cwd is not None else None,
                          capture_output=True, text=True,
                          timeout=timeout_s)


def run_python_module(module_name: str, cwd=None, args: "list[str] | None" = None,
                      timeout_s: "int | None" = None, python_bin: "str | None" = None,
                      check: bool = False) -> "subprocess.CompletedProcess[str]":
    """Run a TRUSTED `-m module` (the bridge/meta-runner pattern). Captures output unless the caller wants a
    raw passthrough; `check=True` raises on non-zero (the `subprocess.run(check=True)` callers)."""
    cmd = [python_bin or sys.executable, "-m", module_name, *(args or [])]
    return subprocess.run(cmd, cwd=str(cwd) if cwd is not None else None,
                          capture_output=True, text=True, timeout=timeout_s, check=check)


def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    ok("safe: pure sympy passes", script_is_safe("import sympy, json\nprint('{}')"))
    ok("safe: os rejected", not script_is_safe("import os\nimport sympy"))
    ok("safe: comma-import os rejected", not script_is_safe("import sympy, os\n"))
    ok("safe: subprocess token rejected", not script_is_safe("import sympy\nsubprocess.run(['x'])"))
    ok("safe: eval-call rejected", not script_is_safe("import json\neval('1+1')"))
    ok("safe: empty rejected", not script_is_safe(""))
    ok("guarded: unsafe blocked", run_guarded_script("import os\nprint('{}')") is None)
    ok("guarded: parses last JSON amid noise",
       (run_guarded_script("import json\nprint('warn')\nprint(json.dumps({'ok':True}))") or {}).get("ok") is True)
    # trusted-file runner (no guard): run a tiny inline-as-module check via -c is not a file, so test module path
    cp = run_python_module("json.tool", args=["--help"])
    ok("trusted module runner returns CompletedProcess", hasattr(cp, "returncode"))

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
