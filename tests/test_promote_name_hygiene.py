"""Publish-boundary name hygiene (promote): banking hashes stripped consistently; collisions left intact.

The rename must be a *consistent* alpha-rename (decl + every reference + the `#print axioms` line) so the kernel
verdict is unchanged, and it must NOT force-merge a hashed name onto a clean sibling (Shamir's `_conjN__hash`
alongside clean `_conjN`). Runnable: `python tests/test_promote_name_hygiene.py`.
"""
import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))  # the fn routes through lean_source now

_SRC = pathlib.Path(__file__).resolve().parents[1] / "scripts/public/control/leanmill/promote_campaign_artifact.py"


def _load_clean():
    ns: dict = {}
    for node in ast.parse(_SRC.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef) and node.name == "_clean_public_names":
            exec(compile(ast.Module([node], []), "<f>", "exec"), ns)  # extract without importing the CLI module
    return ns["_clean_public_names"]


def test_strip_and_collision():
    clean = _load_clean()
    body = "\n".join([
        "theorem foo__c64ef761 : True := by trivial",
        "theorem uses_foo : True := foo__c64ef761",   # a reference must be renamed too
        "#print axioms foo__c64ef761",                # the print line too
        "theorem bar : True := by trivial",           # clean sibling
        "theorem bar__deadbeef : True := by trivial", # base `bar` collides → MUST be left hashed
    ])
    cleaned, renames, residual = clean(body)
    assert renames == {"foo__c64ef761": "foo"}, renames
    assert "foo__c64ef761" not in cleaned, "consistent rename left a dangling hashed reference"
    assert cleaned.count("foo") >= 3, "decl + ref + #print should all read `foo`"
    assert residual == ["bar__deadbeef"], residual
    assert "bar__deadbeef" in cleaned, "collision case must be left intact, never force-merged onto `bar`"
    print("OK: strip consistent, collision skipped")


if __name__ == "__main__":
    test_strip_and_collision()
