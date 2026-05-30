from projects.ns_millennium_hunt.workspace.phase45_common import (
    lookup_threshold_metrics,
    stable_threshold_key,
)


def test_stable_threshold_key_preserves_0995():
    assert stable_threshold_key(0.9) == "0.90"
    assert stable_threshold_key(0.95) == "0.95"
    assert stable_threshold_key(0.99) == "0.99"
    assert stable_threshold_key(0.995) == "0.995"


def test_lookup_threshold_metrics_matches_by_alpha():
    snapshot = {
        "thresholds": {
            "0.99": {"alpha": 0.99, "volume": 2.0},
            "0.995": {"alpha": 0.995, "volume": 1.0},
        }
    }
    assert lookup_threshold_metrics(snapshot, 0.99)["volume"] == 2.0
    assert lookup_threshold_metrics(snapshot, 0.995)["volume"] == 1.0


def test_lookup_threshold_metrics_survives_legacy_key_shape():
    snapshot = {
        "thresholds": {
            "legacy_key": {"alpha": 0.995, "volume": 7.0},
        }
    }
    assert lookup_threshold_metrics(snapshot, 0.995)["volume"] == 7.0
