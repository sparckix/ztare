"""LeanMill → cognitive-firm formal-verification PROVIDER ADAPTER.

LeanMill is a `formal-verification-provider/v1` adapter: it RUNS the checker (the Lean/SMT faithfulness firewall
+ anti-laundering kernel) and emits a provider-neutral, SIGNED payload that cognitive-firm's kernel RECORDS (via
`cognitive-firm-formal-verification create-from-provider-payload`). The boundary is the PAYLOAD — no import
coupling: cognitive-firm never imports ztare/leanmill; leanmill never imports cognitive_firm. Either side speaks
only the v1 JSON schema + an Ed25519 signature over a canonical normalization of it. This module is the leanmill
half: build the payload, map a leanmill result to the verdict semantics cognitive-firm expects, and sign it with
BYTE-IDENTICAL canonicalization so the signature verifies against the kernel's installed provider key.

Verdict mapping (cognitive-firm contract — DO NOT conflate):
  • verified     — the faithfulness firewall PASSED and the checker certificate PASSED.
  • refuted      — the checker found a COUNTEREXAMPLE to the claim (MUST include counterexample_ref).
  • invalid      — the certificate/payload is malformed, OR anti-laundering / faithfulness FAILED, so the claim
                   cannot be trusted at all. An UNFAITHFUL formalization is `invalid`, NOT `verified` and NOT a
                   `refuted` of the original claim (it proved/refuted a DIFFERENT statement).
  • inconclusive — timeout, missing checker, undecidable boundary, or insufficient evidence.

Evidence goes in REFS, not prose: firewall receipts → `faithfulness_refs`; Lean logs / SMT model / proof
artifact → `checker_evidence_refs`; matched-negative-control + anti-laundering receipts → `metadata`. The
installed `leanmill-formal-verification` trust overlay only treats a `verified` row as clean evidence when it
carries (a) a `metadata.provider_payload_signature` that verifies against the configured public key, (b) a
non-empty `faithfulness_refs`, and (c) a non-empty `checker_evidence_refs`. `certify_demo_to_payload` populates
all three.

SIGNING PARITY (what verification hinges on): cognitive-firm signs over `canonical_provider_payload_bytes`, which normalizes the
payload THROUGH the `FormalVerificationProviderPayload` dataclass — it DROPS unknown top-level keys, FILLS missing
optional fields with their defaults (`assumption_refs:[]`, …), STRIPS the 4 signature-bookkeeping keys from
`metadata`, and serializes with `sort_keys=True, separators=(",",":"), ensure_ascii=True`. We reproduce that
EXACTLY here (without importing cognitive_firm); the selftest cross-checks byte-equality against the kernel's own
canonicalizer when it happens to be importable on the box.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Literal, Optional

SCHEMA_VERSION = "formal-verification-provider/v1"
PROVIDER = "leanmill"

FormalSystem = Literal["lean", "smt", "isabelle", "coq", "alloy", "tla", "other"]
PropertyClass = Literal["policy", "schema", "contract", "evidence_chain", "workflow_safety", "math", "other"]
Verdict = Literal["verified", "refuted", "inconclusive", "invalid"]

# The EXACT field surface cognitive-firm's FormalVerificationProviderPayload dataclass serializes (asdict).
# Canonical signing bytes are computed over THIS normalized set so our signature matches the kernel's
# re-canonicalization byte-for-byte: required strings, list fields default [], optional fields default None.
_CANON_REQUIRED = (
    "schema_version", "provider", "formal_system", "verifier_ref", "property_class",
    "subject_ref", "subject_digest", "claim_ref", "certificate_ref", "certificate_digest",
    "verdict", "verification_summary",
)
_CANON_LISTS = ("assumption_refs", "input_refs", "output_refs", "faithfulness_refs", "checker_evidence_refs")
_CANON_OPTIONAL = ("counterexample_ref", "tenant_id", "project_id", "run_id")
# metadata keys the kernel strips before signing (signature bookkeeping is added AFTER the signature is computed)
_SIGNATURE_METADATA_KEYS = frozenset({
    "provider_payload_signature", "provider_payload_signature_verified",
    "provider_payload_digest", "provider_payload_signature_key_ref",
})


def sha256_ref(text: str) -> str:
    """`sha256:<hex>` digest of a UTF-8 artifact (subject / certificate), so the kernel records a content hash."""
    return "sha256:" + hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def map_verdict(*, faithful: Optional[bool], closed: Optional[bool], governance_ratified: Optional[bool],
                counterexample: Optional[str] = None, timed_out: bool = False,
                checker_available: bool = True, malformed: bool = False) -> Verdict:
    """Map a leanmill certify/firewall result to the cognitive-firm verdict. Order matters — a faithfulness or
    anti-laundering FAILURE is `invalid` (the claim can't be trusted), checked BEFORE any closed/refuted read so
    an unfaithful formalization is never reported as `verified` or as a `refuted` of the ORIGINAL claim."""
    if malformed or not checker_available:
        return "inconclusive" if (not checker_available and not malformed) else "invalid"
    if faithful is False:
        return "invalid"                      # proved/refuted a DIFFERENT statement — claim untrustworthy
    if governance_ratified is False:
        return "invalid"                      # anti-laundering / statement-integrity caught a laundered close
    if counterexample:
        return "refuted"                      # checker found a real counterexample to the (faithful) claim
    if timed_out:
        return "inconclusive"
    if closed and (governance_ratified is True or governance_ratified is None):
        return "verified"                     # faithful + checker-closed + ratified
    return "inconclusive"                     # no close, no counterexample → insufficient evidence


def build_payload(
    *,
    formal_system: FormalSystem,
    property_class: PropertyClass,
    verdict: Verdict,
    subject_ref: str,
    subject_text: str,
    claim_ref: str,
    certificate_ref: str,
    certificate_text: str,
    verifier_ref: str,
    verification_summary: str,
    faithfulness_refs: "Optional[list[str]]" = None,
    checker_evidence_refs: "Optional[list[str]]" = None,
    output_refs: "Optional[list[str]]" = None,
    assumption_refs: "Optional[list[str]]" = None,
    input_refs: "Optional[list[str]]" = None,
    anti_laundering: "Optional[dict[str, Any]]" = None,
    extra_metadata: "Optional[dict[str, Any]]" = None,
    counterexample_ref: Optional[str] = None,
    run_id: Optional[str] = None,
    project_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> "dict[str, Any]":
    """Build the `formal-verification-provider/v1` payload cognitive-firm records. Computes the content digests;
    routes evidence into refs. Enforces the contract invariants `refuted ⇒ counterexample_ref` and
    `verified ⇒ no counterexample_ref` here, not downstream. Only emits SCHEMA fields (no `subject_id` — that is
    not part of the v1 payload and would be silently dropped from the signed surface)."""
    if verdict == "refuted" and not counterexample_ref:
        raise ValueError("verdict 'refuted' requires a counterexample_ref (the contract demands it)")
    if verdict == "verified" and counterexample_ref:
        raise ValueError("verdict 'verified' must NOT carry a counterexample_ref")
    metadata: "dict[str, Any]" = dict(extra_metadata or {})
    metadata["anti_laundering"] = dict(anti_laundering or {})
    payload: "dict[str, Any]" = {
        "schema_version": SCHEMA_VERSION,
        "provider": PROVIDER,
        "formal_system": formal_system,
        "verifier_ref": verifier_ref,
        "property_class": property_class,
        "subject_ref": subject_ref,
        "subject_digest": sha256_ref(subject_text),
        "claim_ref": claim_ref,
        "certificate_ref": certificate_ref,
        "certificate_digest": sha256_ref(certificate_text),
        "verdict": verdict,
        "verification_summary": verification_summary,
        "assumption_refs": list(assumption_refs or []),
        "input_refs": list(input_refs or []),
        "output_refs": list(output_refs or []),
        "faithfulness_refs": list(faithfulness_refs or []),
        "checker_evidence_refs": list(checker_evidence_refs or []),
        "counterexample_ref": counterexample_ref,
        "run_id": run_id,
        "metadata": metadata,
    }
    for k, v in (("project_id", project_id), ("tenant_id", tenant_id)):
        if v is not None:
            payload[k] = v
    return payload


# --------------------------------------------------------------------------------------------------------------
# Canonicalization + Ed25519 signing — byte-identical to cognitive_firm.orchestration.formal_verification
# (canonical_provider_payload_bytes / sign_provider_payload), reproduced WITHOUT importing cognitive_firm.
# --------------------------------------------------------------------------------------------------------------

def _canonical_signing_obj(payload: "dict[str, Any]") -> "dict[str, Any]":
    """Normalize `payload` to the kernel's signed surface: only the dataclass fields, defaults filled, unknown
    top-level keys dropped, signature-bookkeeping stripped from metadata."""
    raw: "dict[str, Any]" = {}
    for k in _CANON_REQUIRED:
        raw[k] = payload[k]                              # required — must exist (build_payload guarantees them)
    for k in _CANON_LISTS:
        raw[k] = list(payload.get(k) or [])
    for k in _CANON_OPTIONAL:
        raw[k] = payload.get(k)                          # default None
    md = payload.get("metadata") or {}
    if not isinstance(md, dict):
        raise ValueError("metadata must be a JSON object")
    raw["metadata"] = {k: v for k, v in md.items() if k not in _SIGNATURE_METADATA_KEYS}
    return raw


def canonical_provider_payload_bytes(payload: "dict[str, Any]") -> bytes:
    """The exact bytes a provider SIGNS and the kernel re-hashes. `ensure_ascii=True` + sorted keys + tight
    separators, over the normalized dataclass surface — DO NOT change without re-validating signing parity."""
    return json.dumps(
        _canonical_signing_obj(payload),
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("utf-8")


def canonical_json(payload: "dict[str, Any]") -> str:
    """str view of the canonical SIGNING surface (`canonical_provider_payload_bytes` decoded). This is the
    signed/re-hashed normalization, NOT the wire payload — use `to_transport_json` for the file handed to the
    `create-from-provider-payload` CLI (which keeps every field incl. the signature in metadata)."""
    return canonical_provider_payload_bytes(payload).decode("utf-8")


def provider_payload_digest(payload: "dict[str, Any]") -> str:
    """`sha256:<hex>` over the canonical signing bytes — matches the kernel's `provider_payload_digest`."""
    return "sha256:" + hashlib.sha256(canonical_provider_payload_bytes(payload)).hexdigest()


def to_transport_json(payload: "dict[str, Any]", *, indent: Optional[int] = 2) -> str:
    """The full wire payload written to the file for `cognitive-firm-formal-verification
    create-from-provider-payload` — keeps ALL fields including `metadata.provider_payload_signature`."""
    return json.dumps(payload, sort_keys=True, indent=indent, ensure_ascii=True)


def generate_keypair() -> "tuple[str, str]":
    """Generate a fresh Ed25519 keypair as (private_pem, public_pem), matching cognitive-firm's encoding
    (PKCS#8 unencrypted private, SubjectPublicKeyInfo public). The private PEM is secret; ship only the public."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    sk = Ed25519PrivateKey.generate()
    priv = sk.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    pub = sk.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return priv, pub


def sign_payload(payload: "dict[str, Any]", private_key_pem: str) -> str:
    """Return `ed25519:<hex>` — an Ed25519 signature over `canonical_provider_payload_bytes(payload)`, identical
    to cognitive-firm's `sign_provider_payload`. Sign BEFORE attaching the signature to metadata."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("private key is not an Ed25519 key")
    return "ed25519:" + key.sign(canonical_provider_payload_bytes(payload)).hex()


def attach_signature(payload: "dict[str, Any]", private_key_pem: str) -> "dict[str, Any]":
    """Sign `payload` and write the signature into `metadata.provider_payload_signature` (in place); return it."""
    sig = sign_payload(payload, private_key_pem)
    payload.setdefault("metadata", {})["provider_payload_signature"] = sig
    return payload


def verify_payload_signature(payload: "dict[str, Any]", public_key_pem: str,
                             signature: Optional[str] = None) -> bool:
    """Local round-trip check: verify the payload's Ed25519 signature against `public_key_pem`. Mirrors the
    kernel's `verify_provider_payload_signature` (same canonical bytes). Returns False on a bad signature;
    raises only on structurally-unusable inputs."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if signature is None:
        signature = (payload.get("metadata") or {}).get("provider_payload_signature")
    if not isinstance(signature, str) or not signature.strip():
        raise ValueError("no provider_payload_signature to verify")
    raw = signature.split(":", 1)[1] if signature.startswith("ed25519:") else signature
    key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("public key is not an Ed25519 key")
    try:
        key.verify(bytes.fromhex(raw), canonical_provider_payload_bytes(payload))
        return True
    except InvalidSignature:
        return False


# --------------------------------------------------------------------------------------------------------------
# End-to-end adapter: run the leanmill firewall (faithful + matched-laundered control), map the verdict, build a
# SIGNED payload with non-empty faithfulness_refs + checker_evidence_refs (what the trust overlay requires).
# --------------------------------------------------------------------------------------------------------------

def render_audit(payload: "dict[str, Any]") -> str:
    """Render the LEGIBLE claim audit distilled from this provider payload — the human-readable certificate a
    consumer reads to decide whether to trust the result (vs the machine-facing payload). Pure distillation via
    the substrate-neutral `common.claim_audit`; adds NO verification, reports what governance already found."""
    from ztare.common.claim_audit import from_provider_payload, render_markdown
    return render_markdown(from_provider_payload(payload))


def _slug(text: str) -> str:
    keep = "".join(c if (c.isalnum() or c in "-_") else "-" for c in (text or "").lower())
    while "--" in keep:
        keep = keep.replace("--", "-")
    return keep.strip("-")[:60] or "claim"


def certify_demo_to_payload(
    *,
    rule_nl: str,
    faithful_src: str,
    predicate: str,
    cases: "list[tuple[str, bool]]",
    subject_ref: str,
    claim_ref: str,
    property_class: PropertyClass = "policy",
    laundered_src: Optional[str] = None,
    smt_boundary: Optional[dict] = None,
    battery_fn=None,
    verifier_ref: str = "leanmill:certify-demo@v1",
    private_key_pem: Optional[str] = None,
    run_id: Optional[str] = None,
) -> "dict[str, Any]":
    """Run the certify firewall on a candidate Lean formalization against labelled `cases` (optionally with a
    matched LAUNDERED control), map the result to a v1 verdict, and return a payload (signed if a key is given).

    `battery_fn(lean_src, predicate, cases) -> Optional[bool]` is the kernel call (defaults to leanmill's
    `default_instance_battery`); inject a stub for unit tests so this stays Lean-free + deterministic. The
    matched-laundered control is the anti-laundering signal: a candidate that passes while the laundered twin is
    NOT rejected means the apparatus can't separate them → `governance_ratified=False` → `invalid`."""
    if battery_fn is None:                               # lazy import: the pure payload/sign path stays dep-free
        from ztare.leanmill.solver.autoformalize import default_instance_battery
        battery_fn = lambda src, pred, cs: default_instance_battery(src, pred, cs)  # noqa: E731

    faithful_ok = battery_fn(faithful_src, predicate, cases)
    # The matched-laundered control is TRI-state: None (control timed out / couldn't run) must NOT be conflated
    # with False (the apparatus ADMITTED the launder — a real governance failure). `(None is False)` is False,
    # so the naive form would force `invalid` on a mere timeout — the seam this distinguishes.
    laundered_rejected: Optional[bool] = None           # None ⇒ no control OR control inconclusive
    if laundered_src is not None:
        laundered_ok = battery_fn(laundered_src, predicate, cases)
        if laundered_ok is None:
            laundered_rejected = None                    # control timed out — unknown, don't penalize
        else:
            laundered_rejected = (laundered_ok is False)  # rejected iff the apparatus FAILED the laundered twin

    # governance ratification: True iff the control discriminated; False iff the launder was ADMITTED; None when
    # there was no control or it was inconclusive (then map_verdict defers to the faithful battery, whose own
    # boundary case ⟨449⟩→inadequate already discriminates the off-by-one launder).
    governance_ratified: Optional[bool]
    if laundered_rejected is None:
        governance_ratified = None
    else:
        governance_ratified = bool(laundered_rejected)

    verdict = map_verdict(
        faithful=faithful_ok,
        closed=(faithful_ok is True),
        governance_ratified=governance_ratified,
        timed_out=(faithful_ok is None),
        checker_available=(faithful_ok is not None),
    )

    slug = _slug(claim_ref.rsplit("/", 1)[-1] or claim_ref)
    faith_ref = f"leanmill://faithfulness/{slug}"
    checker_ref = f"leanmill://kernel-log/{slug}"
    cert_ref = f"leanmill://certificates/{slug}"

    faith_record = {
        "rule_nl": rule_nl, "predicate": predicate, "labelled_cases": [list(c) for c in cases],
        "faithful_battery_pass": faithful_ok, "matched_laundered_control_rejected": laundered_rejected,
        "smt_boundary": smt_boundary,
    }
    checker_lines = [
        f"battery({predicate}): faithful_candidate -> {faithful_ok}",
        *([f"battery({predicate}): laundered_control -> rejected={laundered_rejected}"]
          if laundered_rejected is not None else []),
        f"cases={cases}",
    ]
    if laundered_src is None:
        mnc = "none"                                     # no laundered control was supplied
    elif laundered_rejected is True:
        mnc = "rejected"                                 # apparatus discriminated (good)
    elif laundered_rejected is False:
        mnc = "admitted"                                 # apparatus could not separate the launder (governance fail)
    else:
        mnc = "inconclusive"                             # control ran but timed out
    anti_laundering = {
        "statement_integrity": "pass" if faithful_ok else "n/a",
        "matched_negative_control": mnc,
        "smt_boundary_case": (smt_boundary or {}).get("boundary") if smt_boundary else None,
    }
    provider_artifacts = {
        "certificate": {"sha256": sha256_ref(faithful_src), "lean_src": faithful_src},
        "faithfulness": {"sha256": sha256_ref(json.dumps(faith_record, sort_keys=True)), **faith_record},
        "checker_log": {"sha256": sha256_ref("\n".join(checker_lines)), "lines": checker_lines},
    }

    summary = {
        "verified": "faithful formalization + matched-laundered control rejected; kernel battery certified every labelled case.",
        "invalid": "formalization is NOT faithful (failed a labelled/boundary case) or the laundered control was not rejected.",
        "inconclusive": "checker could not decide (timeout / unavailable).",
        "refuted": "checker found a counterexample to the claim.",
    }[verdict]

    payload = build_payload(
        formal_system="lean",
        property_class=property_class,
        verdict=verdict,
        subject_ref=subject_ref,
        subject_text=rule_nl,
        claim_ref=claim_ref,
        certificate_ref=cert_ref,
        certificate_text=faithful_src,
        verifier_ref=verifier_ref,
        verification_summary=summary,
        faithfulness_refs=[faith_ref],
        checker_evidence_refs=[checker_ref],
        anti_laundering=anti_laundering,
        extra_metadata={"provider_artifacts": provider_artifacts},
        run_id=run_id,
    )
    if private_key_pem:
        attach_signature(payload, private_key_pem)
    return payload


# Basel III demo fixture (mirrors scripts/public/demo/leanmill_certify_demo.py) — the first certify path.
_DEMO_RULE = "Basel III: a bank is ADEQUATELY CAPITALIZED iff its CET1 ratio is at least the 4.50% minimum (cet1Bp >= 450)."
_DEMO_FAITHFUL = ("structure Bank where\n  cet1Bp : Nat\n\n"
                  "abbrev adequate (b : Bank) : Prop := 450 ≤ b.cet1Bp\n")
_DEMO_LAUNDERED = ("structure Bank where\n  cet1Bp : Nat\n\n"
                   "abbrev adequate (b : Bank) : Prop := 449 ≤ b.cet1Bp\n")
_DEMO_CASES = [("⟨460⟩", True), ("⟨450⟩", True), ("⟨449⟩", False), ("⟨300⟩", False)]


def emit_demo_payload(*, lean_root: Optional[str] = None, private_key_pem: Optional[str] = None,
                      run_id: Optional[str] = None) -> "dict[str, Any]":
    """Run the Basel certify demo against the real Lean kernel and return a signed v1 payload. Requires a live
    Lean substrate (`lean_root`, default ztare_proofs) — slow on a cold box, ~instant once the warm REPL is up."""
    from pathlib import Path
    root = lean_root or str(Path(__file__).resolve().parents[3] / "ztare_proofs")
    from ztare.leanmill.solver.autoformalize import default_instance_battery
    battery_fn = lambda src, pred, cs: default_instance_battery(src, pred, cs, sandbox=root)  # noqa: E731
    return certify_demo_to_payload(
        rule_nl=_DEMO_RULE, faithful_src=_DEMO_FAITHFUL, predicate="adequate", cases=_DEMO_CASES,
        subject_ref="rule://basel/cet1", claim_ref="claim://basel/cet1-threshold",
        laundered_src=_DEMO_LAUNDERED, smt_boundary={"boundary": 449, "faithful": "450<=x", "laundered": "449<=x"},
        battery_fn=battery_fn, private_key_pem=private_key_pem, run_id=run_id,
    )


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    # verdict mapping — the four contract cases + the decisive "unfaithful ⇒ invalid, never verified/refuted"
    ok("verified: faithful + closed + ratified",
       map_verdict(faithful=True, closed=True, governance_ratified=True) == "verified")
    ok("invalid: UNFAITHFUL is invalid (not verified, not refuted)",
       map_verdict(faithful=False, closed=True, governance_ratified=True, counterexample="x=449") == "invalid")
    ok("invalid: governance caught a laundered close",
       map_verdict(faithful=True, closed=True, governance_ratified=False) == "invalid")
    ok("refuted: faithful claim with a counterexample",
       map_verdict(faithful=True, closed=False, governance_ratified=None, counterexample="cet1Bp=449") == "refuted")
    ok("inconclusive: timeout", map_verdict(faithful=True, closed=False, governance_ratified=None, timed_out=True) == "inconclusive")
    ok("inconclusive: no checker", map_verdict(faithful=None, closed=None, governance_ratified=None, checker_available=False) == "inconclusive")
    ok("inconclusive: no close, no counterexample",
       map_verdict(faithful=True, closed=False, governance_ratified=None) == "inconclusive")

    # payload shape + digests + the refuted/verified counterexample invariants
    p = build_payload(formal_system="smt", property_class="policy", verdict="verified",
                      subject_ref="rule://basel/cet1", subject_text="cet1Bp >= 450",
                      claim_ref="claim://basel", certificate_ref="leanmill://certificates/basel",
                      certificate_text="theorem ... := by decide", verifier_ref="leanmill:certify@v1",
                      verification_summary="faithful + SMT-boundary battery kernel-certified",
                      faithfulness_refs=["leanmill://faithfulness/basel"],
                      checker_evidence_refs=["leanmill://kernel-log/basel"],
                      anti_laundering={"statement_integrity": "pass", "mnc": "pass"}, run_id="run_1")
    ok("payload schema_version + provider", p["schema_version"] == SCHEMA_VERSION and p["provider"] == "leanmill")
    ok("payload digests are sha256 of the artifacts",
       p["subject_digest"] == sha256_ref("cet1Bp >= 450") and p["certificate_digest"].startswith("sha256:"))
    ok("payload routes anti-laundering into metadata", p["metadata"]["anti_laundering"]["statement_integrity"] == "pass")
    try:
        build_payload(formal_system="smt", property_class="policy", verdict="refuted",
                      subject_ref="s", subject_text="s", claim_ref="c", certificate_ref="r",
                      certificate_text="t", verifier_ref="v", verification_summary="x")  # no counterexample_ref
        ok("refuted-without-counterexample raises", False)
    except ValueError:
        ok("refuted-without-counterexample raises", True)

    # canonicalization: drops unknown keys, fills list defaults, strips signature bookkeeping, ensure_ascii
    pe = dict(p)
    pe["subject_id"] = "DROP_ME"                                   # unknown top-level key → must be dropped
    pe["metadata"] = {**p["metadata"], "provider_payload_signature": "ed25519:dead", "extra": "keep"}
    obj = _canonical_signing_obj(pe)
    ok("canonical drops unknown top-level keys", "subject_id" not in obj)
    ok("canonical fills list defaults (assumption_refs/input_refs)",
       obj["assumption_refs"] == [] and obj["input_refs"] == [])
    ok("canonical strips signature bookkeeping but keeps real metadata",
       "provider_payload_signature" not in obj["metadata"] and obj["metadata"].get("extra") == "keep")
    cb = canonical_provider_payload_bytes(pe)
    ok("canonical bytes are ascii-only (ensure_ascii=True)", all(b < 128 for b in cb))
    ok("canonical_json == canonical bytes decoded", canonical_json(pe) == cb.decode("utf-8"))
    # determinism: key order of input doesn't change the bytes
    ok("canonical is order-independent",
       canonical_provider_payload_bytes(pe) == canonical_provider_payload_bytes(dict(reversed(list(pe.items())))))

    # Ed25519 sign/verify round-trip + tamper-detection
    try:
        priv, pub = generate_keypair()
        sig = sign_payload(p, priv)
        ok("signature is ed25519:<hex>", sig.startswith("ed25519:") and len(sig) > 16)
        ok("verify_payload_signature accepts a good signature", verify_payload_signature(p, pub, sig) is True)
        tampered = dict(p); tampered["verification_summary"] = "TAMPERED"
        ok("verify rejects a tampered payload", verify_payload_signature(tampered, pub, sig) is False)
        attach_signature(p, priv)
        ok("attach_signature writes into metadata + re-verifies",
           p["metadata"]["provider_payload_signature"].startswith("ed25519:")
           and verify_payload_signature(p, pub) is True)
        # signing is INVARIANT to the signature key already living in metadata (kernel strips it before hashing)
        ok("signature stable under its own presence in metadata",
           sign_payload(p, priv) == sign_payload({k: v for k, v in p.items() if k != "metadata"}
                                                 | {"metadata": {kk: vv for kk, vv in p["metadata"].items()
                                                                 if kk != "provider_payload_signature"}}, priv))
    except Exception as exc:  # noqa: BLE001
        ok(f"Ed25519 signing round-trip (cryptography available): {exc!r}", False)

    # e2e adapter with a STUB battery (no Lean): faithful pass + laundered rejected ⇒ verified + signed + 3 refs
    def stub_battery(src, pred, cs):
        return "450" in src                                       # faithful (450≤) passes; laundered (449≤) fails
    priv2, pub2 = generate_keypair()
    ep = certify_demo_to_payload(
        rule_nl=_DEMO_RULE, faithful_src=_DEMO_FAITHFUL, predicate="adequate", cases=_DEMO_CASES,
        subject_ref="rule://basel/cet1", claim_ref="claim://basel/cet1-threshold",
        laundered_src=_DEMO_LAUNDERED, smt_boundary={"boundary": 449}, battery_fn=stub_battery,
        private_key_pem=priv2, run_id="demo_run")
    ok("e2e verdict verified (faithful pass + launder rejected)", ep["verdict"] == "verified")
    ok("e2e populates non-empty faithfulness_refs + checker_evidence_refs (trust-overlay requires)",
       bool(ep["faithfulness_refs"]) and bool(ep["checker_evidence_refs"]))
    ok("e2e payload is signed + verifies", verify_payload_signature(ep, pub2) is True)
    ok("e2e carries the matched-negative-control receipt",
       ep["metadata"]["anti_laundering"]["matched_negative_control"] == "rejected")
    # the laundering catch: if the laundered control is NOT rejected (admitted), the verdict must be invalid
    ep_bad = certify_demo_to_payload(
        rule_nl=_DEMO_RULE, faithful_src=_DEMO_FAITHFUL, predicate="adequate", cases=_DEMO_CASES,
        subject_ref="rule://basel/cet1", claim_ref="claim://basel/cet1-threshold",
        laundered_src=_DEMO_LAUNDERED, battery_fn=lambda s, p_, c: True)  # apparatus can't separate → both pass
    ok("e2e invalid when the matched-laundered control is ADMITTED (not rejected)", ep_bad["verdict"] == "invalid")
    ok("e2e admitted-control receipt", ep_bad["metadata"]["anti_laundering"]["matched_negative_control"] == "admitted")
    # the timeout seam: faithful PASSES but the laundered control TIMES OUT (None) ⇒ NOT invalid (None≠admitted);
    # the faithful battery's own boundary case already discriminated ⇒ verified + control marked inconclusive
    ep_to = certify_demo_to_payload(
        rule_nl=_DEMO_RULE, faithful_src=_DEMO_FAITHFUL, predicate="adequate", cases=_DEMO_CASES,
        subject_ref="rule://basel/cet1", claim_ref="claim://basel/cet1-threshold", laundered_src=_DEMO_LAUNDERED,
        battery_fn=lambda s, p_, c: (None if "449" in s else True))  # faithful True, laundered None (timeout)
    ok("e2e laundered-control TIMEOUT is not conflated with admitted (verdict verified, not invalid)",
       ep_to["verdict"] == "verified")
    ok("e2e timeout marks the control inconclusive",
       ep_to["metadata"]["anti_laundering"]["matched_negative_control"] == "inconclusive")
    # faithful itself TIMES OUT ⇒ inconclusive (checker couldn't decide)
    ep_ti = certify_demo_to_payload(
        rule_nl=_DEMO_RULE, faithful_src=_DEMO_FAITHFUL, predicate="adequate", cases=_DEMO_CASES,
        subject_ref="rule://basel/cet1", claim_ref="claim://basel/cet1-threshold",
        battery_fn=lambda s, p_, c: None)
    ok("e2e inconclusive when the faithful battery times out", ep_ti["verdict"] == "inconclusive")

    # PARITY CROSS-CHECK against cognitive-firm's OWN canonicalizer + signer, IF importable on this box (else
    # skip — the shipped selftest must pass standalone). This is the real positive control for signing parity.
    try:
        import importlib
        cf = importlib.import_module("cognitive_firm.orchestration.formal_verification")
    except Exception:  # noqa: BLE001
        print("  [SKIP] cognitive-firm parity cross-check (cognitive_firm not importable here)")
        cf = None
    if cf is not None:
        try:
            ours = canonical_provider_payload_bytes(ep)
            theirs = cf.canonical_provider_payload_bytes(ep)
            ok("PARITY: canonical bytes == cognitive-firm's canonical_provider_payload_bytes", ours == theirs)
            ok("PARITY: provider_payload_digest == cognitive-firm's", provider_payload_digest(ep) == cf.provider_payload_digest(ep))
            cf_sig = cf.sign_provider_payload(ep, private_key_pem=priv2)
            ok("PARITY: cognitive-firm verifies OUR signature",
               cf.verify_message_signature(theirs,
                                           cf._provider_signature_hex(ep["metadata"]["provider_payload_signature"]),
                                           pub2) is True)
            ok("PARITY: WE verify cognitive-firm's signature", verify_payload_signature(ep, pub2, cf_sig) is True)
        except Exception as exc:  # noqa: BLE001
            ok(f"PARITY cross-check raised: {exc!r}", False)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


def _main(argv: "list[str]") -> int:
    import argparse
    ap = argparse.ArgumentParser(description="LeanMill formal-verification provider adapter (v1 payload + Ed25519).")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    kg = sub.add_parser("keygen", help="generate an Ed25519 keypair (PEM)")
    kg.add_argument("--out-dir", help="write leanmill_provider.key / .pub here (else print to stdout)")
    em = sub.add_parser("emit-demo", help="run the Basel certify demo → signed v1 payload JSON")
    em.add_argument("--lean-root", help="Lean substrate dir (default ztare_proofs)")
    em.add_argument("--private-key-file", help="Ed25519 private PEM to sign with (else unsigned)")
    em.add_argument("--run-id")
    em.add_argument("--out", help="write the payload JSON here (else stdout)")
    em.add_argument("--audit-out", help="also write the legible markdown claim-audit here")
    au = sub.add_parser("audit", help="render the legible claim-audit from a provider payload JSON")
    au.add_argument("--payload-json", required=True, help="path to a formal-verification-provider/v1 payload")
    au.add_argument("--out", help="write the markdown audit here (else stdout)")
    a = ap.parse_args(argv)

    if a.cmd in (None, "selftest"):
        return _selftest()
    if a.cmd == "keygen":
        priv, pub = generate_keypair()
        if a.out_dir:
            from pathlib import Path
            d = Path(a.out_dir); d.mkdir(parents=True, exist_ok=True)
            (d / "leanmill_provider.key").write_text(priv, encoding="utf-8")
            (d / "leanmill_provider.pub").write_text(pub, encoding="utf-8")
            print(f"wrote {d/'leanmill_provider.key'} (SECRET) + {d/'leanmill_provider.pub'}")
        else:
            print(priv); print(pub)
        return 0
    if a.cmd == "emit-demo":
        priv = None
        if a.private_key_file:
            from pathlib import Path
            priv = Path(a.private_key_file).read_text(encoding="utf-8")
        payload = emit_demo_payload(lean_root=a.lean_root, private_key_pem=priv, run_id=a.run_id)
        js = to_transport_json(payload)
        if a.out:
            from pathlib import Path
            Path(a.out).write_text(js + "\n", encoding="utf-8")
            print(f"wrote {a.out} (verdict={payload['verdict']}, signed={'provider_payload_signature' in payload['metadata']})")
        else:
            print(js)
        if a.audit_out:
            from pathlib import Path
            Path(a.audit_out).write_text(render_audit(payload) + "\n", encoding="utf-8")
            print(f"wrote legible audit → {a.audit_out}")
        return 0
    if a.cmd == "audit":
        from pathlib import Path
        payload = json.loads(Path(a.payload_json).read_text(encoding="utf-8"))
        md = render_audit(payload)
        if a.out:
            Path(a.out).write_text(md + "\n", encoding="utf-8")
            print(f"wrote {a.out}")
        else:
            print(md)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
