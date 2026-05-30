# org/mandates/

Role mandates are local/private operating-authority documents. They may contain
principal context, current research state, budget posture, and IP-sensitive
instructions, so real mandate files are gitignored.

Public templates live under `org/mandates/templates/`. To initialize a clean
checkout for local use:

```bash
python scripts/public/control/org_first_run_setup.py --init-private --skip-smoke
```

That command copies the templates into local ignored files such as
`org/mandates/manager_mandate.md` and
`org/mandates/research_director_mandate.md` if they do not already exist.

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Sub-folders**

- [`templates/`](templates/) - 2 file(s)

**Documents**

- [Manager-Agent Mandate](manager_mandate.md)
- [Product Manager Mandate (v1.0, 2026-05-06)](product_manager_mandate.md)

<sub>1 sub-folder(s), 2 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
