---
id: ANTI-PATTERN-001
name: citation_laundering
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: ["§X.Y Lemma Z.W", "OP Z.W", "Theorem N, p. K", "per [Author Year-of-textbook]", "private communication"]
  structural:
    - decimal_sub_label_disagrees_with_chapter
    - textbook_cited_for_result_originating_in_journal_paper
    - paywalled_paper_with_page_precise_label_no_open_access_mirror
    - citation_used_load_bearing_in_docstring_or_proof
  problem_classes: [apparatus_self_audit, hard_mathematical_residual]
detection_protocol:
  primary: PATTERN-002  # darwin_idea_killer cross-checks docstring claims
  secondary: PATTERN-009  # independent_cas_verification (citation as "external" leg)
  rule:
    - "When a docstring cites '[Author Year] §X.Y Lemma Z.W' for a result whose primary source is a journal paper, verify the textbook TOC against the cited indices."
    - "When the chapter numeral X disagrees with the inner numeral Z (e.g. §X.9 OP 9.3 while the actual item is X.9.4), hand-verify against TOC or third-party citing paper."
    - "When the cited paper is paywalled with no open-access mirror, distinguish (i) bibliographic, (ii) subject-match, (iii) primary-PDF page verification — mark partial when only (i)+(ii) achievable."
mitigation:
  - "Substitute the verifiable primary source (e.g. Lions 1996 Vol 1 §IV.4 → Lions 1984 CCNL Part 1 Lemma I.1 p. 115)."
  - "If only secondary-corroborated, soften the page-level qualifier or add '(per secondary literature; primary PDF not accessed)'."
  - "If unverifiable AND load-bearing, REMOVE the citation and re-derive or downgrade the dependent claim."
  - "Cascade scan: when one citation in a wall/atom is laundered, audit ALL siblings that share the same author/textbook framing (catch #28 cascade rule)."
examples:
  - id: catch_17
    summary: "Marchioro-Pulvirenti fabrication — citation could not be confirmed; substituted with explicit Kolmogorov-flow construction."
  - id: catch_27
    summary: "Lions 1996 Vol 1 §IV.4 Lemma 4.4 (tightness trichotomy) — book has 4 chapters; Ch. IV is Euler not NS. Substituted Lions 1984 CCNL Part 1 Lemma I.1 p. 115."
    file: lions_tightness_lemma_verification_2026_05_08.md
  - id: catch_28
    summary: "Galdi 2011 §X.9 'OP 9.3' — sub-label not found in any citing paper; actual item is Remark X.9.4 p. 729. Cosmetic but inheritance-prone."
    file: UCC_wall_citation_cascade_audit_2026_05_08.md
  - id: catch_29
    summary: "DiPerna-Majda 1987 CMP 108:667-689 Theorem 1 p. 671 — venue + subject verified by 6 independent secondary sources; page-precise label could not be primary-verified (paywalled, no arXiv). Recorded as verification-confidence-gap, NOT misattribution."
    file: diperna_majda_lemma_verification_2026_05_08.md
falsifiable_test:
  description: "Open the cited textbook's TOC (or third-party citing paper) and locate the cited sub-label. If the sub-label does not appear OR the chapter index contradicts the result class (e.g. cited section is Euler but the result is NS), the anti-pattern is firing."
  binary_check: "TOC_index_lookup(cited_label) ∈ {found_at_chapter_matching_subject, not_found, found_but_subject_mismatch}; firing iff result ∈ {not_found, subject_mismatch}."
  not_trivial: "Returns 'not firing' (False) when the citation is verified on first lookup; this is observed in 10/11 UCC citations (catch #28 audit). Therefore the test is NOT True := by trivial."
chain_position: post  # runs AFTER any docstring or proof claim citing literature
references:
  - "lions_tightness_lemma_verification_2026_05_08.md"
  - "UCC_wall_citation_cascade_audit_2026_05_08.md"
  - "diperna_majda_lemma_verification_2026_05_08.md"
  - "AGENTS.md §6c (citation hygiene)"
---

# ANTI-PATTERN-001 — Citation Laundering

## What it is

A load-bearing literature citation in a docstring, axiom comment, or
proof that does not actually point at the cited result. Three sub-modes
observed tonight:

1. **Misattribution** (catch #27): cited textbook chapter does not
   contain the result; the result lives in the author's earlier
   journal paper.
2. **Sub-label mismatch** (catch #28): chapter is correct, section is
   correct, but the inner numeric label (e.g. "OP 9.3" vs the actual
   "Remark X.9.4") is a lazy decimal reformat.
3. **Verification-confidence gap** (catch #29): paper, venue, subject
   all verified, but the page-precise theorem label cannot be
   primary-verified because the source is paywalled with no
   open-access mirror.
4. **Fabrication** (catch #17): citation cannot be confirmed against
   any source.

## Why it appears

LLMs generating docstrings reach for plausible-sounding section
numerals when they remember the author + theorem class but not the
exact label. The sub-label often gets reformatted (e.g. "X.9.4" →
"OP 9.3") or transposed across editions.

## Why it matters

A misattributed citation in a Lean axiom docstring propagates: every
downstream file that inherits the framing inherits the broken
provenance. Catch #28 cascade audit found 10/11 UCC wall citations
verified — but the 1 misattribution was structural-bookkeeping, not
mathematical content. The danger is reviewer trust collapse on
discovery, not (in this case) mathematical wrongness.

## Detection protocol

Apply PATTERN-002 (DARWIN-IDEA-KILLER) with citation-verification
sub-mode:

1. For each citation in the file's docstrings + axiom comments:
   - Look up the textbook TOC (publisher page, Google Books preview,
     third-party citing paper).
   - Confirm chapter X exists.
   - Confirm section X.Y exists and is on the claimed subject.
   - Confirm the inner label Z.W exists at the claimed page.
2. If any step fails: substitute, soften, or remove.
3. Cascade rule: when a catch demotes one docstring, scan all sibling
   files that copy-pasted the same framing.

## Mitigation when detected

- **Misattribution**: substitute primary source.
- **Sub-label mismatch**: correct the decimal.
- **Verification gap**: add "(per secondary literature)" qualifier.
- **Fabrication**: REMOVE the citation; re-derive or downgrade the
  dependent claim.

## Falsifiable test (catalog-level)

`TOC_index_lookup(cited_label)` ∈ {found_matching, not_found,
subject_mismatch}. The anti-pattern fires iff result is `not_found`
or `subject_mismatch`.

This test is NOT trivially True — empirically 10/11 UCC citations
returned `found_matching` and the catalog declares those
NOT-firing. The test discriminates.

## Cross-references

- PATTERN-002 (`org/patterns/darwin_idea_killer.md`) — primary detector
- PATTERN-009 (`org/patterns/independent_cas_verification.md`) — citation
  as one independent leg of three
- AGENTS.md §6c — citation hygiene (current single-line rule)
- `projects/ns_millennium_hunt/workspace/research_notes/UCC_wall_citation_cascade_audit_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/lions_tightness_lemma_verification_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/diperna_majda_lemma_verification_2026_05_08.md`
