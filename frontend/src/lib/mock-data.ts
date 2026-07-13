// ============================================
// MOCK DATA — Audit Dashboard
// All data hardcoded for standalone frontend
// Replace with API calls when backend is ready
// ============================================

export interface Dataset {
  id: string;
  name: string;
  filename: string;
  rowCount: number;
  columnCount: number;
  uploadDate: string;
  status: "uploaded" | "profiled" | "analyzed" | "reviewed" | "complete";
  fileSize: string;
  analysis_summary?: {
    executive_summary?: string;
    key_risks?: string[];
    findings_by_severity?: {
      HIGH?: number;
      MEDIUM?: number;
      LOW?: number;
    };
    fraud_assessment?: {
      assessment?: string;
      skipped?: boolean;
    };
    supervisor_plan?: Record<string, unknown>;
  };
}

export interface ColumnProfile {
  name: string;
  dataType: string;
  nullCount: number;
  nullPercent: number;
  uniqueCount: number;
  min: string;
  max: string;
  mean: string;
}

export interface Finding {
  id: string;
  datasetId: string;
  datasetName: string;
  rule: string;
  severity: "high" | "medium" | "low";
  amount: number;
  vendor: string;
  status: "pending" | "accepted" | "rejected";
  riskScore: number;
  dateFlagged: string;
  description: string;
  evidence: Record<string, string>;
  explanation: string;
  reviewerNotes: string;
}

export interface ActivityItem {
  id: string;
  timestamp: string;
  action: string;
  dataset: string;
  status: string;
}

// --- DATASETS ---

export const datasets: Dataset[] = [];

// --- COLUMN PROFILES ---

export const columnProfiles: ColumnProfile[] = [];

// --- FINDINGS ---

export const findings: Finding[] = [];

// --- ACTIVITY LOG ---

export const recentActivity: ActivityItem[] = [];

// --- SUMMARY STATS ---

export const summaryStats = {
  totalDatasets: datasets.length,
  totalFindings: findings.length,
  highRiskFindings: findings.filter((f) => f.severity === "high").length,
  pendingReviews: findings.filter((f) => f.status === "pending").length,
};
