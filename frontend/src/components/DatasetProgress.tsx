"use client";

import { datasetStatusBadgeClass, stepLabel } from "@/lib/format";
import { useDatasetStatus } from "@/lib/useDatasetStatus";
import type { DatasetStatus } from "@/lib/types";

interface DatasetProgressProps {
  datasetId: string;
  initialStatus: DatasetStatus;
  initialProgressPct: number;
  initialCurrentStep: string | null;
  initialError?: string | null;
  /** Called once, right when status transitions into "complete" or "failed". */
  onSettled?: () => void;
}

export default function DatasetProgress({
  datasetId,
  initialStatus,
  initialProgressPct,
  initialCurrentStep,
  initialError = null,
  onSettled,
}: DatasetProgressProps) {
  const { status, progressPct, currentStep, error, isActive } = useDatasetStatus(
    datasetId,
    { status: initialStatus, progressPct: initialProgressPct, currentStep: initialCurrentStep, error: initialError },
    { onSettled }
  );

  return (
    <div>
      <span className={`badge ${datasetStatusBadgeClass(status)}`}>{status}</span>
      {isActive && (
        <div style={{ marginTop: "var(--space-xs)", minWidth: "140px" }}>
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${Math.min(100, Math.max(0, progressPct))}%`, transition: "width 0.4s ease" }}
            />
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
            {stepLabel(currentStep)} — {progressPct}%
          </div>
        </div>
      )}
      {status === "failed" && error && (
        <div style={{ fontSize: "11px", color: "var(--risk-high)", marginTop: "2px", maxWidth: "220px" }}>
          {error}
        </div>
      )}
    </div>
  );
}
