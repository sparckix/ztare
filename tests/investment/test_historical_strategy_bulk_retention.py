import json
import os
import zipfile

from ztare.investment.historical_strategy_bulk_corpus import _logical_archive_delta


def test_logical_archive_delta_keeps_only_information_lost_by_successor(tmp_path):
    older, successor = tmp_path / "older.zip", tmp_path / "successor.zip"
    stable = os.urandom(64 * 1024)
    with zipfile.ZipFile(older, "w") as bundle:
        bundle.writestr("changed.json", b"old")
        bundle.writestr("stable.json", stable)
    with zipfile.ZipFile(successor, "w") as bundle:
        bundle.writestr("changed.json", b"new")
        bundle.writestr("stable.json", stable)
        bundle.writestr("new.json", b"later")

    receipt = _logical_archive_delta(older, successor, tmp_path / "deltas")

    assert receipt["status"] == "logical_delta_verified"
    with zipfile.ZipFile(receipt["delta_path"]) as delta:
        manifest = json.loads(delta.read("__jaggedthoughts__/manifest.json"))
        assert delta.read("changed.json") == b"old"
        assert "stable.json" not in delta.namelist()
        assert manifest["successor_only_members"] == ["new.json"]
