#!/usr/bin/env python3
"""GP-241 OPERATOR signing key — generate-if-absent + emit public key.

Forward-spec Contract C2: operator-only transitions (`target_register`,
`admin_retire`, human-approval) were "operator-attested" by an env
flag the AGENT runtime could carry — forgeable. FIX: a SEPARATE
ed25519 keypair. The PRIVATE key lives ONLY on the VPS, owned by a
dedicated `ztare_operator` identity, AGENT- AND DAEMON-SIGNER-
UNREADABLE (same posture as the judge key). The operator signs the
canonical payload offline with it; the daemon verifies that
OPERATOR-KEY signature against the pinned PUBLIC anchor
(`deploy/gp241_operator_pubkey.hex`) before accepting the transition.
The agent lacks the operator private key ⇒ cannot self-register a
target. Generator written by the agent is SAFE because the security
property is the deploy-time identity/ACL separation + the pinned-
anchor hard-verify + the not-the-builder kill-test — exactly as for
the judge key (gen_judge_key.py).

Idempotent: generates ONLY if absent (persist across deploys; rotation
= explicit operator act that also re-pins the public anchor). Run
ONCE on the VPS as the provisioned `ztare_operator` identity (NOT the
agent user, NOT ztare_verify). Prints `PUBKEY_HEX=<64 hex>` — the
OPERATOR pins it into deploy/gp241_operator_pubkey.hex (until then C2
fail-closes, which is safe: closure-claim ticks blocked).

Usage: gen_operator_key.py [/srv/ztare_operator_keys/operator_ed25519.key]
"""
import os
import pathlib
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey)

kp = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                   else "/srv/ztare_operator_keys/operator_ed25519.key")

if kp.exists():
    sk = serialization.load_pem_private_key(kp.read_bytes(), password=None)
else:
    sk = Ed25519PrivateKey.generate()
    pem = sk.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption())
    kp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(kp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        os.write(fd, pem)
    finally:
        os.close(fd)

pub = sk.public_key().public_bytes(
    serialization.Encoding.Raw, serialization.PublicFormat.Raw)
print("PUBKEY_HEX=" + pub.hex())
