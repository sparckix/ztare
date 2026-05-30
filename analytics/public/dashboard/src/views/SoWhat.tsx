import type { DashboardData } from "../lib/data";

// The "so what" — authored in-flight by the agent doing the weekly update,
// rendered above each chart so the takeaway is impossible to miss.
export function SoWhat({ data, k }: { data: DashboardData; k: string }) {
  const p = data.graphSowhat?.panels?.[k];
  if (!p?.headline) return null;
  const trend = p.trend || "flat";
  return (
    <div className={`sowhat sowhat-${trend}`}>
      <span className="sowhat-tag">So what</span>
      <span className="sowhat-text">{p.headline}</span>
      {p.detail && <span className="sowhat-detail">{p.detail}</span>}
    </div>
  );
}
