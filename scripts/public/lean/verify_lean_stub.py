#!/usr/bin/env python3
"""GP-135 P4 gate enforcement — Lean stub verifier with axiom allowlist.

Per external Lean panelist review of the ztare_on_ztare score-92 thesis:
"lake build succeeds" does not guarantee mathematical truth; it only
guarantees well-typedness. To close the statement-fidelity gap, the gate
must additionally:

  1. Compile the stub with `set_option warningAsError true` so `sorry`
     becomes a hard error. (Emitted by `lean_compiler --strict`.)
  2. After successful compile, parse `#print axioms <thm>` for each
     theorem declared in the file and reject any axiom outside the
     allowlist {propext, Classical.choice, Quot.sound}.
  3. Lexically scan the source for `sorry`, `admit`, `native_decide`,
     and standalone `axiom` declarations — belt-and-braces check in
     case warningAsError is bypassed.
  4. Prefer `lean --check` against a pre-built cache over `lake build`
     for per-candidate throughput (target: 1-3 s per candidate).

This script is the POST-COMPILE side of the P4 gate. The PRE-COMPILE
side (strict preamble) lives in src/ztare/formal/lean_compiler.py.

Usage:
    python scripts/public/lean/verify_lean_stub.py --stub <path.lean>
    python scripts/public/lean/verify_lean_stub.py --project ztare_on_ztare
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# Axioms every Lean 4 development implicitly depends on; these are OK.
ALLOWED_AXIOMS = frozenset({
    "propext",
    "Classical.choice",
    "Quot.sound",
})

# Patterns that indicate the stub bypasses the correctness-tax.
FORBIDDEN_TOKENS = (
    "sorry",
    "admit",
    "native_decide",     # trusts compiled code, not kernel-checked
    "\naxiom ",          # user-declared axioms (leading newline anchors)
    # Compiler-trust AXIOM names (2026-06-08). `native_decide` elaborates to `Lean.ofReduceBool`
    # (and the compiler-trust path to `Lean.trustCompiler`) — axioms OUTSIDE the allowlist that the
    # `#print axioms` audit already rejects. Banning the NAMES lexically closes the gap where a stub
    # cites the axiom DIRECTLY (`exact Lean.ofReduceBool …`) on a path that skips the axiom audit.
    # Zero false-positive: these identifiers never appear in legitimate kernel-checked proof source
    # (unlike `partial`/`unsafe`/`@[extern]`, which DO occur in trusted preludes — deliberately NOT
    # banned here to avoid prelude false-positives; the `#print axioms` allowlist is their real gate).
    "Lean.ofReduceBool",
    "Lean.trustCompiler",
    "ofReduceBool",      # the unqualified form (under `open Lean`)
)


def _strip_comments(source: str) -> str:
    """Remove Lean comments so the lexical scanner only sees code.

    Handles both `--` line comments and `/- … -/` block comments
    (including nested block comments per Lean spec).
    """
    out: list[str] = []
    i = 0
    n = len(source)
    depth = 0  # block-comment nesting depth
    while i < n:
        if depth > 0:
            if source.startswith("/-", i):
                depth += 1
                i += 2
            elif source.startswith("-/", i):
                depth -= 1
                i += 2
            else:
                # preserve newlines so line numbers stay stable
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            continue
        if source.startswith("/-", i):
            depth = 1
            i += 2
            continue
        if source.startswith("--", i):
            # consume to end of line
            j = source.find("\n", i)
            if j == -1:
                break
            out.append("\n")
            i = j + 1
            continue
        out.append(source[i])
        i += 1
    return "".join(out)


def lexical_scan(source: str) -> list[str]:
    """Scan source (with comments stripped) for forbidden tokens."""
    code = _strip_comments(source)
    violations: list[str] = []
    for i, line in enumerate(code.splitlines(), 1):
        for tok in FORBIDDEN_TOKENS:
            pat = tok.strip()
            if re.search(rf"\b{re.escape(pat)}\b", line):
                # show the original line for context, not the stripped one
                orig_line = source.splitlines()[i - 1] if i <= len(source.splitlines()) else line
                violations.append(f"  line {i}: '{pat}' — {orig_line.rstrip()[:100]}")
    return violations


def extract_theorem_names(source: str) -> list[str]:
    """Grab all top-level `theorem NAME` declarations."""
    return re.findall(r"^\s*theorem\s+(\w+)", source, flags=re.MULTILINE)


def build_and_check(stub_path: Path, timeout: int = 300) -> tuple[bool, str]:
    """Run `lake build` on the file's parent project. Returns (ok, output)."""
    project = stub_path.parent
    # Prefer lake build from the parent if lakefile exists; else lean --check
    lakefile = project / "lakefile.lean"
    lakefile_toml = project / "lakefile.toml"
    if lakefile.exists() or lakefile_toml.exists():
        cmd = ["lake", "build"]
        cwd = str(project)
    else:
        # Fall back to standalone lean --check (requires lean in PATH + no Mathlib)
        cmd = ["lean", "--check", str(stub_path)]
        cwd = str(project)
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        return res.returncode == 0, res.stdout + res.stderr
    except FileNotFoundError:
        return False, f"lean toolchain not installed (tried: {' '.join(cmd)})"
    except subprocess.TimeoutExpired:
        return False, f"compilation timed out after {timeout}s"


def print_axioms(stub_path: Path, theorem: str, timeout: int = 60) -> tuple[bool, set[str]]:
    """Run `lean` in a mode that emits `#print axioms <theorem>` output.

    Returns (ok_to_parse, set_of_axiom_names_observed).
    Non-zero returncode or parse failure → (False, set()) which the caller
    should treat as "cannot verify → fail the gate."
    """
    project = stub_path.parent
    # Compose a small driver file: import the stub, print its axioms.
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".lean", dir=project, delete=False, encoding="utf-8"
    ) as fh:
        fh.write(f"import {stub_path.stem}\n\n#print axioms {theorem}\n")
        driver = Path(fh.name)
    try:
        res = subprocess.run(
            ["lean", str(driver)], capture_output=True, text=True,
            timeout=timeout, cwd=str(project),
        )
        output = res.stdout + res.stderr
        # `#print axioms` emits: "'<thm>' depends on axioms: [ax1, ax2, ...]"
        # or "'<thm>' does not depend on any axioms"
        axioms: set[str] = set()
        m = re.search(r"depends on axioms:\s*\[(.+?)\]", output, re.DOTALL)
        if m:
            axioms = {a.strip() for a in m.group(1).split(",") if a.strip()}
        elif "does not depend on any axioms" in output:
            axioms = set()
        else:
            return (False, set())
        return (True, axioms)
    finally:
        driver.unlink(missing_ok=True)


def verify_stub(stub_path: Path, strict: bool = True) -> dict:
    """Full P4-gate verification. Returns structured verdict."""
    verdict = {
        "stub": str(stub_path),
        "passed": False,
        "failures": [],
        "warnings": [],
    }

    if not stub_path.exists():
        verdict["failures"].append(f"stub does not exist: {stub_path}")
        return verdict

    source = stub_path.read_text(encoding="utf-8")

    # Step 1: lexical scan for forbidden tokens
    lex_viols = lexical_scan(source)
    if lex_viols:
        verdict["failures"].append(
            "Lexical scan found forbidden tokens:\n" + "\n".join(lex_viols)
        )
        return verdict

    # Step 2: compile / type-check
    ok, output = build_and_check(stub_path)
    if not ok:
        verdict["failures"].append(f"compile failed:\n{output[:800]}")
        return verdict

    # Step 3: axiom allowlist on each theorem
    theorems = extract_theorem_names(source)
    if not theorems:
        verdict["warnings"].append("no `theorem` declarations found in stub")
    else:
        for thm in theorems:
            ok_parse, axioms = print_axioms(stub_path, thm)
            if not ok_parse:
                verdict["failures"].append(
                    f"could not parse `#print axioms {thm}` output; "
                    f"treating as gate failure"
                )
                continue
            unauthorized = axioms - ALLOWED_AXIOMS
            if unauthorized:
                verdict["failures"].append(
                    f"theorem `{thm}` depends on unauthorized axioms: "
                    f"{sorted(unauthorized)} (allowlist: {sorted(ALLOWED_AXIOMS)})"
                )

    verdict["passed"] = not verdict["failures"]
    return verdict


def _lexical_selftest() -> int:
    """Calibrated POSITIVE + NEGATIVE controls for `lexical_scan` (dead-instrument discipline: a banned
    token MUST be caught AND a legitimate proof / a trusted prelude MUST NOT be flagged). Run via
    `--selftest`; deterministic, no Lean toolchain needed."""
    cases = [
        ("POS sorry", "theorem t : True := by sorry", True),
        ("POS admit", "theorem t : True := by admit", True),
        ("POS native_decide", "theorem t : (2+2=4) := by native_decide", True),
        ("POS ofReduceBool (qualified)", "theorem t : True := by exact Lean.ofReduceBool h", True),
        ("POS ofReduceBool (open Lean)", "open Lean\ntheorem t : True := by exact ofReduceBool h", True),
        ("POS trustCompiler", "theorem t : True := by exact Lean.trustCompiler", True),
        ("POS standalone axiom", "axiom bad : False\ntheorem t : False := bad", True),
        ("NEG clean decide", "theorem t : (List.range 5).sum = 10 := by decide", False),
        ("NEG clean term", "theorem t : 1 = 1 := rfl", False),
        ("NEG partial-def prelude (no FP)",
         "partial def helper (n : Nat) : Nat := helper (n+1)\ntheorem t : 1 = 1 := rfl", False),
        ("NEG unsafe/extern prelude (no FP)",
         "@[extern \"c_fn\"] unsafe def f : Nat := 0\ntheorem t : 1 = 1 := rfl", False),
        ("NEG comment mentions ofReduceBool (stripped)",
         "-- we avoid Lean.ofReduceBool here\ntheorem t : 1 = 1 := rfl", False),
    ]
    fails = []
    for name, src, expect in cases:
        flagged = len(lexical_scan(src)) > 0
        ok = flagged == expect
        if not ok:
            fails.append(name)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: flagged={flagged} expect={expect}")
    print("LEXICAL SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--stub", help="Path to the .lean stub file")
    g.add_argument(
        "--project", help="Project name (stub at projects/<name>/<name>.lean)"
    )
    g.add_argument("--selftest", action="store_true",
                   help="Run the calibrated lexical-scan controls (no Lean toolchain needed)")
    ap.add_argument("--json", action="store_true", help="Emit verdict as JSON")
    args = ap.parse_args()

    if args.selftest:
        return _lexical_selftest()

    if args.stub:
        stub_path = Path(args.stub).resolve()
    else:
        stub_path = REPO / "projects" / args.project / f"{args.project}.lean"

    verdict = verify_stub(stub_path)

    if args.json:
        print(json.dumps(verdict, indent=2))
    else:
        print(f"=== P4 gate verification: {stub_path.name} ===")
        print(f"Passed: {verdict['passed']}")
        for f in verdict["failures"]:
            print(f"  ❌ {f}")
        for w in verdict["warnings"]:
            print(f"  ⚠️  {w}")

    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    main()
