import React from "react";
import { Target, FileText, FolderOpen, Settings, Zap, Gavel, ArrowRight } from "lucide-react";

const h = React.createElement;

// The four ways in. "Start from a claim" is primary — the workbench's core job.
const CHOICES = [
  { icon: Target, title: "Start from a claim", body: "State what you're arguing and what would change your mind.", action: "thesis", primary: true },
  { icon: FileText, title: "Start from files", body: "Upload notes, memos, or transcripts to build a claim from.", action: "files" },
  { icon: FolderOpen, title: "Open an existing folder", body: "Pick up a project you already have.", action: "browse" },
  { icon: Settings, title: "Set up models", body: "Choose the models used to run your analysis.", action: "settings" },
];

// The job the workbench does, as a journey — so a first-time user sees the value before choosing.
const JOURNEY = [
  { icon: Target, label: "State a claim", note: "what you're arguing" },
  { icon: FolderOpen, label: "Gather evidence", note: "the files that back it" },
  { icon: Zap, label: "Pressure-test it", note: "the loop attacks it" },
  { icon: Gavel, label: "Read the verdict", note: "can you rely on it?" },
];

// Day-0 onboarding — the JTBD afforded, stated plainly, then the ways in. Native + lucide; no Mantine.
export function DayZeroStartPanel({ liveMode, onCreateProject, onShowProjects, onOpenSettings }) {
  const run = (a) => {
    if (!liveMode) return;
    if (a === "browse") return onShowProjects && onShowProjects();
    if (a === "settings") return onOpenSettings && onOpenSettings();
    return onCreateProject && onCreateProject(a);
  };
  return h("div", { className: "start-screen" },
    h("div", { className: "start-hero" },
      h("div", { className: "start-head" },
        h("span", { className: "start-eyebrow" }, "New project"),
        h("h1", { className: "start-title" }, "What are you investigating?"),
        h("p", { className: "start-sub" },
          liveMode
            ? "The workbench turns a claim into a defensible verdict — state what you're arguing, gather the evidence, and let the loop pressure-test it."
            : "Start the local workbench server to create a project.")),

      // The JTBD journey — what happens here, end to end.
      h("div", { className: "start-journey" },
        JOURNEY.map((s, i) =>
          h(React.Fragment, { key: s.label },
            h("div", { className: "start-journey-step" },
              h("span", { className: "start-journey-icon" }, h(s.icon, { size: 19, strokeWidth: 1.9 })),
              h("strong", null, s.label),
              h("span", null, s.note)),
            i < JOURNEY.length - 1 ? h("span", { className: "start-journey-arrow" }, h(ArrowRight, { size: 16 })) : null))),

      // The ways in.
      h("div", { className: "start-choices" },
        CHOICES.map(({ icon: Icon, title, body, action, primary }) =>
          h("button", {
            key: action, type: "button", disabled: !liveMode,
            className: `start-choice ${primary ? "primary" : ""}`,
            onClick: () => run(action),
          },
            h("span", { className: "start-choice-icon" }, h(Icon, { size: 20, strokeWidth: 1.8 })),
            h("strong", null, title),
            h("span", { className: "start-choice-body" }, body))))));
}
