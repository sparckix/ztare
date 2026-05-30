"""GP-241 pre-tick obligation compiler.

Goal text → deterministic feature extraction → catalog activation
clauses (DNF) → sparse mandatory tick contract. No fuzzy scores, no
embeddings, no LLM in the obligation derivation; the catalog is a
small set of self-describing items, the activation is mechanical.

Commit gate recomputes from goal-hash + catalog-hash and requires
either a typed witness or a structured ``why_not``. Abstention is
first-class — flooding the tick with obligations is itself a membrane
failure. Shares philosophy with ``ztare.orchestrator.mutator_briefing``
(deterministic, no-priors, tiered, persisted composition) but the
semantics differ: this emits a binding contract; the briefing emits
advisory text.
"""
