# Auxiliary Historical Suite

This suite holds **additional historical candidates** mined from real project history but kept separate from the frozen main benchmark.

Purpose:
- evaluate promising historical cases without silently changing the `N=9` main suite
- inspect whether they are genuinely distinct exploit families or just near-duplicates
- decide case-by-case whether any belong in a future benchmark expansion

Generate or refresh the suite with:

```bash
python benchmarks/constraint_memory/mine_auxiliary_historical.py
```

Run it with:

```bash
python benchmarks/constraint_memory/run_benchmark.py --judge-model gemini --suite auxiliary_historical --adjudicator-model gemini
```

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Sub-folders**

- [`ai_inference_internal_price_floor/`](ai_inference_internal_price_floor/) - 6 file(s)
- [`central_station_hypothetical_target_laundering/`](central_station_hypothetical_target_laundering/) - 6 file(s)
- [`central_station_mirrored_monte_carlo/`](central_station_mirrored_monte_carlo/) - 6 file(s)

**Documents**

- [index.json](index.json)

<sub>3 sub-folder(s), 1 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
