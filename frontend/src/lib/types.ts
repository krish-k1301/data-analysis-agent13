// Types mirror backend/app/schemas/{dataset,finding}.py — keep in sync.

export type DatasetStatus = "queued" | "running" | "complete" | "failed";

export interface Dataset {
  id: string;
  filename: string;
  original_filename: string;
  status: DatasetStatus;
  current_step: string | null;
  progress_pct: number;
  error: string | null;
  row_count: number | null;
  column_count: number | null;
  enabled_rules: string[] | null;
  custom_rule_configs: Record<string, unknown> | null;
  analysis_summary: string | null;
  created_at: string;
  updated_at: string;
}

export type ColumnType = "date" | "numeric" | "text";

export interface ColumnProfileEntry {
  type: ColumnType;
  null_count: number;
  null_pct: number;
  unique_count: number;
  sample_values: string[];
  mean?: number;
  median?: number;
  std?: number;
  min?: number;
  max?: number;
  min_date?: string;
  max_date?: string;
}

export interface DatasetProfile {
  row_count: number;
  column_count: number;
  completeness_pct: number;
  columns: Record<string, ColumnProfileEntry>;
}

export interface SchemaMapping {
  dataset_id: string;
  mapping: Record<string, string>; // role -> source column name
  confirmed: boolean;
}

export type Severity = "HIGH" | "MEDIUM" | "LOW";
export type FindingStatus = "PENDING" | "CONFIRMED" | "DISMISSED";

export interface Finding {
  finding_id: string;
  dataset_id: string;
  rule_id: string;
  rule_name: string;
  severity: Severity;
  risk_score: number;
  risk_justification: string | null;
  flagged_rows: Record<string, unknown>[];
  supporting_metrics: Record<string, unknown>;
  audit_explanation: string;
  llm_enriched_explanation: string | null;
  trace: Record<string, unknown>;
  status: FindingStatus;
  created_at: string;
}

export interface ReviewAction {
  id: string;
  finding_id: string;
  action: "CONFIRM" | "DISMISS" | "NOTE";
  note: string | null;
  reviewer: string | null;
  created_at: string;
}

export interface QueryResult {
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
}

export interface NLQueryResult extends QueryResult {
  sql: string;
}

export interface JobStatus {
  job_id: string;
  status: DatasetStatus;
  current_step: string | null;
  progress_pct: number;
  error: string | null;
}
