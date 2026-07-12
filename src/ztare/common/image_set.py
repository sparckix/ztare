"""ImageMaintainingSet — a set that co-maintains named functor images incrementally.

Soundness condition (functoriality law):
    Images are maintained under the assumption that the registered
    functor α is *pointwise* — i.e., α(S ∪ {x}) = α(S) ∪ {α(x)}.
    If this does not hold for your α (e.g. α depends on the full set,
    not just the new element), results will silently diverge from a
    full recomputation.  Use check_invariant(name) to audit.

Purity contract:
    Registered functors MUST be pure (deterministic, no side effects, no
    mutable closure state).  Pointwise shape is necessary but not sufficient:
    a stateful closure that returns the same type can still corrupt images
    silently by returning different values for the same input on different
    calls.  The trace-auditor may call check_invariant(name) to detect drift.

Design: dict of sets, O(1) adds, ~160 lines, no metaclasses.
"""
from __future__ import annotations

import json
import os
from collections import deque
from pathlib import Path
from typing import Callable


_COMPRESSION_WARMUP_DEFAULT = 20
_COMPRESSION_THRESHOLD = 0.9
_WARNINGS_PATH = Path("workspace/functor_compression_warnings.jsonl")


def _emit_compression_warning(name: str, ratio: float, raw_size: int, *, receipts_dir: "Path | None" = None) -> None:
    """Append a one-line friction receipt to functor_compression_warnings.jsonl.

    receipts_dir: explicit directory for the receipt file (overrides CWD-relative
    workspace/ default). Fallback to _WARNINGS_PATH preserves compat for callers
    that don't pass a project workspace.
    """
    out = (Path(receipts_dir) / _WARNINGS_PATH.name) if receipts_dir is not None else _WARNINGS_PATH
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a") as fh:
            fh.write(json.dumps({
                "functor": name,
                "compression_ratio": round(ratio, 4),
                "raw_size": raw_size,
                "note": (
                    f"functor '{name}' compression_ratio={ratio:.2%} > {_COMPRESSION_THRESHOLD:.0%} "
                    f"— injective α duplicates RAM; consider a coarser quotient"
                ),
            }) + "\n")
    except OSError:
        pass  # never crash the caller over a receipt


class ImageMaintainingSet:
    """A set that maintains named functor images incrementally.

    Soundness condition (functoriality law):
        Images are maintained under the assumption that the registered
        functor α is *pointwise* — i.e., α(S ∪ {x}) = α(S) ∪ {α(x)}.
        If this does not hold for your α (e.g. α depends on the full set,
        not just the new element), results will silently diverge from a
        full recomputation.  Use check_invariant(name) to audit.

    Purity contract:
        Functors MUST be pure — no closing over mutable state.
        Pointwise shape is insufficient: a stateful closure can return
        different values for the same input across calls, corrupting the
        image silently.  The trace-auditor may call check_invariant(name)
        at any time to verify invariant integrity.

    Canonicalization:
        By default the carrier returned by each functor must be hashable.
        On the first add per functor, hashability is verified; an unhashable
        return raises TypeError with the functor name and returned type.
        Supply canonicalize={name: fn} to coerce carriers before hashing.

    Compression warnings:
        When |image|/|raw| > 0.9 after a warmup of N adds, a one-line
        friction receipt is appended to workspace/functor_compression_warnings.jsonl.
        An injective α is not a quotient and wastes RAM.

    Usage::

        s = ImageMaintainingSet(functors={'abstract': my_fn})
        s.add(x)
        x in s                         # raw membership
        s.contains_image('abstract', carrier)
        s.image('abstract')            # frozenset
        s.saturated('abstract', window=5)
        s.compression_ratio('abstract')
        s.check_invariant('abstract')  # audit only, not for hot paths
    """

    def __init__(
        self,
        *,
        functors: "dict[str, Callable] | None" = None,
        canonicalize: "dict[str, Callable] | None" = None,
        compression_warmup: int = _COMPRESSION_WARMUP_DEFAULT,
        receipts_dir: "Path | str | None" = None,
    ) -> None:
        self._raw: set = set()
        self._functors: "dict[str, Callable]" = dict(functors or {})
        self._canonicalize: "dict[str, Callable]" = dict(canonicalize or {})
        self._images: "dict[str, set]" = {name: set() for name in self._functors}
        self._add_counts: "dict[str, int]" = {name: 0 for name in self._functors}
        self._size_history: "dict[str, deque]" = {
            name: deque() for name in self._functors
        }
        # per-attempt record (True=new raw element, False=duplicate) —
        # duplicates never touch _size_history, so without this the set
        # cannot tell "raw stopped growing" from "raw grows, image flat"
        self._attempts: deque = deque(maxlen=4096)
        # tracks whether we've run the first-add hash check per functor
        self._hash_checked: "set[str]" = set()
        self._compression_warmup = compression_warmup
        # tracks whether we've already emitted a compression warning per functor
        self._compression_warned: "set[str]" = set()
        # explicit sink for receipts; None → CWD-relative workspace/ (compat)
        self._receipts_dir: "Path | None" = Path(receipts_dir) if receipts_dir is not None else None

    def register(
        self,
        name: str,
        fn: "Callable",
        canonicalize: "Callable | None" = None,
    ) -> None:
        """Register a new functor after construction.

        Purity contract: fn must be pure (see class docstring).
        Backfills the image from the current raw set.
        """
        self._functors[name] = fn
        if canonicalize is not None:
            self._canonicalize[name] = canonicalize
        self._images[name] = {self._apply(name, fn, x) for x in self._raw}
        self._add_counts[name] = len(self._raw)
        self._size_history[name] = deque()
        self._hash_checked.add(name)  # backfill already validated hashability

    def _apply(self, name: str, fn: "Callable", x) -> object:
        """Apply fn to x, optionally canonicalizing, with first-add hash check."""
        carrier = fn(x)
        canon = self._canonicalize.get(name)
        if canon is not None:
            carrier = canon(carrier)
        if name not in self._hash_checked:
            try:
                hash(carrier)
            except TypeError:
                raise TypeError(
                    f"functor '{name}' returned unhashable {type(carrier).__name__} "
                    f"— functors must return frozen types (or supply a canonicalize= hook)"
                )
            self._hash_checked.add(name)
        return carrier

    def add(self, x) -> None:
        """Add x to raw set and update all registered images."""
        if x in self._raw:
            self._attempts.append(False)
            return
        self._attempts.append(True)
        self._raw.add(x)
        raw_size = len(self._raw)
        for name, fn in self._functors.items():
            carrier = self._apply(name, fn, x)
            self._images[name].add(carrier)
            self._add_counts[name] += 1
            self._size_history[name].append(len(self._images[name]))
            # compression warning: after warmup, check ratio once per crossing
            if (
                name not in self._compression_warned
                and raw_size >= self._compression_warmup
            ):
                ratio = len(self._images[name]) / raw_size
                if ratio > _COMPRESSION_THRESHOLD:
                    self._compression_warned.add(name)
                    _emit_compression_warning(name, ratio, raw_size, receipts_dir=self._receipts_dir)

    def __contains__(self, x) -> bool:
        return x in self._raw

    def contains(self, x) -> bool:
        return x in self._raw

    def contains_image(self, name: str, carrier) -> bool:
        """Check membership in the named image set."""
        return carrier in self._images[name]

    def image(self, name: str) -> frozenset:
        """Return the current image as a frozenset."""
        return frozenset(self._images[name])

    def __len__(self) -> int:
        return len(self._raw)

    def compression_ratio(self, name: str) -> float:
        """Return |image(name)| / |raw|. 1.0 = injective (no compression)."""
        raw_size = len(self._raw)
        if raw_size == 0:
            return 0.0
        return len(self._images[name]) / raw_size

    def check_invariant(self, name: str) -> dict:
        """Recompute image from scratch and return a report dict.

        Never call on hot paths — O(|raw|).
        The trace-auditor may call this at any time; it returns a report
        rather than raising so the caller controls failure handling.

        Returns::

            {
                'name': str,
                'maintained_size': int,
                'recomputed_size': int,
                'ok': bool,
                'missing': set,   # in recomputed but not maintained
                'extra': set,     # in maintained but not recomputed
            }
        """
        fn = self._functors[name]
        recomputed = {self._apply(name, fn, x) for x in self._raw}
        actual = self._images[name]
        missing = recomputed - actual
        extra = actual - recomputed
        ok = not missing and not extra
        if not ok:
            raise AssertionError(
                f"ImageMaintainingSet invariant violated for '{name}': "
                f"incremental image diverged from full recomputation. "
                f"Is your functor pure and pointwise? "
                f"Missing: {missing}, Extra: {extra}"
            )
        return {
            "name": name,
            "maintained_size": len(actual),
            "recomputed_size": len(recomputed),
            "ok": ok,
            "missing": missing,
            "extra": extra,
        }

    def saturated(self, name: str, window: int = 5) -> bool:
        """True when the image stopped growing over the last `window` adds.

        A window of identical sizes means every add in that window hit an
        already-seen carrier — i.e., the image has stabilised.
        """
        hist = self._size_history[name]
        if len(hist) < window:
            return False
        tail = list(hist)[-window:]
        return len(set(tail)) == 1

    def saturation_kind(self, name: str, window: int = 50) -> str:
        """Disambiguate saturation: a flat image under a still-growing raw set
        is a statement about the FUNCTOR (it is blind to the new variation —
        premature saturation via lossy abstraction; refine the quotient),
        while a flat raw set is genuine exhaustion of the explored space.
        Returns 'not_saturated' | 'exhausted' | 'alpha_blind'.

        Reads the per-attempt record: duplicates never enter _size_history,
        so image flatness alone can never witness exhaustion.
        """
        recent = list(self._attempts)[-window:]
        if not recent:
            return "not_saturated"
        new_adds = sum(recent)
        if new_adds == 0:
            return "exhausted"  # every recent proposal already seen at raw level
        if self.saturated(name, max(2, min(new_adds, window))):
            return "alpha_blind"  # raw grew, image did not: refine the quotient
        return "not_saturated"

    def holes(self, name: str, reachable_carriers) -> frozenset:
        """The DUAL of saturation: α-carriers reachable under this functor that
        the image has NOT yet witnessed. `reachable_carriers` is an iterable of
        already-α carriers the caller believes attainable (e.g. from a bounded
        forward-reachability sweep, each mapped through α). holes = reachable − image.

        Same object saturation reads from the other side: saturated()/alpha_blind
        = "image stopped growing"; a non-empty holes() set = "reachable carriers
        remain unwitnessed" = coverage debt. Price a hole via
        information_yield_pricing (valuable iff surviving hypotheses disagree
        across it); reach it via γ (pursue_goal to the hole's class). No separate
        coverage component needed — this is the α-image's boundary, nothing new.
        """
        img = self._images[name]
        return frozenset(c for c in reachable_carriers if c not in img)

    def growth_rate(self, name: str) -> float:
        """Cumulative image-density ratio: |image| / adds since registration.

        Returns 0.0 if no adds yet. Approaches 0 as image saturates.

        # ponytail: cumulative density, not a delta rate; monotone-decreasing
        # toward saturation. For a windowed delta rate use hist[-1]-hist[-K]/K.
        """
        adds = self._add_counts[name]
        if adds == 0:
            return 0.0
        return len(self._images[name]) / adds
