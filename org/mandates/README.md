# org/mandates/

Role mandates are local/private operating-authority documents. They may contain
principal context, current research state, budget posture, and IP-sensitive
instructions, so real mandate files are gitignored.

Public templates live under `org/mandates/templates/`. To initialize a clean
checkout for local use:

```bash
python scripts/org_first_run_setup.py --init-private --skip-smoke
```

That command copies the templates into local ignored files such as
`org/mandates/manager_mandate.md` and
`org/mandates/research_director_mandate.md` if they do not already exist.
