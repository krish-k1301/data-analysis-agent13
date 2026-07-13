const API_BASE_URL = "http://localhost:8000/api";

export async function getDatasets() {
  const response = await fetch(`${API_BASE_URL}/datasets`);
  if (!response.ok) throw new Error("Failed to fetch datasets");
  return response.json();
}

export async function uploadDataset(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
    method: "POST",
    body: formData,
  });
  
  if (!response.ok) throw new Error("Upload failed");
  return response.json();
}

export async function getDatasetStatus(id: string) {
  const response = await fetch(`${API_BASE_URL}/jobs/${id}/status`);
  if (!response.ok) throw new Error("Failed to fetch status");
  return response.json();
}

export async function getFindings(datasetId: string) {
  const response = await fetch(`${API_BASE_URL}/findings/dataset/${datasetId}`);
  if (!response.ok) throw new Error("Failed to fetch findings");
  return response.json();
}

export async function getDatasetDetails(datasetId: string) {
  const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}`);
  if (!response.ok) throw new Error("Failed to fetch dataset details");
  return response.json();
}

export function getExportUrl(datasetId: string, format: "xlsx" | "csv") {
  return `${API_BASE_URL}/datasets/${datasetId}/export?format=${format}`;
}
