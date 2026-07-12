# AxiomPack GP-251 — attempt 3 durable continuation amendment

Recorded 2026-07-10 after attempt 3 stopped at nine navigator calls and before
any continuation.

The ninth action previewed the singleton `x = x*((x*y)*x)`. The deterministic
v2 receipt removes its substitution instance `x = x*((x*x)*x)` and retains
`x = x*(x*x)` with `0.67665929` residual identification bits. The run stopped
before the leaf could freeze or reject because the phase allocator reserved an
expansion agent slice even though this campaign freezes
`adapter_forge_attempts: 0`.

The continuation may change only the generic allocation rule: under
`roll_forward_protected_future`, agent resources assigned to AdapterForge are
reachable by navigation when the frozen hard cap makes AdapterForge impossible.
Boundary and interpretation allocations remain protected; total provider calls,
agent turns, wall time, model, effort, context, and all other scientific inputs
remain unchanged.

Resume the same immutable attempt from its nine digest-checked call results.
The host must reconstruct every workbench receipt without provider dispatch;
the next provider call is index 9. Success requires the leaf to explicitly
freeze or reject the positive-residual preview. Any repeated provider call,
changed context, changed prior result digest, or boundary execution before an
explicit freeze kills the continuation.
