from __future__ import annotations

from types import SimpleNamespace


def test_warm_compile_failure_falls_through_to_cold_authority(
    tmp_path, monkeypatch
) -> None:
    from ztare.formal import repl_compile
    from ztare.gates import v33_preflight_risk_detector as gate

    monkeypatch.setattr(
        repl_compile,
        "compile_probe_via_repl",
        lambda *_args, **_kwargs: (False, "warm environment lacks imported module"),
    )
    cold_calls: list[object] = []

    def cold_compile(*args, **kwargs):
        cold_calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(gate.subprocess, "run", cold_compile)

    assert gate._compile_probe_standalone(
        "import Project.Module\n\ntheorem carried : True := by trivial\n",
        tmp_path,
        "RatificationProbe",
        10,
    ) is True
    assert len(cold_calls) == 1
