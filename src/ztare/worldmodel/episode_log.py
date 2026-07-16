"""Canonical append-only episode record for interactive substrates (GP-250).

The log is the system of record: synthesis, gates, rollouts, and audits read
transitions from here, never from a live environment. Live environment steps
are spent only to acquire new information; everything downstream replays free.
Recorded logs double as deterministic CI fixtures.

Format: JSONL, one transition per row.  Legacy rows contain only
``t/s/a/s_next``; adapter-authored rows may additionally carry a typed
``identity`` object.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from ztare.common.equivariance import stable_sha256
from ztare.common.observation_chart import (
    ChartTransportMorphism,
    ObservationChart,
    TransportWitness,
    certify_pointwise_transport,
)
from ztare.worldmodel.grid_dsl import Grid, grid_from_lists, grid_to_lists
from ztare.worldmodel.transition_identity import TransitionIdentity


@dataclass(frozen=True)
class Transition:
    t: int
    s: Grid
    a: int
    s_next: Grid
    identity: TransitionIdentity | None = None

    def context_hash(self) -> str:
        """Digest of the intervention context, excluding its consequence.

        A context can have more than one witnessed consequence.  Callers that
        deduplicate evidence must therefore pair this key with
        :meth:`observation_hash`; collapsing on this key alone would erase a
        determinism counterexample.
        """
        payload = json.dumps(
            [self.t, grid_to_lists(self.s), self.a],
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    def observation_hash(self) -> str:
        """Identity-free digest used by collector sidecar bindings."""
        payload = json.dumps(
            [self.t, grid_to_lists(self.s), self.a, grid_to_lists(self.s_next)],
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()


class EpisodeIdentityBindingError(ValueError):
    """A transition-identity sidecar does not bind the referenced episode."""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity_sidecar_payload(
    episode_path: Path,
    *,
    episode_sha256: str | None = None,
    allow_stale_episode_binding: bool = False,
) -> dict | None:
    """Parse and validate the identity-sidecar envelope once."""
    sidecar = episode_path.with_name(f"{episode_path.stem}.identity.json")
    if not sidecar.is_file():
        return None
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EpisodeIdentityBindingError(f"invalid identity sidecar: {sidecar}") from exc
    if not isinstance(payload, dict):
        raise EpisodeIdentityBindingError("identity sidecar must be an object")
    if payload.get("schema") != "ztare-episode-identity-sidecar-v1":
        raise EpisodeIdentityBindingError("unsupported episode identity sidecar schema")
    expected_sha256 = episode_sha256 or _file_sha256(episode_path)
    if (
        str(payload.get("episode_sha256") or "") != expected_sha256
        and not allow_stale_episode_binding
    ):
        raise EpisodeIdentityBindingError(
            "identity sidecar episode_sha256 does not match episode bytes"
        )
    bindings = payload.get("bindings")
    if not isinstance(bindings, list):
        raise EpisodeIdentityBindingError("identity sidecar bindings must be a list")
    seen: set[int] = set()
    for binding in bindings:
        if not isinstance(binding, dict):
            raise EpisodeIdentityBindingError("identity binding must be an object")
        try:
            index = int(binding["row_index"])
        except (KeyError, TypeError, ValueError) as exc:
            raise EpisodeIdentityBindingError(
                "identity binding needs integer row_index"
            ) from exc
        if index < 0 or index in seen:
            raise EpisodeIdentityBindingError(
                f"invalid or duplicate identity row {index}"
            )
        seen.add(index)
    return payload


def declared_episode_observation_chart(
    sidecar_payload: dict,
) -> ObservationChart | None:
    """Resolve the chart of stored episode rows without list-order authority."""
    raw_charts = sidecar_payload.get("observation_charts") or []
    if not isinstance(raw_charts, list):
        raise EpisodeIdentityBindingError("observation_charts must be a list")
    try:
        charts = [ObservationChart.from_dict(row) for row in raw_charts]
    except (TypeError, ValueError) as exc:
        raise EpisodeIdentityBindingError("invalid observation chart") from exc
    if not charts:
        return None
    charts_by_sha = {chart.sha256: chart for chart in charts}
    if len(charts_by_sha) != len(charts):
        raise EpisodeIdentityBindingError("observation chart identities must be unique")
    declared_sha = str(sidecar_payload.get("episode_chart_sha256") or "").strip()
    if not declared_sha:
        if len(charts) == 1:
            return charts[0]
        raise EpisodeIdentityBindingError(
            "multiple observation charts require episode_chart_sha256"
        )
    chart = charts_by_sha.get(declared_sha)
    if chart is None:
        raise EpisodeIdentityBindingError(
            "episode_chart_sha256 does not name a declared observation chart"
        )
    return chart


def _transport_packet(row: Transition, identity_payload: dict) -> dict:
    """Chart-neutral packet used by the pointwise transport certificate."""
    return {
        "state": grid_to_lists(row.s),
        "intervention": row.a,
        "time": row.t,
        "successor": grid_to_lists(row.s_next),
        "transition_identity": identity_payload,
    }


def _apply_identity_sidecar(
    path: Path,
    rows: list[Transition],
    *,
    allow_stale_episode_binding: bool = False,
    episode_sha256: str | None = None,
) -> list[Transition]:
    payload = _identity_sidecar_payload(
        path,
        episode_sha256=episode_sha256,
        allow_stale_episode_binding=allow_stale_episode_binding,
    )
    if payload is None:
        return rows
    bindings = payload.get("bindings")
    by_index: dict[int, dict] = {}
    for binding in bindings:
        index = int(binding["row_index"])
        if index >= len(rows):
            raise EpisodeIdentityBindingError(f"invalid or duplicate identity row {index}")
        if binding.get("observation_sha256") != rows[index].observation_hash():
            raise EpisodeIdentityBindingError(
                f"identity binding row {index} does not match transition bytes"
            )
        attestation_kind = str(binding.get("attestation_kind") or "")
        if attestation_kind not in {"exact_environment_replay", "duplicate_transport"}:
            raise EpisodeIdentityBindingError(
                f"identity binding row {index} has unsupported attestation_kind"
            )
        by_index[index] = binding

    # Duplicate transport needs a multi-row commuting window. A one-frame
    # collision cannot establish lifecycle identity when hidden state remains
    # possible. The map is declarative and row-local; every source row must
    # carry a direct environment attestation.  This is chart transport, not a
    # within-epoch symmetry claim and not a candidate-law exception.
    duplicate_indices = {
        index
        for index, binding in by_index.items()
        if binding["attestation_kind"] == "duplicate_transport"
    }
    covered_duplicates: set[int] = set()
    windows = payload.get("transport_windows") or []
    if not isinstance(windows, list):
        raise EpisodeIdentityBindingError("transport_windows must be a list")
    raw_charts = payload.get("observation_charts") or []
    if not isinstance(raw_charts, list):
        raise EpisodeIdentityBindingError("observation_charts must be a list")
    try:
        charts = [ObservationChart.from_dict(row) for row in raw_charts]
    except (TypeError, ValueError) as exc:
        raise EpisodeIdentityBindingError("invalid observation chart") from exc
    charts_by_sha = {chart.sha256: chart for chart in charts}
    if len(charts_by_sha) != len(charts):
        raise EpisodeIdentityBindingError("observation chart identities must be unique")
    declared_episode_observation_chart(payload)
    for window in windows:
        if not isinstance(window, dict):
            raise EpisodeIdentityBindingError("transport window must be an object")
        try:
            source_start = int(window["source_start_row"])
            target_start = int(window["target_start_row"])
            length = int(window["length"])
        except (KeyError, TypeError, ValueError) as exc:
            raise EpisodeIdentityBindingError("invalid transport window coordinates") from exc
        if length < 2:
            raise EpisodeIdentityBindingError("transport window must contain at least two rows")
        try:
            morphism = ChartTransportMorphism.from_dict(window["transport_morphism"])
        except (KeyError, TypeError, ValueError) as exc:
            raise EpisodeIdentityBindingError(
                "transport window needs a valid pointwise morphism"
            ) from exc
        source_chart = charts_by_sha.get(morphism.source_chart_sha256)
        target_chart = charts_by_sha.get(morphism.target_chart_sha256)
        if source_chart is None or target_chart is None:
            raise EpisodeIdentityBindingError(
                "transport morphism references an undeclared observation chart"
            )
        witnesses: list[TransportWitness] = []
        for offset in range(length):
            source_index = source_start + offset
            target_index = target_start + offset
            if source_index >= len(rows) or target_index >= len(rows):
                raise EpisodeIdentityBindingError("transport window exceeds episode")
            source_binding = by_index.get(source_index)
            target_binding = by_index.get(target_index)
            if not source_binding or source_binding.get("attestation_kind") != "exact_environment_replay":
                raise EpisodeIdentityBindingError(
                    f"transport source row {source_index} lacks direct replay"
                )
            if not target_binding or target_binding.get("attestation_kind") != "duplicate_transport":
                raise EpisodeIdentityBindingError(
                    f"transport target row {target_index} lacks duplicate binding"
                )
            if int(target_binding.get("source_row_index", -1)) != source_index:
                raise EpisodeIdentityBindingError("duplicate binding points outside its window")
            source, target = rows[source_index], rows[target_index]
            if (source.s, source.a, source.s_next) != (target.s, target.a, target.s_next):
                raise EpisodeIdentityBindingError(
                    f"transport row {target_index} changes state/action/successor"
                )
            if source_binding.get("identity") != target_binding.get("identity"):
                raise EpisodeIdentityBindingError(
                    f"transport row {target_index} changes transition identity"
                )
            witnesses.append(
                TransportWitness(
                    source_packet=_transport_packet(source, source_binding["identity"]),
                    target_packet=_transport_packet(target, target_binding["identity"]),
                    witness_ref=f"{path.name}:row:{source_index}->{target_index}",
                )
            )
            covered_duplicates.add(target_index)
        certificate = certify_pointwise_transport(
            source_chart=source_chart,
            target_chart=target_chart,
            morphism=morphism,
            witnesses=witnesses,
        )
        if not certificate.passed:
            raise EpisodeIdentityBindingError(
                "pointwise chart transport failed: "
                + json.dumps(list(certificate.failures)[:4], sort_keys=True)
            )
        expected_certificate_sha = str(window.get("certificate_sha256") or "")
        actual_certificate_sha = stable_sha256(certificate.to_dict())
        if expected_certificate_sha and expected_certificate_sha != actual_certificate_sha:
            raise EpisodeIdentityBindingError(
                "transport certificate_sha256 does not bind the certified window"
            )
    if covered_duplicates != duplicate_indices:
        raise EpisodeIdentityBindingError(
            "every duplicate transport binding must belong to one certified window"
        )

    result = list(rows)
    for index, binding in by_index.items():
        identity = TransitionIdentity.from_dict(binding.get("identity"))
        row = result[index]
        if row.identity is not None and row.identity != identity:
            raise EpisodeIdentityBindingError(
                f"sidecar conflicts with inline identity at row {index}"
            )
        result[index] = Transition(row.t, row.s, row.a, row.s_next, identity)
    return result


def rebind_identity_sidecar(path: "Path | str", rows: list[Transition]) -> bool:
    """Advance a valid identity sidecar across a compatible episode rewrite.

    The old episode digest is the only field allowed to become stale.  Every
    row binding, observation hash, inline identity, chart declaration,
    transport window, and certificate is revalidated against ``rows`` before
    the sidecar is rebound to the successor bytes.  A reorder, deletion, or
    mutation of a bound observation therefore fails before authority moves.
    """
    episode_path = Path(path)
    sidecar = episode_path.with_name(f"{episode_path.stem}.identity.json")
    if not sidecar.is_file():
        return False
    _apply_identity_sidecar(
        episode_path,
        rows,
        allow_stale_episode_binding=True,
    )
    payload = _identity_sidecar_payload(
        episode_path,
        allow_stale_episode_binding=True,
    )
    assert payload is not None
    payload["episode_sha256"] = _file_sha256(episode_path)
    tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(sidecar)
    return True


class EpisodeLog:
    """In-memory transition sequence with JSONL persistence and a content hash.

    Append-only by convention: rows are only ever added, and `content_hash`
    binds a synthesis receipt to the exact evidence it was earned from.
    """

    def __init__(
        self,
        transitions: "list[Transition] | None" = None,
        *,
        source_path: "Path | None" = None,
        source_sha256: "str | None" = None,
        source_stat: "tuple[int, int] | None" = None,
    ):
        self._rows: list[Transition] = list(transitions or [])
        self._content_hash_cache: str | None = None
        self._context_observation_index_cache: dict[str, set[str]] | None = None
        self._source_path = source_path
        self._source_sha256 = source_sha256
        self._source_stat = source_stat

    def append(
        self,
        s: Grid,
        a: int,
        s_next: Grid,
        t: "int | None" = None,
        *,
        identity: "TransitionIdentity | None" = None,
    ) -> None:
        # t defaults to the row index — correct ONLY for single-episode logs.
        # Multi-episode (reset-witnessing) logs MUST pass the environment's own
        # step, or every episode after the first records a wrong t and any
        # step-dependent law becomes unrecoverable from its own evidence.
        self.append_transition(
            Transition(len(self._rows) if t is None else t, s, a, s_next, identity)
        )

    def append_transition(self, transition: Transition) -> None:
        """Append an already-identified observation without reconstructing it."""
        if not isinstance(transition, Transition):
            raise TypeError("append_transition requires a Transition")
        self._rows.append(transition)
        self._content_hash_cache = None
        if self._context_observation_index_cache is not None:
            self._context_observation_index_cache.setdefault(
                transition.context_hash(), set()
            ).add(transition.observation_hash())

    def context_observation_index(self) -> dict[str, frozenset[str]]:
        """Return the compact context -> witnessed-consequence image.

        This is a derived membership index, not evidence authority.  It is
        maintained incrementally after its first construction and preserves
        multiple consequences for one context so collection cannot hide a
        determinism violation as a duplicate.
        """
        if self._context_observation_index_cache is None:
            index: dict[str, set[str]] = {}
            for row in self._rows:
                index.setdefault(row.context_hash(), set()).add(
                    row.observation_hash()
                )
            self._context_observation_index_cache = index
        return {
            context: frozenset(observations)
            for context, observations in self._context_observation_index_cache.items()
        }

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self) -> Iterator[Transition]:
        return iter(self._rows)

    def transitions(self) -> "tuple[Transition, ...]":
        return tuple(self._rows)

    def within_epoch_view(self, source_epoch: object | None = None) -> "EpisodeLog":
        """Return dynamics/unclassified rows in one lifecycle epoch.

        A full bank is evidence for law transfer; a planning quotient describes
        the active local chart.  Mixing prior-epoch presentations into that
        quotient makes stable structure appear stateful and can turn a sparse
        abstraction back into a raw-state cache.  An epoch is inferred only
        when the adapter supplies an ordered numeric lifecycle or every trusted
        row names the same opaque epoch.  Otherwise the full bank is returned;
        append order cannot manufacture lifecycle order.  Identity-less legacy
        rows remain in that full-bank view and are excluded from an explicit or
        inferred epoch view because no transport assigns them to that chart.
        """
        explicit_epoch = source_epoch is not None
        epoch = source_epoch
        if epoch is None:
            return self
        selected = [
            row for row in self._rows
            if row.identity is not None
            and row.identity.is_authoritative
            and not row.identity.is_boundary
            and row.identity.source_epoch == epoch
            and row.identity.target_epoch in (None, epoch)
        ]
        if selected:
            return EpisodeLog(selected)
        # An explicitly requested but unobserved epoch is an empty chart.  It
        # must never fall back to the all-epoch bank, because that silently
        # transports presentations across a lifecycle boundary.
        return EpisodeLog() if explicit_epoch else self

    def content_hash(self) -> str:
        if self._content_hash_cache is not None:
            return self._content_hash_cache
        rows = []
        for r in self._rows:
            row = [r.t, grid_to_lists(r.s), r.a, grid_to_lists(r.s_next)]
            if r.identity is not None:
                row.append(r.identity.to_dict())
            rows.append(row)
        payload = json.dumps(
            rows,
            separators=(",", ":"),
        ).encode()
        self._content_hash_cache = hashlib.sha256(payload).hexdigest()
        return self._content_hash_cache

    def write_jsonl(self, path: "Path | str") -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        sidecar = p.with_name(f"{p.stem}.identity.json")
        if sidecar.is_file() and p.is_file():
            # Validate proposed row positions and observations before replacing
            # bytes.  Only the episode digest may advance on a compatible write.
            _apply_identity_sidecar(
                p,
                self._rows,
                allow_stale_episode_binding=True,
            )
        with p.open("w") as f:
            for r in self._rows:
                row = {
                    "t": r.t,
                    "s": grid_to_lists(r.s),
                    "a": r.a,
                    "s_next": grid_to_lists(r.s_next),
                }
                if r.identity is not None:
                    row["identity"] = r.identity.to_dict()
                f.write(json.dumps(row) + "\n")
        if sidecar.is_file():
            rebind_identity_sidecar(p, self._rows)

    def append_jsonl(
        self,
        path: "Path | str",
        transitions: "list[Transition] | tuple[Transition, ...]",
    ) -> int:
        """Append observations to the bound source without rewriting its prefix.

        ``read_jsonl`` binds this object to the exact source bytes it decoded.
        The append takes an exclusive file lock, rechecks that byte identity,
        advances the sidecar digest over the same append, and only then extends
        the in-memory materialized view.  A concurrent writer is therefore an
        epoch conflict rather than silent last-writer-wins corruption.
        """
        rows = tuple(transitions)
        if not rows:
            return 0
        if any(not isinstance(row, Transition) for row in rows):
            raise TypeError("append_jsonl requires Transition rows")
        episode_path = Path(path)
        if self._source_path is None or self._source_sha256 is None:
            raise EpisodeIdentityBindingError(
                "append_jsonl requires an EpisodeLog loaded from the target source"
            )
        if episode_path.resolve() != self._source_path.resolve():
            raise EpisodeIdentityBindingError("episode append target changed identity")

        encoded = b"".join(
            (json.dumps(_transition_to_json_object(row)) + "\n").encode("utf-8")
            for row in rows
        )
        sidecar = episode_path.with_name(f"{episode_path.stem}.identity.json")
        sidecar_payload = None

        # POSIX is already a repository/runtime requirement.  Keep the import
        # local so read-only consumers do not pay or depend on the lock path.
        import fcntl

        with episode_path.open("r+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            digest = hashlib.sha256()
            handle.seek(0)
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
            prior_sha256 = digest.hexdigest()
            stat = os.fstat(handle.fileno())
            current_stat = (int(stat.st_size), int(stat.st_mtime_ns))
            if (
                prior_sha256 != self._source_sha256
                or (self._source_stat is not None and current_stat != self._source_stat)
            ):
                raise EpisodeIdentityBindingError(
                    "episode bytes changed after this evidence snapshot was loaded"
                )
            if sidecar.is_file():
                sidecar_payload = _identity_sidecar_payload(
                    episode_path,
                    episode_sha256=prior_sha256,
                )

            successor_digest = digest.copy()
            successor_digest.update(encoded)
            successor_sha256 = successor_digest.hexdigest()
            handle.seek(0, os.SEEK_END)
            if handle.tell() and not _file_ends_with_newline(handle):
                raise EpisodeIdentityBindingError(
                    "episode append requires a newline-terminated JSONL prefix"
                )
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())

            if sidecar_payload is not None:
                sidecar_payload["episode_sha256"] = successor_sha256
                tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
                tmp.write_text(
                    json.dumps(sidecar_payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                tmp.replace(sidecar)

            stat = os.fstat(handle.fileno())
            self._source_sha256 = successor_sha256
            self._source_stat = (int(stat.st_size), int(stat.st_mtime_ns))
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        for row in rows:
            self.append_transition(row)
        return len(rows)

    @classmethod
    def read_jsonl(cls, path: "Path | str") -> "EpisodeLog":
        episode_path = Path(path)
        rows = []
        digest = hashlib.sha256()
        with episode_path.open("rb") as handle:
            for raw_line in handle:
                digest.update(raw_line)
                line = raw_line.decode("utf-8")
                if not line.strip():
                    continue
                rows.append(_transition_from_json_object(json.loads(line)))
        episode_sha256 = digest.hexdigest()
        stat = episode_path.stat()
        return cls(
            _apply_identity_sidecar(
                episode_path,
                rows,
                episode_sha256=episode_sha256,
            ),
            source_path=episode_path,
            source_sha256=episode_sha256,
            source_stat=(int(stat.st_size), int(stat.st_mtime_ns)),
        )

    @classmethod
    def read_jsonl_indices(
        cls,
        path: "Path | str",
        indices: "set[int] | list[int] | tuple[int, ...]",
    ) -> dict[int, Transition]:
        """Read selected physical rows without materializing the full episode.

        Inline transition identities are preserved.  A direct-replay sidecar
        binding is checked against the episode bytes and selected observation.
        A sidecar-only duplicate-transport identity requires its multi-row
        commuting window, so indexed access rejects it instead of weakening the
        certificate.
        """

        episode_path = Path(path)
        wanted = {int(index) for index in indices}
        if any(index < 0 for index in wanted):
            raise IndexError("episode row indices must be non-negative")
        selected: dict[int, Transition] = {}
        physical_index = -1
        with episode_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                physical_index += 1
                if physical_index not in wanted:
                    continue
                selected[physical_index] = _transition_from_json_object(json.loads(line))
        missing = sorted(wanted - set(selected))
        if missing:
            raise IndexError(f"episode rows outside log: {missing}")

        payload = _identity_sidecar_payload(episode_path)
        if payload is None or not wanted:
            return selected
        bindings = payload.get("bindings")
        by_index = {
            int(binding["row_index"]): binding
            for binding in bindings
            if isinstance(binding, dict) and "row_index" in binding
        }
        for index in wanted:
            binding = by_index.get(index)
            if binding is None:
                continue
            row = selected[index]
            if binding.get("observation_sha256") != row.observation_hash():
                raise EpisodeIdentityBindingError(
                    f"identity binding row {index} does not match transition bytes"
                )
            kind = str(binding.get("attestation_kind") or "")
            if kind == "duplicate_transport":
                if row.identity is None:
                    raise EpisodeIdentityBindingError(
                        "indexed access cannot establish a sidecar-only duplicate transport"
                    )
                continue
            if kind != "exact_environment_replay":
                raise EpisodeIdentityBindingError(
                    f"identity binding row {index} has unsupported attestation_kind"
                )
            identity = TransitionIdentity.from_dict(binding.get("identity"))
            if row.identity is not None and row.identity != identity:
                raise EpisodeIdentityBindingError(
                    f"sidecar conflicts with inline identity at row {index}"
                )
            selected[index] = Transition(row.t, row.s, row.a, row.s_next, identity)
        return selected


def _transition_from_json_object(payload: dict) -> Transition:
    identity_payload = payload.get("identity")
    identity = (
        TransitionIdentity.from_dict(identity_payload)
        if identity_payload is not None
        else None
    )
    return Transition(
        payload["t"],
        grid_from_lists(payload["s"]),
        payload["a"],
        grid_from_lists(payload["s_next"]),
        identity,
    )


def _transition_to_json_object(row: Transition) -> dict:
    payload = {
        "t": row.t,
        "s": grid_to_lists(row.s),
        "a": row.a,
        "s_next": grid_to_lists(row.s_next),
    }
    if row.identity is not None:
        payload["identity"] = row.identity.to_dict()
    return payload


def _file_ends_with_newline(handle) -> bool:
    handle.seek(-1, os.SEEK_END)
    return handle.read(1) == b"\n"
