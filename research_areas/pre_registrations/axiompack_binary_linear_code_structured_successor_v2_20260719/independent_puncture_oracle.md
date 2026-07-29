# Independent puncture-family oracle

This post-freeze referee checks the construction family independently of the
campaign authors. It does not add evidence to their context.

Source artifact: the frozen `[51,20,14]` generator in
`../axiompack_binary_linear_code_frontier_v1_20260717/binary_code_control_replay.json`,
artifact SHA-256
`213c591c8870333c54944c011f15e035ee1baa56ab451897ace39bc671588d4e`.

## Exact calculation

The oracle enumerates all `2^20 - 1 = 1,048,575` nonzero messages once in
Gray-code order. It finds minimum distance 14, 1,595 minimum-weight words, and
minimum-support union `0x7ffffffffffff`, covering every one of the 51
coordinates.

For a puncture at coordinate `j`,

`wt(puncture_j(c)) = wt(c) - c_j`.

Thus a minimum word containing `j` gives punctured distance at most 13, while
puncturing can lower distance by at most one, giving distance at least 13.
Coverage of every coordinate by a minimum word therefore proves exact distance
13 for all 51 punctures. Direct GF(2) elimination gives rank 20 for each member.

Result: all 51 coordinate punctures are `[50,20,13]`; this family contains no
`[50,20,14]` witness. This is only a family-level exclusion and says nothing
about global existence.

Replay:

`PYTHONPATH=src ./venv/bin/python research_areas/pre_registrations/axiompack_binary_linear_code_structured_successor_v2_20260719/puncture_family_oracle.py`

Full receipt digest from the first replay:
`70637b3ef321d1c8d9b81a0b6326afe7a61c3848f953656bb94444fce58c8a63`.
