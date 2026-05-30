import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The "so what" — authored in-flight by the agent doing the weekly update,
// rendered above each chart so the takeaway is impossible to miss.
export function SoWhat({ data, k }) {
    const p = data.graphSowhat?.panels?.[k];
    if (!p?.headline)
        return null;
    const trend = p.trend || "flat";
    return (_jsxs("div", { className: `sowhat sowhat-${trend}`, children: [_jsx("span", { className: "sowhat-tag", children: "So what" }), _jsx("span", { className: "sowhat-text", children: p.headline }), p.detail && _jsx("span", { className: "sowhat-detail", children: p.detail })] }));
}
