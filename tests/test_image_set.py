"""Tests for ImageMaintainingSet — functoriality invariant, saturation, growth_rate."""
import random

import pytest

from ztare.common.image_set import ImageMaintainingSet, classify_image_growth


def test_image_growth_separates_expansion_blindness_and_exhaustion():
    assert classify_image_growth(
        prior_raw={"a"}, current_raw={"b"}, prior_image={1}, current_image={2}
    ) == "expanding"
    assert classify_image_growth(
        prior_raw={"a"}, current_raw={"b"}, prior_image={1}, current_image={1}
    ) == "alpha_blind"
    assert classify_image_growth(
        prior_raw={"a"}, current_raw={"a"}, prior_image={1}, current_image={1}
    ) == "exhausted"


def _mod10(x):
    return hash(x) % 10


def _always_zero(x):
    return 0


def test_functoriality_invariant_passes():
    """check_invariant must pass for a pointwise functor after random adds."""
    s = ImageMaintainingSet(functors={"h": _mod10})
    rng = random.Random(42)
    for _ in range(200):
        s.add(rng.randint(0, 1000))
    s.check_invariant("h")  # should not raise


def test_image_size_matches_expected():
    """10 distinct elements with fn=identity → image size == 10."""
    s = ImageMaintainingSet(functors={"id": lambda x: x})
    for i in range(10):
        s.add(i)
    assert len(s) == 10
    assert len(s.image("id")) == 10


def test_duplicate_add_does_not_grow():
    """Adding the same element twice is idempotent."""
    s = ImageMaintainingSet(functors={"h": _mod10})
    s.add(42)
    s.add(42)
    assert len(s) == 1


def test_saturated_returns_true_quickly():
    """A functor that always returns 0 saturates after the first add."""
    s = ImageMaintainingSet(functors={"zero": _always_zero})
    for i in range(20):
        s.add(i)
    assert s.saturated("zero", window=5)


def test_saturated_false_when_growing():
    """Identity functor on distinct elements never saturates in a short window."""
    s = ImageMaintainingSet(functors={"id": lambda x: x})
    for i in range(10):
        s.add(i)
    assert not s.saturated("id", window=5)


def test_growth_rate_approaches_zero_on_saturation():
    """After saturation the growth_rate should be much lower than 1.0."""
    s = ImageMaintainingSet(functors={"zero": _always_zero})
    for i in range(50):
        s.add(i)
    assert s.growth_rate("zero") < 0.1


def test_contains_and_contains_image():
    s = ImageMaintainingSet(functors={"mod3": lambda x: x % 3})
    s.add(6)  # carrier = 0
    assert 6 in s
    assert s.contains_image("mod3", 0)
    assert not s.contains_image("mod3", 1)
    assert 7 not in s


def test_check_invariant_raises_on_tamper():
    """Manually corrupting the internal image should be caught by check_invariant."""
    s = ImageMaintainingSet(functors={"h": _mod10})
    for i in range(5):
        s.add(i)
    # corrupt the image
    s._images["h"].add(999)
    with pytest.raises(AssertionError):
        s.check_invariant("h")


def test_register_backfills():
    """register() on a non-empty set backfills the image correctly."""
    s = ImageMaintainingSet()
    for i in range(5):
        s.add(i)
    s.register("mod2", lambda x: x % 2)
    s.check_invariant("mod2")
    assert s.image("mod2") == frozenset({0, 1})


def test_image_returns_frozenset():
    s = ImageMaintainingSet(functors={"h": _mod10})
    s.add(1)
    assert isinstance(s.image("h"), frozenset)


# --- three additions from external review ---

def test_unhashable_carrier_raises_loud():
    """Functor returning a list raises TypeError naming the functor and type."""
    s = ImageMaintainingSet(functors={"bad": lambda x: [x]})
    with pytest.raises(TypeError, match="functor 'bad' returned unhashable list"):
        s.add(1)


def test_canonicalize_hook_coerces_unhashable():
    """canonicalize= hook converts list → tuple so it becomes hashable."""
    s = ImageMaintainingSet(
        functors={"f": lambda x: [x % 3]},
        canonicalize={"f": tuple},
    )
    s.add(1)
    s.add(4)  # same carrier as 1 mod 3
    assert s.contains_image("f", (1,))


def test_compression_ratio():
    """compression_ratio approaches 1.0 for an injective functor."""
    s = ImageMaintainingSet(functors={"id": lambda x: x})
    for i in range(10):
        s.add(i)
    assert s.compression_ratio("id") == 1.0


def test_compression_ratio_low_for_saturating_fn():
    """compression_ratio is low when many elements map to the same carrier."""
    s = ImageMaintainingSet(functors={"zero": _always_zero})
    for i in range(50):
        s.add(i)
    assert s.compression_ratio("zero") < 0.05


def test_compression_warning_emitted(tmp_path, monkeypatch):
    """Injective functor after warmup writes a receipt to the warnings file."""
    import ztare.common.image_set as ims_mod
    warn_file = tmp_path / "functor_compression_warnings.jsonl"
    monkeypatch.setattr(ims_mod, "_WARNINGS_PATH", warn_file)
    s = ims_mod.ImageMaintainingSet(
        functors={"id": lambda x: x},
        compression_warmup=5,
    )
    for i in range(25):
        s.add(i)
    assert warn_file.exists(), "warning receipt should have been written"
    lines = warn_file.read_text().strip().splitlines()
    assert lines, "at least one warning line expected"
    import json
    receipt = json.loads(lines[0])
    assert receipt["functor"] == "id"
    assert receipt["compression_ratio"] > 0.9
    assert receipt["representation_ratio"] > 0.9


def test_injective_compact_carrier_does_not_claim_ram_duplication(tmp_path):
    """Distinct classes can still compress each presentation substantially."""
    s = ImageMaintainingSet(
        functors={"digest": lambda value: value[:8]},
        compression_warmup=5,
        receipts_dir=tmp_path,
    )
    for i in range(25):
        s.add(f"{i:08d}" + ("x" * 10_000))
    assert s.compression_ratio("digest") == 1.0
    assert not (tmp_path / "functor_compression_warnings.jsonl").exists()


def test_check_invariant_returns_report():
    """check_invariant returns a dict with ok=True on a clean structure."""
    s = ImageMaintainingSet(functors={"h": _mod10})
    for i in range(30):
        s.add(i)
    report = s.check_invariant("h")
    assert report["ok"] is True
    assert report["maintained_size"] == report["recomputed_size"]
    assert report["name"] == "h"


def test_check_invariant_report_on_tamper():
    """Tampered image → check_invariant raises AssertionError (still raises, now also reports)."""
    s = ImageMaintainingSet(functors={"h": _mod10})
    for i in range(5):
        s.add(i)
    s._images["h"].add(999)
    with pytest.raises(AssertionError):
        s.check_invariant("h")


def test_saturation_kind_disambiguates_alpha_blind_from_exhausted():
    s = ImageMaintainingSet(functors={"parity": lambda x: x % 2})
    # growing raw, image saturates at {0,1} → functor-blindness, not exhaustion
    for i in range(20):
        s.add(i)
    assert s.saturation_kind("parity", window=10) == "alpha_blind"
    # now only duplicates arrive → raw flat → genuine exhaustion
    for i in range(20):
        s.add(i)
    assert s.saturation_kind("parity", window=10) == "exhausted"
    # fresh set, no attempts yet
    s2 = ImageMaintainingSet(functors={"id": lambda x: x})
    assert s2.saturation_kind("id") == "not_saturated"
    # injective functor under growing raw never saturates
    for i in range(20):
        s2.add(i)
    assert s2.saturation_kind("id", window=10) == "not_saturated"


# --- FIX 2: receipts_dir= plants the warning in the explicit directory ---

def test_compression_warning_respects_receipts_dir(tmp_path):
    """receipts_dir= routes the receipt to the given dir, not CWD workspace/."""
    import json as _json
    s = ImageMaintainingSet(
        functors={"id": lambda x: x},
        compression_warmup=5,
        receipts_dir=tmp_path,
    )
    for i in range(25):
        s.add(i)
    warn_file = tmp_path / "functor_compression_warnings.jsonl"
    assert warn_file.exists(), "receipt should land in receipts_dir, not CWD"
    rows = [_json.loads(l) for l in warn_file.read_text().splitlines() if l.strip()]
    assert rows, "at least one row expected"
    assert rows[0]["functor"] == "id"


def test_holes_is_dual_of_saturation():
    """holes() = reachable − image: the coverage-debt dual of saturation.
    Same object, opposite side — no separate coverage component."""
    s = ImageMaintainingSet(functors={"parity": lambda x: x % 3})
    for i in (0, 3, 6):        # image under mod-3 = {0}
        s.add(i)
    assert s.image("parity") == frozenset({0})
    # reachable classes {0,1,2}; witnessed {0} → holes {1,2}
    assert s.holes("parity", {0, 1, 2}) == frozenset({1, 2})
    # once all reachable classes witnessed, holes empty (dual of saturated)
    s.add(1); s.add(2)
    assert s.holes("parity", {0, 1, 2}) == frozenset()
