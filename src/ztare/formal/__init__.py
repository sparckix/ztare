"""Lean 4 integration — the proof-side bridge.

Persistent REPL wrapper (``lean_persistent``, ``lean_repl``), compiler
invocation (``lean_compiler``, ``lean_compiler_capture``), and
candidate-hygiene checks (``lean_candidate_hygiene``). Takes Python-side
intermediate lemmas (the compression result from the validator) and
verifies them under Lean's hard gate: typechecks or it didn't.

GP-122 / AlphaGeometry pattern: the topological oracle finds the
compression, the translator emits a Lean stub, this package fills the
proof via constrained LLM + Lean REPL.
"""
