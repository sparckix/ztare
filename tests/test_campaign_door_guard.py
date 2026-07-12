"""Campaign-door mislaunch REPORTER: warns on a bare campaign-shaped `autoformalize_from_notes()` call;
silent for every legitimate direct use (injected attack_fn, run_tag-armed, non-campaign shape, env-off).

Runnable: `python tests/test_campaign_door_guard.py`. ast-extracts the pure helper (no heavy solver imports).
"""
import ast
import os
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "src/ztare/leanmill/solver/autoformalize_notes.py"


def _load():
    ns: dict = {}
    for node in ast.parse(_SRC.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef) and node.name == "_campaign_door_warning":
            exec(compile(ast.Module([node], []), "<f>", "exec"), ns)
    return ns["_campaign_door_warning"]


def test_door_guard():
    warn = _load()
    for k in ("ZTARE_SOLVER_RUN_TAG", "ZTARE_LEANMILL_DOOR_GUARD"):
        os.environ.pop(k, None)
    # the mislaunch: bare call, campaign shape → warns, and the warning names the canonical launcher
    w = warn(attack_injected=False, target="prove no-arbitrage implies state prices")
    assert w and "leanmill campaign" in w, w
    # every legitimate use is silent
    assert warn(attack_injected=True, target="prove X") is None, "hermetic/self-test callers must not be nagged"
    os.environ["ZTARE_SOLVER_RUN_TAG"] = "notes_x_0702T0000"
    assert warn(attack_injected=False, target="prove X") is None, "main()/A-B-armed runs must not be nagged"
    del os.environ["ZTARE_SOLVER_RUN_TAG"]
    assert warn(attack_injected=False, target="") is None, "no ## Target parsed = not a campaign"
    os.environ["ZTARE_LEANMILL_DOOR_GUARD"] = "0"
    assert warn(attack_injected=False, target="prove X") is None, "env kill-switch must revert"
    del os.environ["ZTARE_LEANMILL_DOOR_GUARD"]
    print("OK: warns on bare campaign call; silent for injected/armed/non-campaign/env-off")


if __name__ == "__main__":
    test_door_guard()
