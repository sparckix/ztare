"""Typed capability contracts — the interfaces a plug-in implements to extend the ZTARE kernel.

A Scenario COMPOSES capabilities by name; the registry (`scenarios.registry`) resolves each name to an object
satisfying one of these Protocols. We use structural `Protocol`s (not ABCs) deliberately: a third-party
capability only needs the right methods — no base-class import, no inheritance coupling — so plug-ins stay
decoupled from the kernel. All are `runtime_checkable` so a caller can `isinstance`-check conformance.

Three capability kinds today; the pattern extends to more (each is a `(kind, name)` in the registry):
  * EvidenceProvider — where a scenario's evidence comes from (local files today; Confluence/Jira/telemetry next).
  * Renderer          — how a verdict is emitted (markdown today; workbench/obsidian/pdf next).
  * Solver            — a deeper reasoning engine a scenario can call (leanmill / fit adapt to this contract;
                        an abduction / ARC engine can plug in later WITHOUT touching the kernel).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class EvidenceItem:
    """One piece of evidence a claim can bind to (provenance-preserving)."""
    ref: str                                        # stable identifier: path, URL, ticket id
    title: str = ""
    kind: str = "document"                          # document | data | interview | ticket | telemetry | ...
    body: str = ""                                  # content or summary, when cheaply available
    meta: "dict[str, Any]" = field(default_factory=dict)


@dataclass(frozen=True)
class RenderResult:
    """The output of rendering a verdict."""
    path: str = ""                                  # where it was written, if anywhere
    text: str = ""                                  # rendered text (for in-memory / preview)
    kind: str = "markdown"


@runtime_checkable
class EvidenceProvider(Protocol):
    """Supplies the evidence a scenario's claims bind to. Read-only; provenance-preserving."""
    name: str

    def list_evidence(self, project: str) -> "list[EvidenceItem]":
        """Enumerate available evidence for a project (cheap — refs + titles; body optional)."""
        ...

    def fetch(self, ref: str) -> "EvidenceItem | None":
        """Resolve one evidence ref to its full item, or None if it can't be found."""
        ...


@runtime_checkable
class Renderer(Protocol):
    """Emits a verdict / result in a target format."""
    name: str

    def render(self, result: "dict[str, Any]", *, dest: str = "") -> RenderResult:
        """Render `result`; write to `dest` if given, else return the text in-memory."""
        ...


@runtime_checkable
class Solver(Protocol):
    """A deeper reasoning engine a scenario can invoke on a bounded sub-problem. The existing leanmill and fit
    engines adapt to this contract; a future abduction / ARC engine plugs in here."""
    name: str

    def solve(self, problem: "dict[str, Any]") -> "dict[str, Any]":
        """Attempt the problem; return a structured result (never raises for an ordinary 'no solution')."""
        ...


@runtime_checkable
class Recheck(Protocol):
    """A RE-EXECUTABLE check that re-earns (or fails to re-earn) a warrant for a project. PURE by contract: it
    re-runs a deterministic computation and REPORTS whether it passes — it never writes the graph. The recheck
    DRIVER (`scenarios.warrant_recheck`) is the single door that promotes / demotes / expires the warrant from a
    passing / failing / stale result, so a capability can never mint a warrant by fiat. This is how a scenario
    declares 'this evidence RECOMPUTES' (a covenant ratio, a liquidity runway) WITHOUT a per-scenario script
    writing state — the covenant recompute is a `recheck` capability, not a bolted-on demo."""
    name: str

    def recheck(self, project: str) -> "dict[str, Any]":
        """Re-execute the bound computation for `project`. Return a receipt:
        `{passed: bool, warrant: 'W1'|'W0', target: {src, kind, dst, text}, detail: str}`.
        `warrant` is the class a PASS licenses (recompute->W1, kernel_cert->W0); `target` NAMES the evidence
        node + supporting edge the check warrants (stable ids the DRIVER owns). Deterministic, side-effect-free;
        a raise is treated by the driver as a FAILED check (fail-closed)."""
        ...


# The required-method map the registry uses for a robust, data-attribute-agnostic conformance check
# (runtime_checkable isinstance only guarantees method presence — we assert exactly that at registration).
REQUIRED_METHODS: "dict[str, tuple[str, ...]]" = {
    "evidence": ("list_evidence", "fetch"),
    "renderer": ("render",),
    "solver": ("solve",),
    "recheck": ("recheck",),
}
