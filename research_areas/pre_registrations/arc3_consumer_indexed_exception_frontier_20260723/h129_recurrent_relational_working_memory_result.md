# H129 result — active memory now re-binds and learns from contact

Status: **passed within the preregistered offline boundary**.

The H127 source memory remained unchanged while H129 compiled a distinct
working revision for each current H128 observation. On the successful frozen
treatment path, the ten revisions selected all ten oracle actions. At the two
failed H128 first-divergence states, the current revision selected the oracle
counterfactual: up instead of an extra right before contact, and right instead
of an extra up after contact.

The lifecycle also corrected a deeper assumption. Before contact, the source
relation projected the left-bearing target from `(27,36)` to `(27,30)`. After
the controlled token entered the target node, the successor contained no
target entity. The system emitted exactly one
`target_transport_refuted` settlement and retained the source relation only as
source evidence. It then constructed a different
`ztare-settled-residual-working-revision` identity for the final three
navigation actions. Active target authority cannot be revived in that phase.

All 14 checks passed: exact predecessor chain, unique current revisions,
stable source memory, `10/10` action selection, both failed-path corrections,
single target settlement, active-to-residual type transition, stale-scope
refusal, post-settlement refusal, palette covariance, D4 covariance, and an
oracle-literal firewall.

This makes the candidate loop executable:

```text
source invariant
  -> exact-current-state action
  -> observed successor
  -> applicability prediction error
  -> next revision identity
```

The result uses frozen trajectories. It shows the lifecycle can express and
correct H128's failure, but it does not yet show that injecting current-state
revisions changes fresh controller behavior. The next test holds initial
memory, primitive budget, model, sessions, and refresh cost fixed, varying only
current-state versus stale refresh content.

Evidence:

- `h129_recurrent_relational_working_memory_result.json`
  (`9b44881450716c38a69fdad31d422a28783d8abf59d00dfd493e21c2b53714e2`)
- `h129_recurrent_relational_working_memory_audit.py`
- `src/ztare/worldmodel/relational_affordance.py`
- `src/ztare/worldmodel/relational_affordance_recall.py`
- `tests/test_relational_affordance.py`
