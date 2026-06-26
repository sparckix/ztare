# The limits of audit for self-evaluating AI

Public source for the paper *The limits of audit for self-evaluating AI: authority, correlated error, and the price of judgement*.

The structural fix for a self-evaluating system, separate the producer from the judge and place a non-gameable check outside the loop, leaves two problems the audit analogy cannot reach. The first is authority: when a deterministic check cannot settle whether a surviving deviation is fraud, error, discovery, or dissent, governing it is first a question of who may settle the dispute, and only afterward of measurement. The second is mechanical: a machine monitor can fail by sharing a training lineage with the system it checks, wrong in the same places for the same reasons, a correlation human audit answers with rotation but shared weights tighten. The paper argues for a standing, repriced price on capture and correlation kept in open contest.

Files: `draft.md` (canonical text), `main.tex` / `main.pdf` (pdflatex build), `refs.bib`.
