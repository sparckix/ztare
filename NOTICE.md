ZTARE — Zero-Trust Adversarial Reasoning Engine
Copyright 2026 Daniel Alami

This product includes software developed by Daniel Alami.

Licensed under the MIT License (the "License"); you may not use this
file except in compliance with the License. A copy of the License is
available in the top-level `LICENSE` file.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

------------------------------------------------------------------------

This product depends on or builds against the following open-source
projects. Their licenses apply to the corresponding code paths.

- **Mathlib4** (Apache-2.0) — formal mathematics library used in the
  Lean theorem-proving substrate (`ZtareProofs/`).
- **Lean 4** (Apache-2.0) — proof assistant runtime.
- **scipy, numpy, pandas, matplotlib** (BSD-3-Clause / similar) —
  numerical and analytical machinery underlying the
  substrate-mutator-judge loop.
- **PyTorch** (BSD-style) — neural-scaling and related substrates.
- **Streamlit** (Apache-2.0) — executive-inbox dashboard.
- **mpmath, SymPy, Z3** (BSD / MIT) — symbolic and arbitrary-precision
  verification used by selected substrates.

------------------------------------------------------------------------

This product references the following public datasets and corpora as
substrate inputs. Dataset licenses apply to their respective uses.

- **OLMo2 7B / 13B / 1B production training-loss telemetry** (AllenAI,
  ODC-By). Used as the neural-scaling substrate. Public W&B logs.
- **OEIS** — used for the dark-sequence law-recovery substrate.
- **arXiv preprints** cited per-substrate in the project workspaces.
- **SPARC / public galaxy rotation-curve datasets** — used for the
  modified-gravity substrate.

------------------------------------------------------------------------

This product was developed in collaboration with large language model
agents acting as research workers under the operator's
adversarial-falsification discipline. Agent authorship is documented
per-artifact in commit history, the catch ledger
(`analytics/catch_ledger.jsonl`), and the kill log
(`docs/sprint_60day_journey.md` §6.2). Model versions used during
development are captured in iteration metadata, not redistributed.

LLM agents include releases from Anthropic (Claude family), OpenAI
(GPT family), and Google (Gemini family). Their roles and the
operator's role are kept structurally separate per the discipline
documented in `docs/concepts/epistemic_principles.md`.

------------------------------------------------------------------------

Theoretical grounding for the apparatus draws on:

- Hofstadter, Douglas R. (1979). *Gödel, Escher, Bach: An Eternal
  Golden Braid*. Basic Books. — strange-loop framing for recursive
  self-demotion (P18).
- Hofstadter, Douglas R. (2007). *I Am a Strange Loop*. Basic Books.
- Dennett, Daniel C. (1995). *Darwin's Dangerous Idea*. Simon &
  Schuster. — META-DARWIN protocol.
- Munger, Charles T. (compiled). *Poor Charlie's Almanack*. — inversion
  discipline (P3, P9), lollapalooza, circle of competence.
- Goodhart, Charles A. E. (1975). "Problems of Monetary Management:
  the U.K. Experience." — Goodhart's Law (P1, P16).

These works are cited; no text is reproduced.

------------------------------------------------------------------------

Mentions of DeepMind Co-Mathematician, OpenAI, Anthropic, Google, and
other organizations in this repository are research-context references.
No endorsement or affiliation is implied. Trademarks belong to their
respective holders.

------------------------------------------------------------------------

This repository documents claims that the apparatus produced and then
refuted under its own subsequent audit. Demotions are preserved in the
same artifacts as the original claims, per the self-demotion discipline
(P17, `docs/concepts/epistemic_principles.md`). Readers who encounter a
claim that looks central should check the catch ledger and kill
log before citing.

For methodological objections or to contribute a catch, see
[CONTRIBUTING.md](CONTRIBUTING.md).
