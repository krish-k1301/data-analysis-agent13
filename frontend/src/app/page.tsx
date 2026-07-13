"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDatasets } from "@/lib/api";
import { Dataset, summaryStats, recentActivity, findings } from "@/lib/mock-data"; // We kept the empty arrays and types

export default function DashboardPage() {
  const [realDatasets, setRealDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDatasets()
      .then((data) => {
        setRealDatasets(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const totalDatasets = realDatasets.length;

  return (
    <>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Overview of audit analysis activity</p>
      </div>

      {/* Summary Cards */}
      <div className="card-grid" style={{ marginBottom: "var(--space-xl)" }}>
        <div className="card">
          <div className="card-title">Total Datasets</div>
          <div className="card-value">{loading ? "-" : totalDatasets}</div>
        </div>
        <div className="card">
          <div className="card-title">Total Findings</div>
          <div className="card-value">{summaryStats.totalFindings}</div>
        </div>
        <div className="card">
          <div className="card-title">High Risk</div>
          <div className="card-value" style={{ color: "var(--risk-high)" }}>
            {summaryStats.highRiskFindings}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Pending Review</div>
          <div className="card-value" style={{ color: "var(--status-pending)" }}>
            {summaryStats.pendingReviews}
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
                  <th>ID</th>
                  <th>Filename</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {realDatasets.length === 0 && !loading && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: "center", padding: "var(--space-md)" }}>
                      No datasets found. Upload one to get started!
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
                {realDatasets.map((ds) => (
                  <tr key={ds.id} className="link-row">
                    <td className="cell-mono">{ds.id}</td>
                    <td>
                      <Link href={`/datasets/${ds.id}`} style={{ color: "var(--text-primary)" }}>
                        {ds.filename}
                      </Link>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          ds.status === "COMPLETED"
                            ? "badge-accepted"
                            : ds.status === "FAILED"
                            ? "badge-high"
                            : "badge-pending"
                        }`}
                      >
                        {ds.status}
                      </span>
                    </td>
                    <td className="cell-mono">{new Date(ds.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Other sections removed or left empty since we don't have endpoints for them yet */}
    </>
  );
}
