# analytics/public/dashboard/

The React + Vite analytics dashboard (trajectory, taste, reference
graph, P0, methodology). Operator-built only.

- `src/`, `index.html`, `vite.config.ts` - the app source.
- `scripts/safe-build.sh` - the **only** sanctioned build path
  (`npm run build` maps here). It public-scopes the reference graph,
  collapses private project paths, reuses the private `publish_mask`
  as the single sanitizer, strips `dist/` to one file, and runs a
  fail-closed leak assertion. `build:dev` is the raw, unsafe vite
  build for local dev only.
- `dist/`, `node_modules/` - **gitignored** build output / deps.

The dashboard remains operator-internal: a deploy is authorized only
after the safe-build passes and a human confirms the inlined narrative
is public-appropriate (the declared M3a prose residual).
