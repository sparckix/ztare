# org/preferences/

Preference files encode local principal taste, attention routing, budget
comfort, and decision thresholds. Real preference files are gitignored because
they are personal and operationally sensitive.

Public templates live under `org/preferences/templates/`. To initialize a clean
checkout for local use:

```bash
python scripts/public/control/org_first_run_setup.py --init-private --skip-smoke
```

That command copies `org/preferences/templates/principal.yaml` to the local
ignored file `org/preferences/principal.yaml` if it does not already exist.

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Sub-folders**

- [`templates/`](templates/) - 1 file(s)

**Documents**

- [principal.yaml](principal.yaml)

<sub>1 sub-folder(s), 1 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
