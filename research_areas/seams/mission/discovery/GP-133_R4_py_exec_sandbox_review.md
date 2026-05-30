# GP-133 Round 4 — `py_exec` Sandbox Engineering Review

> **Seam metadata** · `seam_id:` GP-133 · `track:` mission · `status:` advisory; not a panel consensus, a code-review pass · `last_updated:` 2026-05-08


**Date:** 2026-04-23
**Status:** advisory; not a panel consensus, a code-review pass
**Scope:** security hardening of `src/ztare/fit/fit_primitive.py` lines 269-312 (py_exec path)

This review was deferred by the GP-133 Round 4 panel (epistemology-focused). Reading the code, this is what I'd flag.

## Current sandbox structure

```python
_PY_EXEC_BUILTINS = {
    "range", "sum", "len", "int", "round",
    "all", "any", "abs", "min", "max",
    "list", "sorted", "enumerate", "zip",
    "bool", "float", "str", "tuple", "set",
    "divmod", "pow", "True", "False", "None",
}

code = compile(declaration.expression, "<py_exec>", "eval")
# ...
out[i] = float(eval(code, {"__builtins__": {}}, ns))
```

## What's correct

- `compile(..., "eval")` syntactically prevents statements: no `import`, no `def`, no `class`, no assignment, no `for/while` (comprehensions ok), no `try/except`.
- Empty `{"__builtins__": {}}` blocks `__import__`, `open`, `exec`, `compile`, `eval`, `input`, `getattr` being bound by default.
- Whitelist excludes reflection: no `getattr`, `setattr`, `hasattr`, `vars`, `dir`, `globals`, `locals`, `type`.

## Concerns — ordered by severity

### 1. Classic `__subclasses__` escape via tuple/list/str `__class__` (medium-high)

The following expression is a legal Python expression under `compile(..., "eval")` and does not require any blocked builtin:

```python
().__class__.__base__.__subclasses__()
```

Returns a list of ALL loaded classes, which typically contains `<class '_frozen_importlib.BuiltinImporter'>`. Once you have `BuiltinImporter`, you can call its `load_module` to import arbitrary modules — `os`, `subprocess`, etc.

Equivalent attack vectors:
- `[].__class__.__base__.__subclasses__()`
- `"".__class__.__base__.__subclasses__()`
- `set().__class__.__base__.__subclasses__()`

**Why the current sandbox doesn't stop this:** the blocked-builtins dict only affects NAME lookups. Attribute access on an already-constructed value (empty tuple literal) bypasses builtins entirely — Python just walks the object's MRO.

### 2. Empty-dict `__builtins__` is less safe than `None` (low-medium)

`{"__builtins__": {}}` is documented to work for sandboxing, but CPython has historically leaked default builtins in certain import-adjacent contexts. Probably fine in CPython 3.13 for this specific code path, but not the tightest spelling.

### 3. `math` module access is broad (low)

`math` is passed into `ns` as a whole module. In principle fine for number theory, but the whitelist of allowed `math` attributes on the `eml_only` path (`_ALLOWED_MATH_ATTRS`, `_EML_ONLY_CONSTANT_ATTRS`) is NOT applied to the `py_exec` path. If math ever gains a reflection-adjacent attribute (`math.__loader__` in a future CPython, say), it becomes an escape vector.

### 4. No expression complexity / time limit (medium)

An LLM can write `sum(1 for _ in range(10**9))` — legal under the current whitelist, computes for minutes to hours per evaluation. Multiplied by curve_fit's many iterations, this is a DoS vector on the apparatus itself. Not exfil, just resource exhaustion.

### 5. `pow(2, 10**10)` — memory blowup (medium)

`pow(2, 10000000)` is a legal expression that computes a very large integer, consuming memory proportional to the result size. `expression_byte_budget` limits source length but not runtime compute.

## Recommended hardenings (in order of effort)

### Cheap and decisive: AST pre-check that rejects `__` attribute access

```python
import ast

def _validate_py_exec_expression(expression: str) -> None:
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError(
                f"py_exec sandbox: dunder/private attribute access not allowed ({node.attr!r}). "
                f"This defeats the classic .__class__.__base__.__subclasses__() escape."
            )
```

This single check closes Concerns #1 and #3 together. ~15 LOC. **Should ship before next py_exec run.**

### Medium effort: wall-clock timeout on `eval`

Wrap `eval` in `signal.alarm`-based timeout (Unix only) or subprocess with timeout (portable). Closes Concern #4. ~30 LOC.

### Higher effort: full RestrictedPython adoption

Replace hand-rolled sandbox with `RestrictedPython` (well-audited Zope library). Closes all Concerns but adds a dependency. Defer to v2.

## What the principal should do

- **Today:** ship the AST pre-check for `__`-attribute access (~15 LOC). This closes the `__subclasses__` escape with minimum friction.
- **Before any py_exec run on shared infra or CI:** add wall-clock timeout.
- **Before py_exec is advertised externally:** migrate to RestrictedPython OR commission a dedicated security review.

## Feed-back into GP-133 Round 4

Add as an explicit action item: **"Item 6.1: ship AST pre-check for `__`-attribute access in `fit_primitive.py::_build_model_callable` before the next py_exec run on any substrate other than principal's laptop."** Minimum-viable hardening; the rest can follow.

## Caveat

Static-review quality, not live-exploit-confirmed. I did NOT execute any escape expressions against the live sandbox. A dedicated penetration-test pass is a legitimate separate exercise.
