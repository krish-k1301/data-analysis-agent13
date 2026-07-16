import type { DatasetStatus, FindingStatus, Severity } from "./types";

export function severityBadgeClass(severity: Severity | string): string {
  return `badge-${severity.toLowerCase()}`;
}

const FINDING_STATUS_BADGE: Record<FindingStatus, string> = {
  PENDING: "badge-pending",
  CONFIRMED: "badge-accepted",
  DISMISSED: "badge-rejected",
};

export function findingStatusBadgeClass(status: FindingStatus | string): string {
  return FINDING_STATUS_BADGE[status as FindingStatus] ?? "badge-pending";
}

const FINDING_STATUS_LABEL: Record<FindingStatus, string> = {
  PENDING: "Pending",
  CONFIRMED: "Confirmed",
  DISMISSED: "Dismissed",
};

export function findingStatusLabel(status: FindingStatus | string): string {
  return FINDING_STATUS_LABEL[status as FindingStatus] ?? status;
}

const DATASET_STATUS_BADGE: Record<DatasetStatus, string> = {
  queued: "badge-pending",
  running: "badge-pending",
  complete: "badge-accepted",
  failed: "badge-rejected",
};

export function datasetStatusBadgeClass(status: DatasetStatus | string): string {
  return DATASET_STATUS_BADGE[status as DatasetStatus] ?? "badge-pending";
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    dateStyle: "medium",
    timeStyle: "medium",
  });
}

export function formatNumber(n: number): string {
  return n.toLocaleString();
}

// Mirrors NODE_PROGRESS keys in backend/app/workflow/graph.py.
const STEP_LABELS: Record<string, string> = {
  ingest: "Reading file",
  clean: "Cleaning data",
  profile: "Profiling columns",
  schema_fit: "Mapping schema",
  validate_schema: "Validating data",
  audit_rules: "Running audit rules",
  statistics: "Computing statistics",
  risk_score: "Scoring risk",
  explain: "Generating explanations",
  persist: "Saving results",
};

export function stepLabel(step: string | null | undefined): string {
  if (!step) return "Queued";
  return STEP_LABELS[step] ?? step;
}
