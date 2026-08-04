"""Content-addressed object occurrences for one settled grid observation.

This is a grid adapter for the controller/worldmodel judgment bridge.  It
derives field-like palette values from component area, then catalogs
four-connected components over the remaining values.  Object type identity is
translation-invariant; occurrence identity remains bound to the exact
observation and bounding box.

Task roles and goals do not enter this module.  An experiment adapter may
resolve evidence-backed selectors against the catalog, while the common
judgment kernel sees only opaque occurrence references.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.object_roles import _component_image, _components


SCHEMA = "ztare-grid-object-catalog-v1"
PRESENTATION_SCHEMA = "ztare-grid-object-catalog-presentation-v1"
_COMPILER_SPEC = {
    "schema": SCHEMA,
    "adjacency": "four_connected",
    "field_threshold": "2*max(height,width)",
    "field_test": "largest_same_value_component_area",
    "object_mask": "complement_of_field_values",
    "type_identity": "normalized_colored_shape",
    "occurrence_identity": [
        "observation_sha256",
        "compiler_sha256",
        "type_sha256",
        "bbox",
    ],
}
CATALOG_COMPILER_SHA256 = stable_sha256(_COMPILER_SPEC)


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _rectangular_grid(
    grid: Sequence[Sequence[int]],
) -> tuple[tuple[int, ...], ...]:
    rows = tuple(tuple(int(value) for value in row) for row in grid)
    if not rows or not rows[0]:
        raise ValueError("grid must be nonempty")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("grid must be rectangular")
    return rows


def decode_grid_rle_rows(rows: Sequence[str]) -> tuple[tuple[int, ...], ...]:
    """Decode the lossless ``value x run`` observation representation."""

    grid: list[tuple[int, ...]] = []
    for row_index, row in enumerate(rows):
        values: list[int] = []
        for token in str(row).split(","):
            pieces = token.split("x")
            if len(pieces) != 2:
                raise ValueError(
                    f"invalid RLE token at row {row_index}: {token!r}"
                )
            value, count = (int(piece) for piece in pieces)
            if count <= 0:
                raise ValueError("RLE run length must be positive")
            values.extend([value] * count)
        grid.append(tuple(values))
    return _rectangular_grid(grid)


def _field_values(
    grid: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    threshold = 2 * max(len(grid), len(grid[0]))
    values = sorted({value for row in grid for value in row})
    return tuple(
        value
        for value in values
        if max(
            (len(component) for component in _components(grid, {value})),
            default=0,
        )
        >= threshold
    )


@dataclass(frozen=True)
class GridObjectOccurrence:
    """One exact-observation occurrence of a normalized colored component."""

    observation_sha256: str
    compiler_sha256: str
    type_sha256: str
    bbox: tuple[int, int, int, int]
    cell_count: int
    palette: tuple[int, ...]
    normalized_colored_shape: tuple[tuple[int, int, int], ...]

    def __post_init__(self) -> None:
        for name in (
            "observation_sha256",
            "compiler_sha256",
            "type_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if len(self.bbox) != 4:
            raise ValueError("bbox must have four coordinates")
        y0, x0, y1, x1 = (int(value) for value in self.bbox)
        if y1 < y0 or x1 < x0:
            raise ValueError("bbox is inverted")
        object.__setattr__(self, "bbox", (y0, x0, y1, x1))
        if int(self.cell_count) <= 0:
            raise ValueError("cell_count must be positive")
        object.__setattr__(self, "cell_count", int(self.cell_count))
        object.__setattr__(
            self,
            "palette",
            tuple(sorted({int(value) for value in self.palette})),
        )
        shape = tuple(sorted(
            tuple(int(value) for value in cell)
            for cell in self.normalized_colored_shape
        ))
        if len(shape) != self.cell_count:
            raise ValueError("shape size does not equal cell_count")
        if stable_sha256({"normalized_colored_shape": shape}) != (
            self.type_sha256
        ):
            raise ValueError("object type identity drifted")
        object.__setattr__(self, "normalized_colored_shape", shape)

    @property
    def occurrence_sha256(self) -> str:
        return stable_sha256({
            "observation_sha256": self.observation_sha256,
            "compiler_sha256": self.compiler_sha256,
            "type_sha256": self.type_sha256,
            "bbox": list(self.bbox),
        })

    @property
    def object_ref(self) -> str:
        return f"object:{self.occurrence_sha256}"

    def to_receipt(self, *, include_shape: bool = True) -> dict[str, Any]:
        row: dict[str, Any] = {
            "object_ref": self.object_ref,
            "type_sha256": self.type_sha256,
            "bbox": list(self.bbox),
            "cell_count": self.cell_count,
            "palette": list(self.palette),
        }
        if include_shape:
            row["normalized_colored_shape"] = [
                list(cell) for cell in self.normalized_colored_shape
            ]
        return row


@dataclass(frozen=True)
class GridObjectCatalog:
    observation_sha256: str
    grid_sha256: str
    compiler_sha256: str
    grid_shape: tuple[int, int]
    field_values: tuple[int, ...]
    objects: tuple[GridObjectOccurrence, ...]

    def __post_init__(self) -> None:
        for name in (
            "observation_sha256",
            "grid_sha256",
            "compiler_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if len(self.grid_shape) != 2 or min(self.grid_shape) <= 0:
            raise ValueError("grid_shape must be positive")
        refs = [row.object_ref for row in self.objects]
        if len(refs) != len(set(refs)):
            raise ValueError("catalog contains duplicate object refs")
        if any(
            row.observation_sha256 != self.observation_sha256
            or row.compiler_sha256 != self.compiler_sha256
            for row in self.objects
        ):
            raise ValueError("catalog object authority drifted")

    @property
    def sha256(self) -> str:
        return stable_sha256({
            "schema": SCHEMA,
            "observation_sha256": self.observation_sha256,
            "grid_sha256": self.grid_sha256,
            "compiler_sha256": self.compiler_sha256,
            "grid_shape": list(self.grid_shape),
            "field_values": list(self.field_values),
            "objects": [
                row.to_receipt(include_shape=True) for row in self.objects
            ],
        })

    @property
    def object_refs(self) -> tuple[str, ...]:
        return tuple(row.object_ref for row in self.objects)

    def prompt_receipt(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "observation_sha256": self.observation_sha256,
            "catalog_sha256": self.sha256,
            "grid_shape": list(self.grid_shape),
            "field_values": list(self.field_values),
            "objects": [
                row.to_receipt(include_shape=True) for row in self.objects
            ],
        }

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            **self.prompt_receipt(),
            "grid_sha256": self.grid_sha256,
            "compiler_sha256": self.compiler_sha256,
        }
        return {
            **payload,
            "sha256": stable_sha256(payload),
        }

    def resolve_selector(
        self,
        selector: Mapping[str, Any],
    ) -> GridObjectOccurrence:
        """Resolve an adapter selector uniquely or fail before controller use."""

        allowed = {"bbox", "palette", "cell_count", "type_sha256"}
        unknown = set(selector) - allowed
        if unknown:
            raise ValueError(
                f"object selector has unknown keys: {sorted(unknown)}"
            )
        matches = list(self.objects)
        if "bbox" in selector:
            bbox = tuple(int(value) for value in selector["bbox"])
            matches = [row for row in matches if row.bbox == bbox]
        if "palette" in selector:
            palette = tuple(sorted(
                {int(value) for value in selector["palette"]}
            ))
            matches = [row for row in matches if row.palette == palette]
        if "cell_count" in selector:
            count = int(selector["cell_count"])
            matches = [row for row in matches if row.cell_count == count]
        if "type_sha256" in selector:
            type_sha = str(selector["type_sha256"])
            matches = [
                row for row in matches if row.type_sha256 == type_sha
            ]
        if len(matches) != 1:
            raise ValueError(
                "object selector must resolve exactly once; "
                f"resolved={len(matches)} selector={dict(selector)!r}"
            )
        return matches[0]


@dataclass(frozen=True)
class GridObjectCatalogPresentation:
    """Role-free local handles bound to one exact object catalog."""

    catalog: GridObjectCatalog
    handle_to_object_ref: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        pairs = tuple(
            (str(handle), str(object_ref))
            for handle, object_ref in self.handle_to_object_ref
        )
        handles = [handle for handle, _object_ref in pairs]
        refs = [object_ref for _handle, object_ref in pairs]
        if len(handles) != len(set(handles)):
            raise ValueError("presentation contains duplicate handles")
        if len(refs) != len(set(refs)):
            raise ValueError("presentation repeats object refs")
        if set(refs) != set(self.catalog.object_refs):
            raise ValueError(
                "presentation must cover the catalog exactly once"
            )
        if any(
            handle != f"o{index:02d}"
            for index, handle in enumerate(handles)
        ):
            raise ValueError("presentation handles changed ordinal form")
        object.__setattr__(self, "handle_to_object_ref", pairs)

    @property
    def sha256(self) -> str:
        return stable_sha256({
            "schema": PRESENTATION_SCHEMA,
            "observation_sha256": self.catalog.observation_sha256,
            "catalog_sha256": self.catalog.sha256,
            "handle_to_object_ref": [
                [handle, object_ref]
                for handle, object_ref in self.handle_to_object_ref
            ],
        })

    def resolve_handle(self, handle: str) -> str:
        matches = [
            object_ref
            for candidate, object_ref in self.handle_to_object_ref
            if candidate == str(handle)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"unknown catalog-scoped object handle: {handle!r}"
            )
        return matches[0]

    def handle_for_ref(self, object_ref: str) -> str:
        matches = [
            handle
            for handle, candidate in self.handle_to_object_ref
            if candidate == str(object_ref)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"object ref is absent from presentation: {object_ref!r}"
            )
        return matches[0]

    def prompt_receipt(self) -> dict[str, Any]:
        by_ref = {
            row.object_ref: row for row in self.catalog.objects
        }
        return {
            "schema": PRESENTATION_SCHEMA,
            "observation_sha256": self.catalog.observation_sha256,
            "catalog_sha256": self.catalog.sha256,
            "presentation_sha256": self.sha256,
            "grid_shape": list(self.catalog.grid_shape),
            "field_values": list(self.catalog.field_values),
            "objects": [
                {
                    "handle": handle,
                    **{
                        key: value
                        for key, value in by_ref[
                            object_ref
                        ].to_receipt(include_shape=True).items()
                        if key != "object_ref"
                    },
                }
                for handle, object_ref in self.handle_to_object_ref
            ],
        }

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            **self.prompt_receipt(),
            "handle_bindings": [
                {
                    "handle": handle,
                    "object_ref": object_ref,
                }
                for handle, object_ref in self.handle_to_object_ref
            ],
        }
        return {**payload, "sha256": stable_sha256(payload)}


def compile_grid_object_catalog(
    grid: Sequence[Sequence[int]],
    *,
    observation_sha256: str,
) -> GridObjectCatalog:
    """Compile one observation without task labels or action semantics."""

    frozen = _rectangular_grid(grid)
    observation = _nonempty(observation_sha256, "observation_sha256")
    field_values = _field_values(frozen)
    object_values = {
        value for row in frozen for value in row
    } - set(field_values)
    occurrences: list[GridObjectOccurrence] = []
    for component in _components(frozen, object_values):
        origin, shape = _component_image(frozen, component)
        ys = [cell[0] for cell in component]
        xs = [cell[1] for cell in component]
        normalized = tuple(
            tuple(int(value) for value in cell) for cell in shape
        )
        type_sha = stable_sha256({
            "normalized_colored_shape": normalized,
        })
        occurrences.append(GridObjectOccurrence(
            observation_sha256=observation,
            compiler_sha256=CATALOG_COMPILER_SHA256,
            type_sha256=type_sha,
            bbox=(
                int(origin[0]),
                int(origin[1]),
                int(max(ys)),
                int(max(xs)),
            ),
            cell_count=len(component),
            palette=tuple(
                sorted({frozen[y][x] for y, x in component})
            ),
            normalized_colored_shape=normalized,
        ))
    occurrences.sort(
        key=lambda row: (
            row.bbox,
            row.cell_count,
            row.type_sha256,
        )
    )
    grid_sha = stable_sha256({
        "grid": [list(row) for row in frozen],
    })
    return GridObjectCatalog(
        observation_sha256=observation,
        grid_sha256=grid_sha,
        compiler_sha256=CATALOG_COMPILER_SHA256,
        grid_shape=(len(frozen), len(frozen[0])),
        field_values=field_values,
        objects=tuple(occurrences),
    )


def compile_catalog_presentation(
    catalog: GridObjectCatalog,
) -> GridObjectCatalogPresentation:
    if len(catalog.objects) > 100:
        raise ValueError(
            "two-digit catalog presentation supports at most 100 objects"
        )
    return GridObjectCatalogPresentation(
        catalog=catalog,
        handle_to_object_ref=tuple(
            (f"o{index:02d}", row.object_ref)
            for index, row in enumerate(catalog.objects)
        ),
    )


def compile_catalog_from_observation(
    observation: Mapping[str, Any],
) -> GridObjectCatalog:
    """Compile directly from a settled lossless observation receipt."""

    schema = str(observation.get("schema") or "")
    if schema != "ztare-arc3-settled-observation-v1":
        raise ValueError("unsupported settled observation schema")
    observation_sha = _nonempty(
        str(observation.get("sha256") or ""),
        "observation.sha256",
    )
    rows = observation.get("grid_rle_rows")
    if not isinstance(rows, list):
        raise ValueError("observation omitted grid_rle_rows")
    grid = decode_grid_rle_rows(tuple(str(row) for row in rows))
    declared_shape = tuple(
        int(value) for value in observation.get("grid_shape") or ()
    )
    if declared_shape != (len(grid), len(grid[0])):
        raise ValueError("observation grid shape drifted")
    return compile_grid_object_catalog(
        grid,
        observation_sha256=observation_sha,
    )


def selector_refs(
    catalog: GridObjectCatalog,
    selectors: Iterable[Mapping[str, Any]],
) -> tuple[str, ...]:
    return tuple(
        catalog.resolve_selector(selector).object_ref
        for selector in selectors
    )


__all__ = [
    "CATALOG_COMPILER_SHA256",
    "GridObjectCatalog",
    "GridObjectCatalogPresentation",
    "GridObjectOccurrence",
    "PRESENTATION_SCHEMA",
    "compile_catalog_presentation",
    "compile_catalog_from_observation",
    "compile_grid_object_catalog",
    "decode_grid_rle_rows",
    "selector_refs",
]
