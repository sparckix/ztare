"""Static guard for the 'best-effort bare-except hides a NameError' bug CLASS (2026-06-22).

THE RECURRING BUG (memory: feedback_best_effort_bare_except_hides_bugs; "silently" appears ~7900× in the
session transcript): a telemetry / observability / best-effort helper is wrapped in `try: ... except Exception:
pass` and its body uses a STDLIB module name (`re`, `json`, `os`, `Path`, `time`, ...) that is NOT imported in
that scope. The reference raises `NameError` on EVERY call, the swallowing `except` hides it forever, and the
helper silently no-ops (a created-but-EMPTY output file is the classic signature). It bit us 3-4× because the
cure was treated as vigilance ("import stdlib names locally inside the try") — but vigilance does not scale.

The structural cure is a MECHANICAL scan, not a principle: flag a SWALLOWING `try/except` whose body uses a
known-stdlib module name with NO in-scope import (module-level OR a local `import` in the function). This is the
exact NameError-silent-no-op signature. It is deliberately CONSERVATIVE (a fixed stdlib name set, used as
`name.attr`, with any in-scope import — including an aliased `import re as _re`, whose *alias* is the used name —
clearing it) so the correct local-import pattern is never flagged.

Run:  python -m ztare.leanmill.except_audit            # exit 1 on a finding
      python -m ztare.leanmill.except_audit --list     # print every finding (advisory inventory)
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# The bare module names whose use inside a swallowing try/except, with no in-scope import, is the bug signature.
# (Aliased local imports — the FIX pattern, `import re as _re` → the used name is `_re`, not `re` — are immune
# because the alias is not in this set; an un-aliased local `import re` puts `re` in scope and clears it too.)
_STDLIB = frozenset({
    "re", "json", "os", "sys", "time", "math", "hashlib", "subprocess", "tempfile", "shutil", "glob",
    "itertools", "functools", "collections", "random", "datetime", "sqlite3", "Path", "urllib", "io",
    "pickle", "csv", "base64", "textwrap", "traceback", "importlib", "threading", "concurrent",
})


def _swallowing(handler: ast.ExceptHandler) -> bool:
    """A handler that HIDES the exception: it never re-raises (no bare `raise` in its body). `pass` / a bare
    `return` / `continue` / a lone `print`/log call are the canonical swallow forms; the only thing that makes
    a handler NON-swallowing is a `raise` (re-raise or raise-new)."""
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return False
    return True


def _imported_names(nodes: "list[ast.AST]") -> set:
    out: set = set()
    for top in nodes:
        for node in ast.walk(top):
            if isinstance(node, ast.Import):
                for a in node.names:
                    out.add((a.asname or a.name).split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    out.add(a.asname or a.name)
    return out


def scan_file(path: Path) -> "list[tuple[str, int, str, str]]":
    """Return [(file, line, func, name)] for each swallowed potential-NameError. Conservative — see module doc."""
    findings: "list[tuple[str, int, str, str]]" = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:  # a file that won't even parse is a different problem; this guard skips it
        return findings
    module_imports = _imported_names([tree])
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        in_scope = set(module_imports)
        in_scope |= _imported_names(list(fn.body))                       # local imports anywhere in the fn
        in_scope |= {a.arg for a in (fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs)}
        in_scope |= {t.id for n in ast.walk(fn) if isinstance(n, ast.Assign)
                     for t in n.targets if isinstance(t, ast.Name)}      # local rebinds (e.g. `time = ...`)
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Try) and any(_swallowing(h) for h in node.handlers)):
                continue
            seen: set = set()
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name)
                        and sub.value.id in _STDLIB and sub.value.id not in in_scope):
                    key = (sub.value.id, getattr(sub, "lineno", fn.lineno))
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append((str(path), getattr(sub, "lineno", fn.lineno), fn.name, sub.value.id))
    return findings


def scan_tree(root: "Path | None" = None) -> "list[tuple[str, int, str, str]]":
    root = root or (Path(__file__).resolve().parents[3] / "src" / "ztare" / "leanmill")
    findings: "list[tuple[str, int, str, str]]" = []
    for p in sorted(root.rglob("*.py")):
        findings.extend(scan_file(p))
    return findings


def main(argv: "list[str] | None" = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    findings = scan_tree()
    if not findings:
        print("OK — no swallowed-NameError patterns (stdlib name used in a swallowing try/except with no "
              "in-scope import).")
        return 0
    print(f"FOUND {len(findings)} swallowed-NameError candidate(s) — a stdlib name used inside a swallowing "
          "try/except with NO in-scope import (would NameError-then-silently-no-op):")
    for f, ln, fn, nm in findings:
        rel = f.split("/src/")[-1]
        print(f"  {rel}:{ln}  in {fn}()  uses `{nm}` with no in-scope import")
    print("\nFIX: add a local `import <name>` inside the function (or at module top), then RUN the helper once "
          "and confirm non-empty output. Never assume a best-effort writer fired.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
