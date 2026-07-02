import React from "react";

// Native + design-system shims for the subset of the Mantine API LeanMill uses, so LeanMill speaks the
// same visual language as the rest of the workbench (the .chip button system, hairlines, one type scale)
// instead of Mantine's. Swapped in for `@mantine/core` — the 823 lines of LeanMill JSX are unchanged.
const h = React.createElement;

const SP = { none: 0, xs: 6, sm: 10, md: 16, lg: 24, xl: 32 };
const RAD = { xs: 6, sm: 8, md: 12, lg: 16 };
// Map the shim's t-shirt sizes onto the workbench type-scale tokens (not raw px) so LeanMill shares the
// exact rhythm of the redesigned sections. sm/xs/md land within 1px of the old values (low risk).
const FZ = { xs: "var(--fs-label)", sm: "var(--fs-meta)", md: "var(--fs-body)", lg: "var(--fs-subhead)", xl: "var(--fs-title)" };
const sp = (v) => (typeof v === "number" ? v : (SP[v] != null ? SP[v] : 0));
const rad = (v) => (typeof v === "number" ? v : (RAD[v] != null ? RAD[v] : 8));

// Pull Mantine spacing margin props into a style object.
function mstyle(p) {
  const s = {};
  if (p.mt != null) s.marginTop = sp(p.mt);
  if (p.mb != null) s.marginBottom = sp(p.mb);
  if (p.ml != null) s.marginLeft = sp(p.ml);
  if (p.mr != null) s.marginRight = sp(p.mr);
  if (p.my != null) { s.marginTop = sp(p.my); s.marginBottom = sp(p.my); }
  if (p.m != null) s.margin = sp(p.m);
  if (p.w != null) s.width = typeof p.w === "number" ? p.w : p.w;
  if (p.h != null) s.height = typeof p.h === "number" ? p.h : p.h;  // so h="100%" fills the card → space-between bottom-aligns buttons
  return s;
}

export function Box({ children, className, style, ...p }) {
  return h("div", { className, style: { ...mstyle(p), ...style } }, children);
}

export function Group({ children, justify, align = "center", wrap, gap = "sm", className, style, ...p }) {
  return h("div", {
    className: className ? `lm-group ${className}` : "lm-group",
    style: {
      display: "flex", flexDirection: "row", alignItems: align,
      justifyContent: justify || "flex-start",
      flexWrap: wrap === "nowrap" ? "nowrap" : "wrap",
      gap: sp(gap), ...mstyle(p), ...style,
    },
  }, children);
}

export function Stack({ children, gap = "md", align, className, style, ...p }) {
  return h("div", {
    className, style: { display: "flex", flexDirection: "column", gap: sp(gap), alignItems: align || undefined, ...mstyle(p), ...style },
  }, children);
}

export function SimpleGrid({ children, cols = 1, spacing = "md", className, style, ...p }) {
  // Desktop-first: take the `sm` breakpoint count (or a plain number).
  const n = typeof cols === "object" && cols ? (cols.sm || cols.base || 1) : (cols || 1);
  return h("div", {
    className, style: { display: "grid", gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))`, gap: sp(spacing), ...mstyle(p), ...style },
  }, children);
}

export function Button({ children, variant, onClick, disabled, leftSection, fullWidth, type = "button", size, className, component, href, title, ...p }) {
  // no variant → primary (filled); "default" → outline chip; "light"/"subtle" → ghost.
  const tier = variant === "light" || variant === "subtle" ? "chip ghost" : variant === "default" || variant === "outline" ? "chip" : "chip primary";
  const cls = [tier, fullWidth ? "lm-btn-full" : "", className || ""].filter(Boolean).join(" ");
  const inner = [leftSection ? h("span", { key: "ls", className: "lm-btn-icon" }, leftSection) : null, children];
  if (component === "a" || href) {
    return h("a", { className: cls, href, onClick, title, style: mstyle(p) }, inner);
  }
  return h("button", { type, className: cls, onClick, disabled, title, style: mstyle(p) }, inner);
}

function Field({ label, description, error, children, ...p }) {
  return h("label", { className: "lm-field", style: mstyle(p) },
    label ? h("span", { className: "lm-field-label" }, label) : null,
    children,
    description ? h("span", { className: "lm-field-desc" }, description) : null,
    error ? h("span", { className: "lm-field-error" }, error) : null);
}

export function TextInput({ label, description, error, value, onChange, placeholder, disabled, type = "text", className, ...p }) {
  return h(Field, { label, description, error, ...p },
    h("input", { className: `lm-input ${className || ""}`, type, value: value == null ? "" : value, onChange, placeholder, disabled }));
}

export function Textarea({ label, description, error, value, onChange, placeholder, disabled, minRows = 3, autosize, className, ...p }) {
  return h(Field, { label, description, error, ...p },
    h("textarea", { className: `lm-input lm-textarea ${className || ""}`, value: value == null ? "" : value, onChange, placeholder, disabled, rows: minRows }));
}

export function NativeSelect({ label, description, value, onChange, data, disabled, className, ...p }) {
  const opts = (Array.isArray(data) ? data : []).map((d, i) => {
    const o = typeof d === "string" ? { value: d, label: d } : d;
    return h("option", { key: i, value: o.value }, o.label != null ? o.label : o.value);
  });
  return h(Field, { label, description, ...p },
    h("select", { className: `lm-input lm-select ${className || ""}`, value: value == null ? "" : value, onChange, disabled }, opts));
}

// Paper/Card → a calm hairline container (no Mantine shadow); shadow="none" honored.
export function Paper({ children, withBorder, p, radius = "md", shadow, className, style, ...rest }) {
  return h("div", {
    className: className ? `lm-paper ${className}` : "lm-paper",
    style: {
      border: withBorder !== false ? "1px solid var(--line)" : "none",
      borderRadius: rad(radius), padding: p != null ? sp(p) : 16,
      background: "var(--surface)", ...mstyle(rest), ...style,
    },
  }, children);
}
export const Card = Paper;

export function Text({ children, c, fw, fz, size, tt, span, ta, className, style, title, ...p }) {
  const st = { ...mstyle(p), ...style };
  if (c === "dimmed") st.color = "var(--muted)"; else if (c) st.color = c;
  if (fw != null) st.fontWeight = fw;
  const f = fz || size;
  if (f != null) st.fontSize = typeof f === "number" ? f : (FZ[f] || "var(--fs-body)");
  if (tt) st.textTransform = tt;
  if (tt === "uppercase") st.letterSpacing = "0.04em";
  if (ta) st.textAlign = ta;
  return h(span ? "span" : "p", { className: className ? `lm-text ${className}` : "lm-text", style: st, title }, children);
}

export function Title({ children, order = 2, className, style, ...p }) {
  return h(`h${order}`, { className: className ? `lm-title ${className}` : "lm-title", style: { ...mstyle(p), ...style } }, children);
}

// Emit the canonical design-system tag (`ds-tag`) so LeanMill badges are pixel-identical to ZTARE's,
// not a bespoke bordered pill. Map Mantine colors onto the ds-tag tone set (accent/ok/warn/danger).
const BADGE_TONE = { teal: "ok", green: "ok", blue: "accent", grape: "accent", violet: "accent", indigo: "accent", red: "danger", orange: "warn", yellow: "warn", gray: "" };
export function Badge({ children, color, variant, size, className, leftSection, style, ...p }) {
  const tone = BADGE_TONE[color] != null ? BADGE_TONE[color] : "";
  return h("span", { className: `ds-tag ${tone} ${className || ""}`.trim(), style: { ...mstyle(p), ...style } },
    leftSection ? h("span", { className: "lm-badge-icon" }, leftSection) : null, children);
}

export function Code({ children, className, block, style }) {
  return h("code", { className: `lm-code ${block ? "lm-code-block" : ""} ${className || ""}`.trim(), style }, children);
}

export function Divider({ label, my, className, style, ...p }) {
  if (label) return h("div", { className: "lm-divider-labeled", style: { ...mstyle({ my, ...p }), ...style } }, h("span", null, label));
  return h("hr", { className: className ? `lm-divider ${className}` : "lm-divider", style: { ...mstyle({ my, ...p }), ...style } });
}

export function Anchor({ children, href, onClick, className, target, ...p }) {
  if (onClick && !href) return h("button", { type: "button", className: `text-link ${className || ""}`.trim(), onClick, style: mstyle(p) }, children);
  return h("a", { href, onClick, target, className: `text-link ${className || ""}`.trim(), style: mstyle(p) }, children);
}

export function Alert({ children, title, color, icon, variant, className, style, ...p }) {
  const tone = BADGE_TONE[color] != null ? BADGE_TONE[color] : "";
  return h("div", { className: `lm-alert ${tone} ${className || ""}`.trim(), style: { ...mstyle(p), ...style } },
    icon ? h("span", { className: "lm-alert-icon" }, icon) : null,
    h("div", { className: "lm-alert-body" },
      title ? h("strong", { className: "lm-alert-title" }, title) : null,
      h("div", null, children)));
}

// Accordion → native <details>. Compound API: Accordion / .Item / .Control / .Panel.
export function Accordion({ children }) { return h("div", { className: "lm-accordion" }, children); }
function AccordionItem({ children, value }) { return h("details", { className: "lm-acc", "data-value": value }, children); }
function AccordionControl({ children }) { return h("summary", { className: "lm-acc-control" }, children); }
function AccordionPanel({ children }) { return h("div", { className: "lm-acc-panel" }, children); }
Accordion.Item = AccordionItem;
Accordion.Control = AccordionControl;
Accordion.Panel = AccordionPanel;
