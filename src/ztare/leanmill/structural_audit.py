"""Static guards for the ACCRETED-PARALLEL-PATH bug class — the root cause behind the recurring leanmill bugs
(2026-06-22). The 316-RCA history clusters into a few classes; the deepest is "N implementations of M core
concepts," so a fix in one copy rots the others (the forgotten-sibling class) and new parallel paths sneak in
(the pool-closure-drop class). Two mechanical guards, because the cure for the CLASS is enforcement, not
vigilance:

  1. DUPLICATE FUNCTION BODIES — two functions in DIFFERENT files with byte-identical logic (same AST). This is
     the canonical missed-sibling shape: the kernel type-equiv oracle once lived as two byte-identical copies
     (`lean_proof_gate._kernel_type_equiv_fn` + `solver_core._target_type_equiv_fn`); generalizing one left the
     other stale → a whole campaign false-rejected. Flags non-trivial cross-file duplicates so they are
     consolidated to one canonical home (callers re-export), never hand-synced.

  2. RATIFICATION CHOKEPOINT — the soundness stamp `UPDATE attempts SET ratified` must have exactly ONE writer
     (`_record_governance_verdict`). A second writer is a PARALLEL ratification path — precisely how the pool
     "closed" telemetry diverged from real governance. Assert the single chokepoint so a new ratified-writer
     fails CI (review it: route through the chokepoint, or justify the exception explicitly).

Run:  python -m ztare.leanmill.structural_audit          # exit 1 on any finding
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

_LEANMILL = Path(__file__).resolve().parent

# Boilerplate whose bodies are legitimately similar across files (selftests, dunders, trivial delegators).
_EXCLUDE_NAMES = frozenset({
    "_selftest", "_self_test", "selftest", "main", "__init__", "__repr__", "__eq__", "__hash__",
    "__str__", "setUp", "_run", "run", "_main",
})
# A function body of fewer than this many AST nodes is too trivial to be a meaningful "duplicate" (a getter,
# a one-line delegator). Tuned so the kernel-equiv-oracle-class (a real ~15-line function) is caught while
# trivial shims are not.
_MIN_BODY_NODES = 28
# The ONLY function permitted to write the ratification stamp (the single soundness chokepoint).
_RATIFIED_WRITER = "_record_governance_verdict"


def _body_without_docstring(fn: ast.AST) -> "list[ast.stmt]":
    body = list(getattr(fn, "body", []))
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]   # drop the docstring
    return body


def _is_trivial_delegator(body: "list[ast.stmt]") -> bool:
    """A body that is just `return <call/expr>` (+ maybe one local import) — an intentional re-export shim."""
    stmts = [s for s in body if not isinstance(s, (ast.Import, ast.ImportFrom))]
    return len(stmts) <= 1


def _module_level_functions(tree: ast.AST) -> "list[ast.AST]":
    """Module-level functions + class methods — NOT functions nested inside another function. Nested defs are
    local helpers (e.g. the selftest `ok(name, cond)` idiom repeated in every module's `_selftest`); they are
    legitimately duplicated and are not the forgotten-sibling risk (which is duplicated TOP-LEVEL logic)."""
    out: "list[ast.AST]" = []

    def visit(node: ast.AST, inside_fn: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not inside_fn:
                    out.append(child)
                visit(child, True)        # descend, but nested defs are excluded from `out`
            else:
                visit(child, inside_fn)
    visit(tree, False)
    return out


def duplicate_function_bodies(root: "Path | None" = None) -> "list[list[tuple[str, str, int]]]":
    """Groups of [(file, func, line)] whose function bodies are AST-identical across ≥2 distinct files."""
    root = root or _LEANMILL
    by_hash: "dict[str, list[tuple[str, str, int]]]" = {}
    for p in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        for fn in _module_level_functions(tree):
            if fn.name in _EXCLUDE_NAMES:
                continue
            body = _body_without_docstring(fn)
            if not body or _is_trivial_delegator(body):
                continue
            wrapped = ast.Module(body=body, type_ignores=[])
            if len(list(ast.walk(wrapped))) < _MIN_BODY_NODES:
                continue
            key = ast.dump(wrapped, annotate_fields=False)   # identifier names INCLUDED → byte-identical logic
            by_hash.setdefault(key, []).append((str(p), fn.name, getattr(fn, "lineno", 0)))
    out = []
    for members in by_hash.values():
        files = {m[0] for m in members}
        if len(members) >= 2 and len(files) >= 2:   # cross-FILE duplicate logic = the forgotten-sibling shape
            out.append(sorted(members))
    return out


def ratification_chokepoint_violations(root: "Path | None" = None) -> "list[tuple[str, str, int]]":
    """Functions OTHER than the single chokepoint that write the ratification stamp (`SET ratified`)."""
    root = root or _LEANMILL
    viol: "list[tuple[str, str, int]]" = []
    for p in sorted(root.rglob("*.py")):
        if p.name.endswith("_audit.py"):
            continue   # the meta-guards (flag_audit/except_audit/structural_audit) carry detection-pattern
            #            strings ("SET ratified", etc.) by design — they are not production write paths.
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name == _RATIFIED_WRITER:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and "set ratified" in node.value.lower():
                    viol.append((str(p), fn.name, getattr(fn, "lineno", 0)))
                    break
    return viol


def main(argv: "list[str] | None" = None) -> int:
    dups = duplicate_function_bodies()
    chokepoint = ratification_chokepoint_violations()
    rc = 0
    if dups:
        rc = 1
        print(f"FOUND {len(dups)} cross-file duplicate function body group(s) (the forgotten-sibling shape — "
              "consolidate to ONE canonical home; callers re-export):")
        for grp in dups:
            print("  duplicate logic:")
            for f, fn, ln in grp:
                print(f"    {f.split('/src/')[-1]}:{ln}  {fn}()")
    if chokepoint:
        rc = 1
        print(f"FOUND {len(chokepoint)} parallel ratification-stamp writer(s) (the chokepoint is "
              f"`{_RATIFIED_WRITER}` — route through it or justify):")
        for f, fn, ln in chokepoint:
            print(f"    {f.split('/src/')[-1]}:{ln}  {fn}() writes `SET ratified`")
    if rc == 0:
        print("OK — no cross-file duplicate function bodies; ratification stamp has a single chokepoint "
              f"(`{_RATIFIED_WRITER}`).")
    return rc


if __name__ == "__main__":
    sys.exit(main())
