// Row/label/slug + review-file helpers extracted from main.js (behavior-preserving).
// Pure helpers for labeling rows, slugging, naming downloads, and parsing review files.

import { displayText } from "../design-system.js";

export function itemLabel(rowOrLabel) {
  if (rowOrLabel && typeof rowOrLabel === "object" && rowOrLabel.display_label) return displayText(rowOrLabel.display_label);
  const label = typeof rowOrLabel === "string" ? rowOrLabel : (rowOrLabel && rowOrLabel.label) || "";
  return displayText(label || "project issue");
}

export function safeFilePart(value) {
  return String(value || "")
    .trim()
    .replace(/[^A-Za-z0-9_.-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80) || "project";
}

export function caseScopedDownloadName(snapshot, rowKey, suffix) {
  const project = safeFilePart((snapshot && snapshot.project) || "ztare");
  const intake = safeFilePart((snapshot && snapshot.intake) || "project");
  const item = safeFilePart(rowKey || "item");
  return `${project}_${intake}_${item}_${suffix}.json`;
}

export function rowSlug(label) {
  return String(label || "item").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "item";
}

export function parseReviewFile(value) {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}
