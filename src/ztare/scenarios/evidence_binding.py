"""Evidence-binding (COMPOUNDER, KERNEL). Binds a cited excerpt to a real source with a tamper-evident record,
so a claim's evidence is a system-of-record citation, not a vibe.

The invariant (Fable): the KERNEL owns the binding record — source id + content hash + timestamp + a VERBATIM
excerpt check (the cited excerpt must appear verbatim in the fetched content, or the binding is refused,
fail-closed). Connectors (Jira / Confluence / telemetry fetchers) are pure PLUGINs behind the existing
`EvidenceProvider` Protocol — they FETCH, the kernel BINDS. Deferred, explicitly (the genuinely hard external
problems, not strawmanned): re-verification on staleness, and ACLs / who-may-see-what. A fetch hash + timestamp
is the v1 staleness answer (a changed hash ⇒ re-bind).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


def _norm(text: str) -> str:
    return " ".join((text or "").split())


@dataclass(frozen=True)
class EvidenceBinding:
    """A governed evidence binding: a cited excerpt tied to a source by content hash. The excerpt is
    verbatim-in-source by construction (only `bind_evidence` mints these)."""
    source_id: str
    content_sha256: str
    excerpt: str
    fetched_at: str = ""     # ISO timestamp, passed IN (kernel does no clock reads)

    def is_stale(self, current_content: str) -> bool:
        """v1 staleness: the source changed if its hash no longer matches. (Re-verification policy is deferred.)"""
        return hashlib.sha256((current_content or "").encode("utf-8")).hexdigest() != self.content_sha256


def bind_evidence(source_id: str, content: str, excerpt: str, *, fetched_at: str = "") -> "EvidenceBinding | None":
    """Bind `excerpt` to `source_id`+`content`: GATE that the excerpt appears VERBATIM (whitespace-normalized)
    in the content, then hash the content. Returns an EvidenceBinding, or None when the excerpt is NOT in the
    content — a citation that drifted from its source is refused, fail-closed. No LLM."""
    if not excerpt.strip() or _norm(excerpt) not in _norm(content):
        return None
    return EvidenceBinding(
        source_id=source_id,
        content_sha256=hashlib.sha256((content or "").encode("utf-8")).hexdigest(),
        excerpt=excerpt.strip(),
        fetched_at=fetched_at,
    )


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    content = "Ticket ABC-123: 9 of 12 interviewees hit the missing-payment-method wall during checkout."
    good = bind_evidence("jira:ABC-123", content, "9 of 12 interviewees hit the missing-payment-method wall",
                         fetched_at="2026-07-09T00:00:00Z")
    ok("a verbatim excerpt binds", good is not None and good.source_id == "jira:ABC-123")
    ok("binding carries a content hash + timestamp", bool(good.content_sha256) and good.fetched_at.endswith("Z"))
    ok("a drifted excerpt is REFUSED (fail-closed)",
       bind_evidence("jira:ABC-123", content, "everyone loved the checkout flow") is None)
    ok("empty excerpt is refused", bind_evidence("s", content, "  ") is None)
    ok("staleness: a changed source no longer matches the hash",
       good.is_stale(content + " (edited)") and not good.is_stale(content))

    print("EVIDENCE-BINDING SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
