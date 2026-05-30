# analytics/public/dashboard/scripts/

Build + data-staging scripts for the dashboard.

- `safe-build.sh` - the ONLY sanctioned publish build (`npm run build`
  maps here). Public-scopes the reference graph, collapses private
  project paths, reuses the private `publish_mask` as the single
  sanitizer, strips `dist/` to one file, runs a fail-closed leak
  assertion. `build:dev` is the raw unsafe vite build for local dev.
- `refresh-data.sh` - stages the pipeline JSON into `src/data/` +
  `public/data/` before a build (the private taste primer is
  deliberately not staged).
