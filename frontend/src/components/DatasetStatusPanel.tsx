"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { getExportUrl } from "@/lib/api";
import { stepLabel } from "@/lib/format";
import { useDatasetStatus } from "@/lib/useDatasetStatus";
import type { Dataset } from "@/lib/types";

interface DatasetStatusPanelProps {
  dataset: Dataset;
}

export default function DatasetStatusPanel({ dataset }: DatasetStatusPanelProps) {
  const router = useRouter();
  const { status, progressPct, currentStep, error, isActive } = useDatasetStatus(
    dataset.id,
    {
      status: dataset.status,
      progressPct: dataset.progress_pct,
      currentStep: dataset.current_step,
      error: dataset.error,
    },
    { onSettled: () => router.refresh() }
  );

  const isComplete = status === "complete";

  return (
    <>
      {!isComplete && (
        <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
          {status === "failed" ? (
            <p style={{ color: "var(--risk-high)" }}>Analysis failed{error ? `: ${error}` : "."}</p>
          ) : (
            <>
              <p style={{ color: "var(--text-secondary)", marginBottom: "var(--space-sm)" }}>
                Analysis in progress ({stepLabel(currentStep)}) — {progressPct}% complete. Profile, stats, and
                findings will appear here automatically once it finishes.
              </p>
              {isActive && (
                <div className="progress-bar-track">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${Math.min(100, Math.max(0, progressPct))}%`, transition: "width 0.4s ease" }}
                  />
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Actions: Query + Download */}
      <div className="card" style={{ marginBottom: "var(--space-xl)", padding: "var(--space-lg)" }}>
        <div style={{ display: "flex", gap: "var(--space-md)", flexWrap: "wrap" }}>
          <Link href={`/datasets/${dataset.id}/query`}>
            <button className="btn btn-primary" disabled={!isComplete}>
              Query This Dataset (SQL)
            </button>
          </Link>
          {isComplete && (
            <>
              <a href={getExportUrl(dataset.id, "xlsx")}>
                <button className="btn btn-secondary">Download XLSX</button>
              </a>
              <a href={getExportUrl(dataset.id, "csv")}>
                <button className="btn btn-secondary">Download CSV</button>
              </a>
            </>
          )}
        </div>
      </div>
    </>
  );
}
