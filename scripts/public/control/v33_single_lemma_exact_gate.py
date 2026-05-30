"""Backward-compat shim. Canonical location: src/ztare/gates/v33_single_lemma_exact_gate.py.

Kept here so existing importers (route_c_layer_2c_dispatch.py,
ztareproofs_auto_prover_packet.py, gp225_audit.py, leanmill_proof_audit.py,
etc.) continue to work without per-file rewrites. New code should import
directly from ztare.gates.v33_single_lemma_exact_gate.
"""
from __future__ import annotations
import sys
from pathlib import Path
_repo = Path(__file__).resolve().parents[3]
if str(_repo / "src") not in sys.path:
    sys.path.insert(0, str(_repo / "src"))
from ztare.gates.v33_single_lemma_exact_gate import *  # noqa: F401,F403,E402
