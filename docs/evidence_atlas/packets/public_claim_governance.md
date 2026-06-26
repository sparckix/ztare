---
description: "Review packet for ZTARE public claim governance: claim register, project summaries, non-claims, and next falsifiers."
---
# Public claim governance packet

> **Up:** [Review Packets](README.md)

## Scoped claim

ZTARE has a public claim-governance layer that separates scoped claims,
evidence pointers, non-claims, retest tags, demotions, and next falsifiers
across multiple project families.

## Evidence level

L3 as governance infrastructure. Individual project claims vary from L1 to L4.

## Primary sources

- [Public claim register](../../public_claim_register.md)
- [Packet coverage](../packet_coverage.md)
- [Claim cards](../claim_cards.md)
- [Experiment track record](../../../research_areas/EXPERIMENT_TRACK_RECORD.md)
- Per-project `projects/*/public/CLAIM_SUMMARY.md`

## Runnable anchor

```bash
find projects -path '*/public/CLAIM_SUMMARY.md' | sort
```

Current count observed by the atlas audit: 38 public project summaries.

## Evidence summary

The public claim register is the canonical prose surface for public campaign
status. Per-project summaries provide local claim surfaces, and the experiment
track record adds the broader provenance layer. Reading all three makes it
possible to tell whether a project is claiming a positive result, a null, a
demotion, a source-blocked state, or a next falsifier.

## Non-claims

- A public summary is not external replication.
- A large number of summaries is not evidence that every project is strong.
- Some project claims remain system-internal, original-run-only, partial,
  or explicitly demoted.
- The current summaries are not yet normalized into a machine-readable schema.

## Missing upgrade

The current packet checker validates curated claim cards for the minimum public
fields. The next upgrade is broader: normalize project `public/CLAIM_SUMMARY.md`
files or add sidecar rows so the checker can fail if any public project claim
lacks:

- scoped claim
- evidence level or status
- evidence pointer
- non-claim
- next falsifier
- path that exists in the checkout

This belongs in docs/tooling and can validate project summaries in place. It
does not require creating a new `projects/` experiment.
