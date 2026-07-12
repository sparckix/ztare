"""The ONE backing-tier vocabulary (Fable eigenreview: it was triplicated across belief_ledger / rice /
argument_kernel). A backing tier says HOW CHECKABLE a piece of support is — the moat's core axis. Warrant CODES
(W0..W3) are the wire format; PLAIN names (proven / reproducible / cited / unchecked) are the only thing a human
ever sees. Hardest -> flimsiest. This module has NO ZTARE deps, so anything may import it without a cycle."""
from __future__ import annotations

# code -> checkability rank (higher = harder to fake); a conclusion is never more trusted than the weakest
# warrant on a load-bearing support edge (the "no untyped trust" invariant).
WARRANT_RANK = {"W0": 3, "W1": 2, "W2": 1, "W3": 0}
WARRANT_LABEL = {
    "W0": "kernel certificate (formal proof, e.g. LeanMill)",
    "W1": "re-executable computation (recomputes from bound raw data; gp-ansatz / fit)",
    "W2": "verbatim quote binding (normalized-equal to bound source text)",
    "W3": "proposed-unchecked (LLM-proposed edge, admitted but marked)",
}
TIER_NAME = {"W0": "proven", "W1": "reproducible", "W2": "cited", "W3": "unchecked"}  # code -> plain (human)
PROFILE_TIER = ("proven", "reproducible", "cited", "unchecked")  # strength-profile index 0..3, hardest->flimsiest
TIER_RANK = {"proven": 3, "reproducible": 2, "cited": 1, "unchecked": 0}  # plain name -> rank
