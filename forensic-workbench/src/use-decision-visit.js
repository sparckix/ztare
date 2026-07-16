import React from "react";

const KEY_PREFIX = "ztare.workbench.decision.last-seen.";

function decisionState(decision) {
  return (decision && decision.result && decision.result.decision_state) || null;
}

function snapshot(state) {
  if (!state || !state.fingerprint) return null;
  return {
    fingerprint: state.fingerprint,
    status: state.status || "",
    headline: state.headline || "",
    next_test: state.next_test && state.next_test.text ? state.next_test.text : "",
  };
}

export function decisionVisitDelta(prior, current) {
  if (!prior || !current || !prior.fingerprint || prior.fingerprint === current.fingerprint) return null;
  const statusChanged = String(prior.status || "") !== String(current.status || "");
  const testChanged = String(prior.next_test || "") !== String((current.next_test && current.next_test.text) || "");
  return {
    statusChanged,
    testChanged,
    label: statusChanged
      ? `Standing changed from ${prior.status || "unrecorded"} to ${current.status || "unrecorded"}`
      : testChanged
        ? "The next decisive test changed"
        : "The decision's supporting structure changed",
  };
}

export function useDecisionVisit(project, decision) {
  const current = decisionState(decision);
  const [prior, setPrior] = React.useState(null);

  React.useEffect(() => {
    if (!project) { setPrior(null); return; }
    try {
      const raw = window.localStorage.getItem(`${KEY_PREFIX}${encodeURIComponent(project)}`);
      setPrior(raw ? JSON.parse(raw) : null);
    } catch { setPrior(null); }
  }, [project]);

  React.useEffect(() => {
    const currentSnapshot = snapshot(current);
    if (!project || !currentSnapshot) return undefined;
    const remember = () => {
      try { window.localStorage.setItem(`${KEY_PREFIX}${encodeURIComponent(project)}`, JSON.stringify(currentSnapshot)); }
      catch { /* The comparison remains optional when browser storage is unavailable. */ }
    };
    window.addEventListener("pagehide", remember);
    return () => window.removeEventListener("pagehide", remember);
  }, [project, current && current.fingerprint, current && current.status, current && current.headline,
    current && current.next_test && current.next_test.text]);

  return decisionVisitDelta(prior, current);
}
