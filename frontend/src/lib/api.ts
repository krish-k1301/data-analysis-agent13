import type { Dataset, DatasetProfile, Finding, JobStatus, NLQueryResult, QueryResult, ReviewAction, SchemaMapping } from "./types";

const API_BASE_URL = "http://localhost:8000/api";
const DEFAULT_TIMEOUT_MS = 15000;

async function apiFetch(path: string, options: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${API_BASE_URL}${path}`, { ...options, cache: "no-store", signal: controller.signal });
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("Request timed out — the server may still be processing this dataset. Try again shortly.");
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

async function parseErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json();
    return data.detail || fallback;
  } catch {
    return fallback;
  }
}

export async function getDatasets(): Promise<Dataset[]> {
  const response = await apiFetch("/datasets");
  if (!response.ok) throw new Error("Failed to fetch datasets");
  return response.json();
}

export async function uploadDataset(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(
    "/datasets/upload",
    { method: "POST", body: formData },
    60000
  );

  if (!response.ok) throw new Error("Upload failed");
  return response.json();
}

export async function getDatasetStatus(id: string): Promise<JobStatus> {
  const response = await apiFetch(`/jobs/${id}/status`);
  if (!response.ok) throw new Error("Failed to fetch status");
  return response.json();
}

export async function getDatasetDetails(datasetId: string): Promise<Dataset> {
  const response = await apiFetch(`/datasets/${datasetId}`);
  if (!response.ok) throw new Error("Failed to fetch dataset details");
  return response.json();
}

export async function getDatasetProfile(datasetId: string): Promise<DatasetProfile> {
  const response = await apiFetch(`/datasets/${datasetId}/profile`);
  if (!response.ok) throw new Error("Failed to fetch dataset profile");
  const data = await response.json();
  return data.profile;
}

export async function getDatasetSchema(datasetId: string): Promise<SchemaMapping> {
  const response = await apiFetch(`/datasets/${datasetId}/schema`);
  if (!response.ok) throw new Error("Failed to fetch dataset schema");
  return response.json();
}

export function getExportUrl(datasetId: string, format: "xlsx" | "csv") {
  return `${API_BASE_URL}/datasets/${datasetId}/export?format=${format}`;
}

export async function deleteDataset(datasetId: string): Promise<void> {
  const response = await apiFetch(`/datasets/${datasetId}`, { method: "DELETE" });
  if (!response.ok) throw new Error(await parseErrorDetail(response, "Failed to delete dataset"));
}

export async function getFindings(datasetId: string): Promise<Finding[]> {
  const response = await apiFetch(`/findings/dataset/${datasetId}`);
  if (!response.ok) throw new Error("Failed to fetch findings");
  return response.json();
}

export async function getAllFindings(): Promise<Finding[]> {
  const response = await apiFetch("/findings");
  if (!response.ok) throw new Error("Failed to fetch findings");
  return response.json();
}

export async function getFinding(findingId: string): Promise<Finding> {
  const response = await apiFetch(`/findings/${findingId}`);
  if (!response.ok) throw new Error("Failed to fetch finding");
  return response.json();
}

export async function getFindingReviews(findingId: string): Promise<ReviewAction[]> {
  const response = await apiFetch(`/findings/${findingId}/reviews`);
  if (!response.ok) throw new Error("Failed to fetch review history");
  return response.json();
}

export async function reviewFinding(
  findingId: string,
  action: "CONFIRM" | "DISMISS" | "NOTE",
  note?: string
): Promise<Finding> {
  const response = await apiFetch(`/findings/${findingId}/review`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, note }),
  });
  if (!response.ok) throw new Error(await parseErrorDetail(response, "Failed to submit review"));
  return response.json();
}

export async function runQuery(datasetId: string, sql: string): Promise<QueryResult> {
  const response = await apiFetch(
    `/datasets/${datasetId}/query`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql }),
    },
    30000
  );
  if (!response.ok) throw new Error(await parseErrorDetail(response, "Query failed"));
  return response.json();
}

export async function askDataset(datasetId: string, question: string): Promise<NLQueryResult> {
  const response = await apiFetch(
    `/datasets/${datasetId}/query/ask`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    },
    45000
  );
  if (!response.ok) throw new Error(await parseErrorDetail(response, "Failed to answer question"));
  return response.json();
}
