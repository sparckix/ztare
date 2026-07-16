const QUIESCENT_STATUS = /(?:complete|completed|frozen|verified|retired|stopped|blocked|unreadable|no_candidate|warm_route_required)/i;

export function campaignIsLive(status) {
  if (!status) return false;
  const lease = status.attempt_lease || {};
  const run = status.run || {};
  const state = String(status.status || run.status || "");
  // A stale lease file cannot make a finalized or waiting campaign active again.
  if (QUIESCENT_STATUS.test(state)) return false;
  return Boolean(lease.active) || run.status === "running" || state === "running";
}
