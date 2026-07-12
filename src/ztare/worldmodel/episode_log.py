"""Canonical append-only episode record for interactive substrates (GP-250).

The log is the system of record: synthesis, gates, rollouts, and audits read
transitions from here, never from a live environment. Live environment steps
are spent only to acquire new information; everything downstream replays free.
Recorded logs double as deterministic CI fixtures.

Format: JSONL, one transition per row:
    {"t": int, "s": [[int,...],...], "a": int, "s_next": [[...],...]}
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from ztare.worldmodel.grid_dsl import Grid, grid_from_lists, grid_to_lists


@dataclass(frozen=True)
class Transition:
    t: int
    s: Grid
    a: int
    s_next: Grid


class EpisodeLog:
    """In-memory transition sequence with JSONL persistence and a content hash.

    Append-only by convention: rows are only ever added, and `content_hash`
    binds a synthesis receipt to the exact evidence it was earned from.
    """

    def __init__(self, transitions: "list[Transition] | None" = None):
        self._rows: list[Transition] = list(transitions or [])

    def append(self, s: Grid, a: int, s_next: Grid, t: "int | None" = None) -> None:
        # t defaults to the row index — correct ONLY for single-episode logs.
        # Multi-episode (reset-witnessing) logs MUST pass the environment's own
        # step, or every episode after the first records a wrong t and any
        # step-dependent law becomes unrecoverable from its own evidence.
        self._rows.append(Transition(len(self._rows) if t is None else t, s, a, s_next))

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self) -> Iterator[Transition]:
        return iter(self._rows)

    def transitions(self) -> "tuple[Transition, ...]":
        return tuple(self._rows)

    def content_hash(self) -> str:
        payload = json.dumps(
            [[r.t, grid_to_lists(r.s), r.a, grid_to_lists(r.s_next)] for r in self._rows],
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    def write_jsonl(self, path: "Path | str") -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w") as f:
            for r in self._rows:
                f.write(json.dumps({"t": r.t, "s": grid_to_lists(r.s), "a": r.a,
                                    "s_next": grid_to_lists(r.s_next)}) + "\n")

    @classmethod
    def read_jsonl(cls, path: "Path | str") -> "EpisodeLog":
        rows = []
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            rows.append(Transition(d["t"], grid_from_lists(d["s"]), d["a"],
                                   grid_from_lists(d["s_next"])))
        return cls(rows)
