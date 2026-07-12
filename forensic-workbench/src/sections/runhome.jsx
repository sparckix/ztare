import React from "react";

const h = React.createElement;

// Pressure-test is one workflow with a long post-run reading surface. The rail preserves that single home
// while giving the operator a stable way to move between its real sections.
export function RunHome({ console, findings, panels, anchors }) {
  const rail = (anchors || []).filter(Boolean);
  return h("section", { className: "run-home", "aria-label": "Pressure-test" },
    h("div", { className: "run-home-body" },
      h("div", { className: "run-home-main" },
        h("div", { id: "run-console" }, console),
        findings,
        panels || null),
      rail.length > 1
        ? h("nav", { className: "run-home-rail", "aria-label": "On this page" },
            h("span", { className: "eyebrow" }, "On this page"),
            rail.map((anchor) => h("a", { key: anchor.id, href: `#${anchor.id}` }, anchor.label)))
        : null));
}
