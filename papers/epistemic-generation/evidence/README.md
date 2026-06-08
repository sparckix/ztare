# Evidence Packet

This directory contains the minimal public evidence packet for the headline
numbers in the epistemic-generation manuscript.

Run from the repository root:

```sh
./venv/bin/python papers/epistemic-generation/evidence/reproducers/verify_gp216_claims.py
```

The verifier checks the saved GP-216 and GP-218 artifacts used for the paper's
reported cross-corpus split, negative control, compression result, eight-subfield
catalogue, out-of-domain extensions, and PDE adversarial rescore.

This is intentionally narrower than the private workingpaper evidence directory.
It excludes old exploratory logs, hidden audit keys, and private path metadata.
The full project provenance map is maintained in the private root workspace at
`epistemic-generation/research_log.md`; this public packet carries only the
saved artifacts needed to verify the manuscript's headline numbers.
