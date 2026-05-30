#!/usr/bin/env python3
"""GP-241 JUDGE signing key — generate-if-absent + emit public key.

Cold review baxgapbe9 (STILL-GAMEABLE): a mutator-submitted
`judge_verdict` proved daemon stamping, NOT a real separate judge run
(judge_identity was a self-declared proposal string). FIX: a SEPARATE
ed25519 keypair. The PRIVATE key lives ONLY on the judge host, owned
by the provisioned judge identity and AGENT-UNREADABLE (same posture
as the daemon key). `judge_out_of_loop.py`, run from the agent-
unwritable trusted install under that identity, signs the execution
proof with it. The daemon verifies that JUDGE-KEY signature (pinned
PUBLIC key, committed deploy/gp241_judge_pubkey.hex) BEFORE it signs an
official judge_verdict. The mutator lacks the judge private key ⇒
cannot fabricate a verdict.

Idempotent: generates ONLY if absent (persist across deploys; rotation
= explicit operator act that also re-commits the public anchor). Run
ONCE on the judge host as the provisioned judge identity (NOT the
agent user). Prints `PUBKEY_HEX=<64 hex>` — commit it to
deploy/gp241_judge_pubkey.hex (the pinned anchor; until then judge
verification fail-closes, which is safe — substantive ticks blocked).

Usage: gen_judge_key.py [/srv/ztare_judge_keys/judge_ed25519.key]
"""
import os
import pathlib
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey)

kp = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                   else "/srv/ztare_judge_keys/judge_ed25519.key")

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
