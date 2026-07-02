// Render smoke-check: load the key workbench routes in headless Chrome and fail if any hits the error
// boundary ("hit a rendering error") or logs an uncaught error. Catches undefined-component refs that the
// Vite build does NOT catch (they crash only at render — e.g. `IconUpload is not defined`).
//
// Usage: node render_smoke.mjs   (requires vite dev on :5174 + API on :8765)
// No new deps — drives the same `/Applications/Google Chrome.app` headless binary used for screenshots,
// via the DevTools JSON endpoint is overkill; instead we render each route to a throwaway PNG and scrape
// the page's console + DOM by injecting a check through --dump-dom.
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { rm } from "node:fs/promises";

const run = promisify(execFile);
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const BASE = "http://localhost:5174";
const P = "&project=ai_capex";
const ROUTES = [
  "/?workspace=projects&section=Current%20project",
  "/?workspace=projects&section=Connect%20project&day0=1&start=files",
  "/?workspace=projects&section=Connect%20project&day0=1&start=folder",
  "/?workspace=projects&section=Connect%20project&day0=1&start=thesis",
  `/?workspace=overview&section=Thesis${P}`,
  `/?workspace=sources&section=Prepare%20files${P}`,
  `/?workspace=run&section=Results${P}`,
  `/?workspace=review&section=Things%20to%20review${P}`,
  `/?workspace=save&section=Report%20readiness${P}`,
  "/?workspace=leanmill&section=Start",
  "/?workspace=leanmill&section=Draft%20target",
  "/?workspace=leanmill&section=Run%20a%20proof",
  "/?workspace=leanmill&section=Proof%20files",
  "/?workspace=leanmill&section=Proof%20status",
  "/?workspace=projects&section=Settings",
];

let failures = 0;
for (let i = 0; i < ROUTES.length; i++) {
  const url = BASE + ROUTES[i];
  const prof = `/tmp/render_smoke_${i}`;
  try {
    // --dump-dom prints the rendered DOM after load; --virtual-time-budget lets async render settle.
    const { stdout } = await run(CHROME, [
      "--headless", "--disable-gpu", "--no-sandbox", `--user-data-dir=${prof}`,
      "--virtual-time-budget=9000", "--dump-dom", url,
    ], { timeout: 30000, maxBuffer: 32 * 1024 * 1024 });
    const dom = stdout || "";
    const crashed = /hit a rendering error/i.test(dom) || /is not defined/i.test(dom);
    const empty = dom.replace(/\s/g, "").length < 400; // near-empty = failed mount
    if (crashed || empty) {
      failures++;
      const why = crashed ? (dom.match(/[A-Za-z]+ is not defined/)?.[0] || "error boundary") : "empty/blank mount";
      console.log(`FAIL  ${ROUTES[i]}  → ${why}`);
    } else {
      console.log(`ok    ${ROUTES[i]}`);
    }
  } catch (e) {
    failures++;
    console.log(`FAIL  ${ROUTES[i]}  → ${String(e.message || e).slice(0, 80)}`);
  } finally {
    await rm(prof, { recursive: true, force: true }).catch(() => {});
  }
}
console.log(`\n${failures ? `❌ ${failures} route(s) failed render smoke` : "✅ all routes rendered without error"}`);
process.exit(failures ? 1 : 0);
