"""Role extensions — per-role Python modules loaded by org/ agent runtimes.

Each role in org/roles/ has a corresponding extension module here that
implements the role's procedural duties as callable functions. The
extensions are NOT imported by autoresearch_loop or any other apparatus
code path; they are loaded ONLY by the role's runtime (today: a Claude
Code session; in future: an org-OS daemon process).

This separation preserves the apparatus / role boundary:
  - apparatus = substrate-agnostic ZTARE loop that runs on any project
  - role extensions = per-role logic (Research Director triangulation,
    Skeptic adversarial probes, Inverter forms, etc.)
  - mandates (org/roles/<role>.md) = the role's config / procedural rules
  - rubrics (rubrics/<project>.json) = per-substrate data the role reads

Naming convention: one module per role, named after the role
(`research_director.py`, `principal.py`, `skeptic.py`, ...). Each module
exposes a small public API: load(), run(trigger, context) — so the
future daemon framework can wire them in uniformly.
"""
