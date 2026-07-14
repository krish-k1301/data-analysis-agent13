import { useEffect, useRef, useState } from "react";
import { getDatasetStatus } from "@/lib/api";
import type { DatasetStatus } from "@/lib/types";

const POLL_INTERVAL_MS = 1500;

interface InitialJobState {
  status: DatasetStatus;
  progressPct: number;
  currentStep: string | null;
  error?: string | null;
}

interface UseDatasetStatusOptions {
  /** Called once, right when status transitions into "complete" or "failed". */
  onSettled?: () => void;
}

/** Polls /jobs/{id}/status while a dataset's analysis pipeline is queued/running. */
export function useDatasetStatus(
  datasetId: string,
  initial: InitialJobState,
  { onSettled }: UseDatasetStatusOptions = {}
) {
  const [status, setStatus] = useState(initial.status);
  const [progressPct, setProgressPct] = useState(initial.progressPct);
  const [currentStep, setCurrentStep] = useState(initial.currentStep);
  const [error, setError] = useState(initial.error ?? null);
  const onSettledRef = useRef(onSettled);
  onSettledRef.current = onSettled;

  const isActive = status === "queued" || status === "running";

  useEffect(() => {
    if (!isActive) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const job = await getDatasetStatus(datasetId);
        if (cancelled) return;
        setStatus(job.status);
        setProgressPct(job.progress_pct);
        setCurrentStep(job.current_step);
        setError(job.error);
        if (job.status === "complete" || job.status === "failed") {
          onSettledRef.current?.();
        }
      } catch {
        // Transient fetch failure — keep polling, don't surface as fatal.
      }
    };

    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [datasetId, isActive]);

  return { status, progressPct, currentStep, error, isActive };
}
