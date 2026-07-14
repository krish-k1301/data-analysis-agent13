"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { deleteDataset, getAllFindings, getDatasets, uploadDataset } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Dataset, Finding } from "@/lib/types";
import DatasetProgress from "@/components/DatasetProgress";

export default function DashboardPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadData = () => {
    return Promise.all([getDatasets(), getAllFindings()])
      .then(([d, f]) => {
        setDatasets(d);
        setFindings(f);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalDatasets = datasets.length;
  const totalFindings = findings.length;
  const highRiskFindings = findings.filter((f) => f.severity === "HIGH").length;
  const pendingReviews = findings.filter((f) => f.status === "PENDING").length;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith(".csv") || file.name.endsWith(".xlsx"))) {
      setSelectedFile(file);
      setUploadError(null);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setUploadError(null);
    try {
      await uploadDataset(selectedFile);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadData();
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Failed to upload dataset.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (ds: Dataset) => {
    if (!confirm(`Delete "${ds.original_filename}"? This removes the dataset and all its findings.`)) return;
    setDeletingId(ds.id);
    try {
      await deleteDataset(ds.id);
      await loadData();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to delete dataset.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Overview of audit analysis activity</p>
      </div>

      {/* Upload */}
      <div className="section">
        <div className="section-title">Upload Dataset</div>
        <div className="card">
          <div
            className={`drop-zone ${isDragOver ? "active" : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="drop-zone-label">Drop file here or click to browse</div>
            <div className="drop-zone-sublabel">Accepted formats: .csv, .xlsx</div>
            {selectedFile && <div className="drop-zone-file">{selectedFile.name}</div>}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx"
              onChange={handleFileSelect}
              style={{ display: "none" }}
            />
          </div>

          {uploadError && (
            <p style={{ color: "var(--risk-high)", marginTop: "var(--space-md)" }}>{uploadError}</p>
          )}

          <div className="actions-row" style={{ marginTop: "var(--space-md)" }}>
            <button className="btn btn-primary" onClick={handleUpload} disabled={!selectedFile || isUploading}>
              {isUploading ? "Uploading…" : "Upload"}
            </button>
            {selectedFile && !isUploading && (
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setSelectedFile(null);
                  setUploadError(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="card-grid" style={{ marginBottom: "var(--space-xl)" }}>
        <div className="card">
          <div className="card-title">Total Datasets</div>
          <div className="card-value">{loading ? "-" : totalDatasets}</div>
        </div>
        <div className="card">
          <div className="card-title">Total Findings</div>
          <div className="card-value">{loading ? "-" : totalFindings}</div>
        </div>
        <div className="card">
          <div className="card-title">High Risk</div>
          <div className="card-value" style={{ color: "var(--risk-high)" }}>
            {loading ? "-" : highRiskFindings}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Pending Review</div>
          <div className="card-value" style={{ color: "var(--status-pending)" }}>
            {loading ? "-" : pendingReviews}
          </div>
        </div>
      </div>

      {/* Datasets */}
      <div className="section">
        <div className="section-title">Datasets</div>
        <div className="card">
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {datasets.length === 0 && !loading && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: "center", padding: "var(--space-md)" }}>
                      No datasets found. Upload one above to get started!
                    </td>
                  </tr>
                )}
                {loading && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: "center", padding: "var(--space-md)" }}>
                      Loading...
                    </td>
                  </tr>
                )}
                {datasets.map((ds) => (
                  <tr key={ds.id} className="link-row">
                    <td>
                      <Link href={`/datasets/${ds.id}`} style={{ color: "var(--text-primary)" }}>
                        {ds.original_filename}
                      </Link>
                    </td>
                    <td>
                      <DatasetProgress
                        datasetId={ds.id}
                        initialStatus={ds.status}
                        initialProgressPct={ds.progress_pct}
                        initialCurrentStep={ds.current_step}
                        initialError={ds.error}
                        onSettled={loadData}
                      />
                    </td>
                    <td className="cell-mono">{formatDateTime(ds.created_at)}</td>
                    <td className="cell-right">
                      <div style={{ display: "flex", gap: "var(--space-sm)", justifyContent: "flex-end" }}>
                        <Link href={`/datasets/${ds.id}/query`}>
                          <button
                            className="btn btn-primary"
                            style={{ fontSize: "11px", padding: "4px 10px" }}
                            disabled={ds.status !== "complete"}
                          >
                            Query
                          </button>
                        </Link>
                        <button
                          className="btn btn-secondary"
                          style={{ fontSize: "11px", padding: "4px 10px" }}
                          onClick={() => handleDelete(ds)}
                          disabled={deletingId === ds.id}
                        >
                          {deletingId === ds.id ? "Deleting…" : "Delete"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
