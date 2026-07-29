from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from ztare.leanmill import cold_calibration


def test_measure_cold_baseline_invokes_existing_absolute_temp_probe(
    tmp_path: Path, monkeypatch
) -> None:
    lean_root = tmp_path / "lean-project"
    lean_root.mkdir()
    baseline_file = tmp_path / "cold-baseline.json"
    seen: dict[str, object] = {}

    monkeypatch.setattr(cold_calibration, "_BASELINE_FILE", baseline_file)
    monkeypatch.setattr(cold_calibration, "_MEM_CACHE", {})
    ticks = iter((10.0, 11.25))
    monkeypatch.setattr(cold_calibration.time, "monotonic", lambda: next(ticks))

    def fake_run(argv, *, cwd, capture_output, text, timeout):
        probe = Path(argv[-1])
        seen.update(argv=argv, cwd=cwd, probe=probe, timeout=timeout)
        assert probe.is_absolute()
        assert probe.exists()
        assert probe.name == "ColdBaselineProbe.lean"
        assert probe.parent != lean_root
        assert cwd == str(lean_root)
        assert capture_output is True and text is True
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cold_calibration.subprocess, "run", fake_run)

    measured = cold_calibration.measure_cold_baseline(
        lean_root, ceiling_s=17, force=True
    )

    assert measured == 1.25
    assert seen["argv"][:3] == ["lake", "env", "lean"]
    assert seen["timeout"] == 17
    persisted = json.loads(baseline_file.read_text(encoding="utf-8"))
    assert persisted[str(lean_root.resolve())]["baseline_s"] == 1.2
