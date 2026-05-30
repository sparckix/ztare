#!/usr/bin/env python3
"""operator_sign — the OPERATOR's offline signing tool (C2/C4).

Run ONLY as the provisioned `ztare_operator` identity, on the host
where the operator key lives. It reads the operator private key (mode
0400, owned by ztare_operator, agent- and daemon-signer-UNREADABLE)
and emits the ed25519 hex signature over EXACTLY the message argument.
The agent cannot run this usefully: it cannot read the key file, so
under the correct OS topology the call fails for the agent identity
(that failure IS the boundary — verified by C4's not-the-builder
triad check, not by this script).

Written by an agent is SAFE for the same reason gen_operator_key.py /
gen_judge_key.py are: the security property is the deploy-time
identity + ACL separation, not authorship of the signer. This script
holds no secret; it only invokes the key the OS has already fenced.

Usage (as ztare_operator):
  deploy/operator_sign.py '<exact canonical payload string>'
    e.g. C4 retire:  '<owner>|<tick_row>|<reason>|<ts>'
    e.g. C2 target:  '<statement_sha256>|<label>|<env_hash>'
Prints: SIG_HEX=<hex>   (paste into --operator-sig)
"""
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization

KEY = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
    "/srv/ztare_operator_keys/operator_ed25519.key")

if len(sys.argv) < 2 or not sys.argv[1]:
    print("usage: operator_sign.py '<exact payload>' [keypath]",
          file=sys.stderr)
    raise SystemExit(2)

msg = sys.argv[1]
try:
    sk = serialization.load_pem_private_key(
        KEY.read_bytes(), password=None)
except Exception as e:  # agent identity hits this (cannot read key)
    print(f"REFUSED: cannot load operator key {KEY} ({type(e).__name__}). "
          f"If you are the agent, this is the boundary working — you "
          f"are not the operator identity. If you ARE the operator, "
          f"run as the ztare_operator user on the key host.",
          file=sys.stderr)
    raise SystemExit(2)

print("SIG_HEX=" + sk.sign(msg.encode("utf-8")).hex())
