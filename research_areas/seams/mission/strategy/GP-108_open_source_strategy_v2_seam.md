# GP-108 — Open Source Strategy v2

> **Seam metadata** · `seam_id:` GP-108 · `track:` mission · `status:` closed · `last_updated:` 2026-04-30


**Status:** closed  
**Opened:** 2026-04-21  
**Closed:** 2026-04-30 23:20:00  
**Visibility:** public; release-decision seam, no sealed experiment details.

## Context

This seam revisited the repository's open-source strategy after the engine had
gained stronger compression, validation, and proof-adjacent machinery. The
question was not whether the work should ever be public; the repo was already
public. The question was what should be pushed, what should remain private
while active, and what release discipline should govern future pushes.

## Decision

The principal rejected a long secrecy window. The operating decision is:

```text
Ship the scientific instrument and public documentation aggressively, but do
not dump active strategy seams, sealed pre-registrations, personal context, or
first-mover-sensitive product tactics.
```

The durable rule is the same one now encoded in `AGENTS.md`:

- closed and safe artifacts promote public;
- open/testing/active artifacts stay private;
- sealed GT, private principal context, and in-flight pre-registrations stay
  private until closure;
- stable principles can be rendered into public derivatives without exposing
  raw active strategy.

## Panel Summary

The debate considered three broad options:

| Option | Upside | Risk |
|---|---|---|
| Full open | Maximizes reproducibility, adoption, and timestamped priority | Competitors can scale the apparatus faster |
| Partial open | Preserves more commercial control | Black-box verification undermines trust |
| Staged open | Balances priority and stabilization | Can become indefinite delay by another name |

The pre-mortem compared two failure modes:

- **Open too early:** a larger lab forks the tool, scales it, and captures much
  of the external credit.
- **Hold too long:** the work remains unseen, unreplicated, and irrelevant
  while weaker public tools become the de facto standard.

The principal judged the second failure mode worse. If the tool matters but
someone else scales it, the work still changed the field. If the tool stays
private and unused, it did not.

## Release Rule

Public release is not the same as public dumping.

### Public by default once stable

- MIT-licensed scientific engine code;
- validators, gates, fit primitives, compression tools, and public docs;
- closed seams that pass the visibility rule;
- papers and reproducibility artifacts with calibrated claims;
- public derivatives of private philosophy/product seams.

### Private until closure or derivative rendering

- active seams;
- sealed pre-registrations and GT-sensitive derivations;
- private principal context;
- in-flight science tactics;
- product or governance-kernel strategy whose value depends on being first;
- credentials, contact channels, and personal planning.

## Closure

This seam is closed as a release-governance decision. Ongoing work now lives in:

- `priority_roadmap.md` for current product priorities;
- `research_areas/ZTARE_BOARD.md` for execution board state;
- `MIRROR.md` for private-to-public derivative discipline;
- `research_areas/seams/README.md` and `AGENTS.md` for file-cabinet rules.
