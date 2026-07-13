"use client";

import { useState, useRef } from "react";
import { uploadDataset } from "@/lib/api";

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      setUploadProgress(0);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadProgress(0);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setUploadProgress(20);
    
    try {
      const response = await uploadDataset(selectedFile);
      setUploadProgress(100);
      alert(`Successfully uploaded ${response.filename} (ID: ${response.id})`);
    } catch (error) {
      alert("Failed to upload dataset.");
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  return (
    <>
      <div className="page-header">
        <h2>Upload Dataset</h2>
        <p>Upload a CSV or XLSX file for audit analysis</p>
      </div>

      <div className="upload-form">
        {/* Drop Zone */}
        <div
          className={`drop-zone ${isDragOver ? "active" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="drop-zone-label">
            Drop file here or click to browse
          </div>
          <div className="drop-zone-sublabel">
            Accepted formats: .csv, .xlsx
          </div>
          {selectedFile && (
            <div className="drop-zone-file">{selectedFile.name}</div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx"
            onChange={handleFileSelect}
            style={{ display: "none" }}
          />
        </div>

        {/* File Details */}
        {selectedFile && (
          <div className="card" style={{ marginTop: "var(--space-lg)" }}>
            <div className="section-title">File Details</div>
            <div className="table-container">
              <table>
                <tbody>
                  <tr>
                    <td style={{ color: "var(--text-secondary)", width: "160px" }}>
                      Filename
                    </td>
                    <td className="cell-mono">{selectedFile.name}</td>
                  </tr>
                  <tr>
                    <td style={{ color: "var(--text-secondary)" }}>Size</td>
                    <td className="cell-mono">
                      {formatFileSize(selectedFile.size)}
                    </td>
                  </tr>
                  <tr>
                    <td style={{ color: "var(--text-secondary)" }}>Type</td>
                    <td className="cell-mono">
                      {selectedFile.name.endsWith(".csv")
                        ? "CSV (Comma-Separated Values)"
                        : "XLSX (Excel Workbook)"}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Progress Bar */}
        {uploadProgress > 0 && (
          <div style={{ marginTop: "var(--space-lg)" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "var(--space-xs)",
              }}
            >
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--text-secondary)",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                {uploadProgress >= 100 ? "Upload Complete" : "Uploading..."}
              </span>
              <span
                className="cell-mono"
                style={{ fontSize: "11px", color: "var(--text-secondary)" }}
              >
                {Math.round(uploadProgress)}%
              </span>
            </div>
            <div className="progress-bar-track">
              <div
                className="progress-bar-fill"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="upload-actions">
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? "Uploading..." : "Upload"}
          </button>
          {selectedFile && !isUploading && (
            <button
              className="btn btn-secondary"
              onClick={() => {
                setSelectedFile(null);
                setUploadProgress(0);
              }}
            >
              Clear
            </button>
          )}
        </div>
      </div>
    </>
  );
}
