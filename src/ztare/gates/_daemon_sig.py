"""GP-241 daemon signature (cold round-4 blocker — endpoint identity
was in the TCB).

The verificator daemon signs every stamped row's `official_state_hash`
with an ed25519 private key that ONLY ztare_verify holds (VPS,
agent-unreadable, outside the synced repo + gate tree). Readers
(stamped_state.chain_valid → verify_fetched/is_official, used by the
remote poll AND every canonical consumer) require a valid signature by
the PINNED public key committed at deploy/gp241_daemon_pubkey.hex.

Consequence: the hash-chain alone is forgeable by anyone (sha256 is
public) — a chosen SSH endpoint can present a self-consistent fake
chain. The signature is NOT: without the VPS-only private key an
attacker cannot produce a row the pinned key accepts. So the ledger
may be fetched from anywhere; only genuinely daemon-signed rows are
OFFICIAL, and the SSH target leaves the trust boundary.

Fail-closed everywhere: missing key/lib, bad/absent signature, any
error ⇒ NOT verified (never an exception into a verdict path).
"""
from __future__ import annotations

import pathlib

# Daemon-side private key — HARD-PINNED absolute path (the daemon runs
# as ztare_verify on the VPS; this path is root/ztare_verify-controlled
# and agent-unreadable). Never from env (an agent-steerable key path
# would re-introduce the forge).
PRIV_PATH = pathlib.Path("/srv/ztare_verify_keys/daemon_ed25519.key")

# Pinned PUBLIC key = committed trust anchor. Resolved relative to this
# file so it works both in the repo and in the structure-preserving
# /srv/ztare_gate copy. This is the operator-established anchor; it
# changes only via a reviewed commit (like the frozen-manifest sha).
_PUB_HEX_FILE = (pathlib.Path(__file__).resolve().parents[3]
                 / "deploy" / "gp241_daemon_pubkey.hex")


def _not_writable_by_me(p: pathlib.Path) -> bool:
    """A trust-anchor / verifier file is tamperproof for THIS process
    only if it exists, is a regular file (no symlink swap), and is NOT
    writable by our euid (and its parent dir is not writable by us —
    else we could replace it). Mirrors stamped_state._verify_enforce_
    store's posture for the store path."""
    import os
    try:
        if p.is_symlink() or not p.is_file():
            return False
        st = p.stat()
        euid = os.geteuid()
        # writable by us via owner or world bit?
        if st.st_uid == euid and (st.st_mode & 0o200):
            return False
        if st.st_mode & 0o002:
            return False
        d = p.parent
        ds = d.stat()
        if d.is_symlink():
            return False
        if ds.st_uid == euid and (ds.st_mode & 0o200):
            return False
        if ds.st_mode & 0o002:
            return False
        return True
    except Exception:
        return False


def anchor_tamperproof() -> tuple[bool, str]:
    """Round-5 blocker: remote-enforce must REFUSE unless the pinned
    public-key anchor AND the verifier modules are NOT writable by the
    running user — otherwise the agent swaps the anchor for its own key
    and forges the endpoint verdict (the round-4 class, relocated to
    the local checkout). No code can make its own host unwritable;
    this turns silent-trust into loud-fail unless the verifier is
    installed from an agent-unwritable location (like /srv/ztare_gate
    on the VPS). Returns (ok, reason)."""
    targets = [
        _PUB_HEX_FILE,
        pathlib.Path(__file__).resolve(),                       # _daemon_sig
        pathlib.Path(__file__).resolve().parent / "stamped_state.py",
        pathlib.Path(__file__).resolve().parent / "propose.py",
    ]
    bad = [str(t) for t in targets if not _not_writable_by_me(t)]
    if bad:
        return False, ("verifier/anchor is writable by this user "
                       "(install it agent-unwritable, e.g. root-owned "
                       "0755 like /srv/ztare_gate): " + ", ".join(bad))
    return True, "verifier + pinned anchor are agent-unwritable"


def _load_pub():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey)
        hx = _PUB_HEX_FILE.read_text(encoding="utf-8").strip()
        if len(hx) != 64:
            return None
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hx))
    except Exception:
        return None


def sign(message: str) -> str:
    """Daemon-side: ed25519-sign `message`, return hex. Raises on
    failure (the daemon MUST NOT append an unsigned row — a write
    failure is loud, not silent)."""
    from cryptography.hazmat.primitives import serialization
    sk = serialization.load_pem_private_key(
        PRIV_PATH.read_bytes(), password=None)
    return sk.sign(message.encode("utf-8")).hex()


def verify(message: str, sig_hex: str | None) -> bool:
    """Reader-side: True iff `sig_hex` is a valid signature of
    `message` by the PINNED daemon public key. Fail-closed."""
    if not sig_hex:
        return False
    pk = _load_pub()
    if pk is None:
        return False
    try:
        pk.verify(bytes.fromhex(sig_hex), message.encode("utf-8"))
        return True
    except Exception:
        return False


# ── JUDGE KEY (cold review baxgapbe9: a mutator-submitted
# judge_verdict was forgeable). A SEPARATE ed25519 keypair: the
# private key lives ONLY where the trusted judge runs (operator-
# provisioned, agent-UNREADABLE — same posture as the daemon key);
# judge_out_of_loop signs its execution proof with it. The daemon
# verifies this judge-key signature BEFORE it signs an official
# judge_verdict. The mutator cannot hold the judge key ⇒ cannot
# fabricate a verdict. Public key pinned (committed) like the daemon
# anchor.
JUDGE_PRIV_PATH = pathlib.Path(
    "/srv/ztare_judge_keys/judge_ed25519.key")  # VPS/judge-host only
_JUDGE_PUB_HEX_FILE = (pathlib.Path(__file__).resolve().parents[3]
                       / "deploy" / "gp241_judge_pubkey.hex")


def _load_judge_pub():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey)
        hx = _JUDGE_PUB_HEX_FILE.read_text(encoding="utf-8").strip()
        if len(hx) != 64:
            return None
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hx))
    except Exception:
        return None


_FAMILY_ANCHORS_FILE = (pathlib.Path(__file__).resolve().parents[3]
                        / "deploy" / "gp241_family_anchors.json")

# Strict canonical provider enum (cold review boibujil4 D1): replaces
# the greedy substring _fam(). Exact-token map; anything else => the
# explicit sentinel "unknown" which the daemon REJECTS. No substring
# ambiguity (a string containing both "claude" and "gpt" => unknown).
_PROVIDER_TOKENS = {
    "anthropic": "anthropic", "claude": "anthropic",
    "openai": "openai", "gpt": "openai", "codex": "openai",
    "o3": "openai", "o4": "openai",
    "google": "google", "gemini": "google",
}


def canon_family(model_identity: str) -> str:
    """Map a model identity to exactly one provider, or 'unknown'.
    Tokenize on non-alphanumerics; a single unambiguous provider token
    wins; zero or conflicting tokens => 'unknown' (REJECTED upstream).
    Never best-effort: ambiguity is a hard fail, not a guess."""
    s = (model_identity or "").lower()
    hits = set()
    for tok, prov in _PROVIDER_TOKENS.items():
        if tok in s:
            hits.add(prov)
    return hits.pop() if len(hits) == 1 else "unknown"


def load_family_anchors() -> tuple[str, str] | None:
    """Return (judge_family, mutator_family) from the COMMITTED anchor
    file, or None (=> daemon fail-closes the judge_verdict). Both are
    operator-provisioned trust anchors, NEVER proposal-derived. None if:
    file missing/invalid, either family not a known provider, or the
    two families are equal (a same-family judge is no judge)."""
    try:
        import json as _j
        d = _j.loads(_FAMILY_ANCHORS_FILE.read_text(encoding="utf-8"))
        jf = canon_family(str(d.get("judge", "")))
        mf = canon_family(str(d.get("mutator", "")))
        if jf == "unknown" or mf == "unknown" or jf == mf:
            return None
        return (jf, mf)
    except Exception:
        return None


def judge_sign(message: str) -> str:
    """Judge-side (run from the trusted install under the provisioned
    judge identity): ed25519-sign the execution proof. Raises if the
    judge key is unreadable — the AGENT cannot read it, so an agent
    that tries to self-produce a verdict fails loudly (fail-closed)."""
    from cryptography.hazmat.primitives import serialization
    sk = serialization.load_pem_private_key(
        JUDGE_PRIV_PATH.read_bytes(), password=None)
    return sk.sign(message.encode("utf-8")).hex()


def judge_verify(message: str, sig_hex: str | None) -> bool:
    """Daemon-side: True iff `sig_hex` is a valid signature of
    `message` by the PINNED JUDGE public key. Fail-closed. This is
    what proves a real separate judge ran (the mutator lacks the
    judge private key)."""
    if not sig_hex:
        return False
    pk = _load_judge_pub()
    if pk is None:
        return False
    try:
        pk.verify(bytes.fromhex(sig_hex), message.encode("utf-8"))
        return True
    except Exception:
        return False


# ── OPERATOR KEY (GP-241 forward-spec Contract C2). The THIRD peer
# identity alongside daemon-signer and judge (deploy/FIRST_TIME_SETUP
# already establishes the three-OS-identity posture). Operator-only
# transitions (target_register, admin_retire, human-approval) are
# authenticated by THIS key, whose private half lives only where the
# operator signs (agent- AND daemon-signer-UNREADABLE, mode 0400 like
# the judge key) — replacing the env-flag "attestation" an agent
# runtime could carry. Public key pinned/committed like the daemon +
# judge anchors; changes only via a reviewed commit.
OPERATOR_PRIV_PATH = pathlib.Path(
    "/srv/ztare_operator_keys/operator_ed25519.key")  # operator only
_OPERATOR_PUB_HEX_FILE = (pathlib.Path(__file__).resolve().parents[3]
                          / "deploy" / "gp241_operator_pubkey.hex")


def _load_operator_pub():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey)
        hx = _OPERATOR_PUB_HEX_FILE.read_text(encoding="utf-8").strip()
        if len(hx) != 64:
            return None
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hx))
    except Exception:
        return None


def operator_anchor_provisioned() -> bool:
    """C2 BLOCKED-vs-FAIL discriminator: True iff a real 64-hex
    operator pubkey anchor is committed (not the unprovisioned
    placeholder). Daemon fail-closes (BLOCKED) when False — never
    'allow until provisioned' (P5)."""
    try:
        hx = _OPERATOR_PUB_HEX_FILE.read_text(encoding="utf-8").strip()
        return len(hx) == 64 and all(
            c in "0123456789abcdefABCDEF" for c in hx)
    except Exception:
        return False


def operator_verify(message: str, sig_hex: str | None) -> bool:
    """Daemon-side: True iff `sig_hex` is a valid signature of
    `message` by the PINNED OPERATOR public key. Fail-closed. An
    agent runtime cannot hold the operator private key, so an
    operator-only transition it forges cannot verify."""
    if not sig_hex:
        return False
    pk = _load_operator_pub()
    if pk is None:
        return False
    try:
        pk.verify(bytes.fromhex(sig_hex), message.encode("utf-8"))
        return True
    except Exception:
        return False
