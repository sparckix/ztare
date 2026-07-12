"""Exact finite object-by-hypothesis contexts.

The primitive is substrate-neutral. A caller supplies a finite ordered object
universe and one truth bitset per hypothesis. LeanMill instantiates objects as
finite models and hypotheses as formulas; an interactive worldmodel can
instantiate objects as observed transitions and hypotheses as executable
programs.

All closure claims are conditional on exact=True and the caller's completeness
receipt. Sampled panels may use the same behavioral quotient, but cannot
request exact closure or generated-concept receipts.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import combinations
import json
from typing import Any, Iterable, Mapping, Protocol, Sequence


CONTEXT_SCHEMA = "ztare.finite_incidence_context.v1"
CONCEPT_SCHEMA = "ztare.finite_incidence_concept.v1"


def _digest(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class IncidenceProfile:
    """One hypothesis column over the context's ordered objects."""

    attribute_id: str
    truth_bits: int
    provenance_ref: str = ""

    def __post_init__(self) -> None:
        if not self.attribute_id:
            raise ValueError("attribute_id must be non-empty")
        if type(self.truth_bits) is not int or self.truth_bits < 0:
            raise ValueError("truth_bits must be a nonnegative integer")

    def to_json(self) -> dict[str, Any]:
        return {
            "attribute_id": self.attribute_id,
            "truth_bits_hex": hex(self.truth_bits),
            "provenance_ref": self.provenance_ref,
        }


@dataclass(frozen=True)
class GeneratedConcept:
    """A materialized extent generated within a declared presentation band."""

    context_hash: str
    node_id: str
    extent_bits: int
    closure_bits: int
    minimal_generators: tuple[tuple[str, ...], ...]
    presentation_count: int
    schema: str = CONCEPT_SCHEMA

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "context_hash": self.context_hash,
            "node_id": self.node_id,
            "extent_bits_hex": hex(self.extent_bits),
            "closure_bits_hex": hex(self.closure_bits),
            "minimal_generators": [list(row) for row in self.minimal_generators],
            "presentation_count": self.presentation_count,
        }


class FiniteIncidenceAdapter(Protocol):
    """Minimal adapter shared by exact algebra and observed-data substrates."""

    @property
    def object_ids(self) -> Sequence[str]: ...

    @property
    def attribute_ids(self) -> Sequence[str]: ...

    def satisfies(self, object_id: str, attribute_id: str) -> bool: ...


@dataclass(frozen=True)
class FiniteIncidenceContext:
    object_ids: tuple[str, ...]
    profiles: tuple[IncidenceProfile, ...]
    base_mask: int
    exact: bool
    completeness_ref: str
    schema: str = CONTEXT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CONTEXT_SCHEMA:
            raise ValueError(f"unsupported context schema: {self.schema!r}")
        if not self.object_ids:
            raise ValueError("finite incidence context needs at least one object")
        if len(set(self.object_ids)) != len(self.object_ids):
            raise ValueError("object_ids must be unique")
        if not self.profiles:
            raise ValueError("finite incidence context needs at least one attribute")
        ordered = tuple(sorted(self.profiles, key=lambda row: row.attribute_id))
        if ordered != self.profiles:
            object.__setattr__(self, "profiles", ordered)
        attribute_ids = [row.attribute_id for row in self.profiles]
        if len(set(attribute_ids)) != len(attribute_ids):
            raise ValueError("attribute_ids must be unique")
        if type(self.base_mask) is not int or self.base_mask < 0:
            raise ValueError("base_mask must be a nonnegative integer")
        invalid_bits = self.base_mask & ~self.all_mask
        if invalid_bits:
            raise ValueError("base_mask contains bits outside the object universe")
        for profile in self.profiles:
            if profile.truth_bits & ~self.all_mask:
                raise ValueError(
                    f"truth bits for {profile.attribute_id!r} exceed the object universe"
                )
        if self.exact and not self.completeness_ref:
            raise ValueError("exact contexts require a completeness_ref")

    @property
    def all_mask(self) -> int:
        return (1 << len(self.object_ids)) - 1

    @property
    def attribute_ids(self) -> tuple[str, ...]:
        return tuple(row.attribute_id for row in self.profiles)

    @property
    def context_hash(self) -> str:
        return _digest(self.to_json(include_hash=False))

    def to_json(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "object_ids": list(self.object_ids),
            "profiles": [row.to_json() for row in self.profiles],
            "base_mask_hex": hex(self.base_mask),
            "exact": self.exact,
            "completeness_ref": self.completeness_ref,
        }
        if include_hash:
            payload["context_hash"] = _digest(payload)
        return payload

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "FiniteIncidenceContext":
        profiles = tuple(
            IncidenceProfile(
                attribute_id=str(row["attribute_id"]),
                truth_bits=int(str(row["truth_bits_hex"]), 16),
                provenance_ref=str(row.get("provenance_ref") or ""),
            )
            for row in value.get("profiles") or ()
            if isinstance(row, Mapping)
        )
        context = cls(
            object_ids=tuple(str(row) for row in value.get("object_ids") or ()),
            profiles=profiles,
            base_mask=int(str(value.get("base_mask_hex") or "0"), 16),
            exact=value.get("exact") is True,
            completeness_ref=str(value.get("completeness_ref") or ""),
            schema=str(value.get("schema") or ""),
        )
        supplied_hash = value.get("context_hash")
        if supplied_hash is not None and supplied_hash != context.context_hash:
            raise ValueError("finite incidence context hash mismatch")
        return context

    def _profile_map(self) -> dict[str, IncidenceProfile]:
        return {row.attribute_id: row for row in self.profiles}

    def _require_exact(self) -> None:
        if not self.exact:
            raise ValueError("exact closure requires a complete finite context")

    def extent_bits(self, attribute_ids: Iterable[str]) -> int:
        profiles = self._profile_map()
        extent = self.base_mask
        for attribute_id in attribute_ids:
            try:
                extent &= profiles[str(attribute_id)].truth_bits
            except KeyError as exc:
                raise KeyError(f"unknown attribute_id: {attribute_id}") from exc
        return extent

    def extent_object_ids(self, attribute_ids: Iterable[str]) -> tuple[str, ...]:
        bits = self.extent_bits(attribute_ids)
        return tuple(
            object_id
            for index, object_id in enumerate(self.object_ids)
            if bits & (1 << index)
        )

    def closure_bits_for_extent(self, extent_bits: int) -> int:
        self._require_exact()
        if type(extent_bits) is not int or extent_bits < 0 or extent_bits & ~self.all_mask:
            raise ValueError("extent_bits is outside the object universe")
        closure = 0
        for index, profile in enumerate(self.profiles):
            if extent_bits & ~profile.truth_bits == 0:
                closure |= 1 << index
        return closure

    def closure_bits(self, attribute_ids: Iterable[str]) -> int:
        return self.closure_bits_for_extent(self.extent_bits(attribute_ids))

    def closure_ids(self, attribute_ids: Iterable[str]) -> tuple[str, ...]:
        bits = self.closure_bits(attribute_ids)
        return tuple(
            attribute_id
            for index, attribute_id in enumerate(self.attribute_ids)
            if bits & (1 << index)
        )

    def semantic_attribute_classes(self) -> tuple[tuple[str, ...], ...]:
        classes: dict[int, list[str]] = {}
        for profile in self.profiles:
            classes.setdefault(profile.truth_bits & self.base_mask, []).append(
                profile.attribute_id
            )
        return tuple(
            tuple(sorted(rows))
            for _bits, rows in sorted(classes.items(), key=lambda item: (item[0], item[1]))
        )

    def observational_object_classes(self) -> tuple[tuple[str, ...], ...]:
        """Group base objects indistinguishable by the current attributes.

        This is a language-relative partition, never an object-identity or
        isomorphism claim. Adding one attribute may refine it.
        """

        classes: dict[int, list[str]] = {}
        for object_index, object_id in enumerate(self.object_ids):
            if not self.base_mask & (1 << object_index):
                continue
            signature = 0
            for attribute_index, profile in enumerate(self.profiles):
                if profile.truth_bits & (1 << object_index):
                    signature |= 1 << attribute_index
            classes.setdefault(signature, []).append(object_id)
        return tuple(
            tuple(rows)
            for rows in sorted(classes.values(), key=lambda values: tuple(values))
        )

    def observational_partition_summary(self) -> dict[str, int]:
        classes = self.observational_object_classes()
        return {
            "class_count": len(classes),
            "non_singleton_class_count": sum(len(row) > 1 for row in classes),
            "largest_class_size": max((len(row) for row in classes), default=0),
        }

    def separation_object_id(
        self,
        left_attribute_ids: Iterable[str],
        right_attribute_ids: Iterable[str],
    ) -> str | None:
        difference = self.extent_bits(left_attribute_ids) ^ self.extent_bits(
            right_attribute_ids
        )
        if not difference:
            return None
        index = (difference & -difference).bit_length() - 1
        return self.object_ids[index]

    def independence_object_id(
        self,
        presentation: Sequence[str],
        target_attribute_id: str,
    ) -> str | None:
        if target_attribute_id not in presentation:
            raise ValueError("target attribute is not in the presentation")
        profiles = self._profile_map()
        background = tuple(
            attribute_id
            for attribute_id in presentation
            if attribute_id != target_attribute_id
        )
        witness_bits = self.extent_bits(background) & ~profiles[target_attribute_id].truth_bits
        if not witness_bits:
            return None
        index = (witness_bits & -witness_bits).bit_length() - 1
        return self.object_ids[index]

    def implication_counterexample_object_id(
        self,
        premise_attribute_ids: Iterable[str],
        target_attribute_id: str,
    ) -> str | None:
        """Return one object satisfying the premises and refuting the target."""

        profiles = self._profile_map()
        try:
            target = profiles[str(target_attribute_id)]
        except KeyError as exc:
            raise KeyError(f"unknown attribute_id: {target_attribute_id}") from exc
        witness_bits = self.extent_bits(premise_attribute_ids) & ~target.truth_bits
        if not witness_bits:
            return None
        index = (witness_bits & -witness_bits).bit_length() - 1
        return self.object_ids[index]

    def synergy_bits(self, presentation: Sequence[str]) -> int:
        self._require_exact()
        if not presentation:
            raise ValueError("synergy requires a nonempty presentation")
        joint = self.closure_bits(presentation)
        inherited = 0
        for target in presentation:
            inherited |= self.closure_bits(
                attribute_id
                for attribute_id in presentation
                if attribute_id != target
            )
        return joint & ~inherited

    def synergy_ids(self, presentation: Sequence[str]) -> tuple[str, ...]:
        bits = self.synergy_bits(presentation)
        return tuple(
            attribute_id
            for index, attribute_id in enumerate(self.attribute_ids)
            if bits & (1 << index)
        )

    def generated_concepts(
        self,
        *,
        max_presentation_size: int,
        semantic_quotient: bool = False,
    ) -> tuple[GeneratedConcept, ...]:
        """Materialize extents in a bounded presentation band.

        ``semantic_quotient`` is a read-model optimization: equivalent
        attribute profiles are represented by their first stable ID before
        combinations are enumerated.  It does not alter the context or the
        identity-bearing selection path; callers that need formula identity
        continue to use the full incidence columns.
        """

        self._require_exact()
        if type(max_presentation_size) is not int or max_presentation_size < 0:
            raise ValueError("max_presentation_size must be a nonnegative integer")
        if max_presentation_size > len(self.profiles):
            raise ValueError("max_presentation_size exceeds the attribute universe")

        attribute_ids = self.attribute_ids
        if semantic_quotient:
            attribute_ids = tuple(
                row[0] for row in self.semantic_attribute_classes()
            )

        rows: dict[int, dict[str, Any]] = {}
        for size in range(max_presentation_size + 1):
            for presentation in combinations(attribute_ids, size):
                extent = self.extent_bits(presentation)
                row = rows.setdefault(
                    extent,
                    {
                        "min_size": size,
                        "minimal_generators": [],
                        "presentation_count": 0,
                    },
                )
                row["presentation_count"] += 1
                if size < row["min_size"]:
                    row["min_size"] = size
                    row["minimal_generators"] = [presentation]
                elif size == row["min_size"]:
                    row["minimal_generators"].append(presentation)

        concepts: list[GeneratedConcept] = []
        for extent, row in rows.items():
            node_id = _digest(
                {"context_hash": self.context_hash, "extent_bits_hex": hex(extent)}
            )
            concepts.append(
                GeneratedConcept(
                    context_hash=self.context_hash,
                    node_id=node_id,
                    extent_bits=extent,
                    closure_bits=self.closure_bits_for_extent(extent),
                    minimal_generators=tuple(row["minimal_generators"]),
                    presentation_count=int(row["presentation_count"]),
                )
            )
        concepts.sort(key=lambda row: (row.extent_bits.bit_count(), row.extent_bits))
        return tuple(concepts)


def build_incidence_context(
    *,
    object_ids: Sequence[str],
    attribute_truth_bits: Mapping[str, int],
    base_mask: int | None = None,
    exact: bool,
    completeness_ref: str = "",
    provenance_refs: Mapping[str, str] | None = None,
) -> FiniteIncidenceContext:
    object_ids = tuple(str(item) for item in object_ids)
    all_mask = (1 << len(object_ids)) - 1
    provenance_refs = provenance_refs or {}
    profiles = tuple(
        IncidenceProfile(
            attribute_id=str(attribute_id),
            truth_bits=int(truth_bits),
            provenance_ref=str(provenance_refs.get(str(attribute_id), "")),
        )
        for attribute_id, truth_bits in sorted(attribute_truth_bits.items())
    )
    return FiniteIncidenceContext(
        object_ids=object_ids,
        profiles=profiles,
        base_mask=all_mask if base_mask is None else base_mask,
        exact=exact,
        completeness_ref=completeness_ref,
    )


def build_context_from_adapter(
    adapter: FiniteIncidenceAdapter,
    *,
    exact: bool,
    completeness_ref: str = "",
    base_object_ids: Iterable[str] | None = None,
) -> FiniteIncidenceContext:
    object_ids = tuple(str(item) for item in adapter.object_ids)
    positions = {object_id: index for index, object_id in enumerate(object_ids)}
    if len(positions) != len(object_ids):
        raise ValueError("adapter object_ids must be unique")
    truth: dict[str, int] = {}
    for attribute_id in adapter.attribute_ids:
        bits = 0
        for index, object_id in enumerate(object_ids):
            if adapter.satisfies(object_id, str(attribute_id)):
                bits |= 1 << index
        truth[str(attribute_id)] = bits
    if base_object_ids is None:
        base_mask = (1 << len(object_ids)) - 1
    else:
        base_mask = 0
        for object_id in base_object_ids:
            try:
                base_mask |= 1 << positions[str(object_id)]
            except KeyError as exc:
                raise KeyError(f"unknown base object_id: {object_id}") from exc
    return build_incidence_context(
        object_ids=object_ids,
        attribute_truth_bits=truth,
        base_mask=base_mask,
        exact=exact,
        completeness_ref=completeness_ref,
    )


__all__ = [
    "CONCEPT_SCHEMA",
    "CONTEXT_SCHEMA",
    "FiniteIncidenceAdapter",
    "FiniteIncidenceContext",
    "GeneratedConcept",
    "IncidenceProfile",
    "build_context_from_adapter",
    "build_incidence_context",
]
