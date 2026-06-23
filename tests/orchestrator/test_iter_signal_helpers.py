from ztare.orchestrator.iter_signal_helpers import weakest_point_text
from ztare.validator.core.information_yield import IterationSignal


def test_weakest_point_text_reads_current_iteration_signal_dataclass() -> None:
    signal = IterationSignal(
        iteration_index=3,
        score=42,
        weakest_point="same weakest point keeps repeating",
    )

    assert weakest_point_text(signal) == "same weakest point keeps repeating"


def test_weakest_point_text_preserves_legacy_dict_rows() -> None:
    assert weakest_point_text({"weakest_point": "legacy row"}) == "legacy row"
    assert weakest_point_text({}) == ""
    assert weakest_point_text(None) == ""
