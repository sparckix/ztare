"""Deterministic sidecar that checks LLM auditor outputs against the target
document.

Catches confabulation-dressed-as-grounding: quoted lines that do not
appear in the target, mechanisms paired with the wrong location, claim
ranges that overrun the file. Knows nothing about semantics — pure
structural checks (quote locality, rule-3 profile).

Used by the validator's auditor-output gates; never invoked from
research-side reasoning code.
"""
