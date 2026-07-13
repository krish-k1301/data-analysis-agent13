"use client";

import { useState, useMemo } from "react";
import { findings } from "@/lib/mock-data";
import Link from "next/link";

export default function ReviewQueuePage() {
  const pendingFindings = useMemo(
    () => findings.filter((f) => f.status === "pending"),
    []
  );
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [processed, setProcessed] = useState<Record<string, string>>({});

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleAll = () => {
    const unprocessed = pendingFindings.filter((f) => !processed[f.id]);
    if (selected.size === unprocessed.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(unprocessed.map((f) => f.id)));
    }
  };

  const handleBulkAction = (action: string) => {
    const newProcessed = { ...processed };
    selected.forEach((id) => {
      newProcessed[id] = action;
    });
    setProcessed(newProcessed);
    setSelected(new Set());
  };

  const unprocessedFindings = pendingFindings.filter((f) => !processed[f.id]);
  const processedFindings = pendingFindings.filter((f) => processed[f.id]);

  return (
    <>
      <div className="page-header">
        <h2>Review Queue</h2>
        <p>
          {unprocessedFindings.length} finding
          {unprocessedFindings.length !== 1 ? "s" : ""} pending review
        </p>
      </div>

      {/* Bulk Actions */}
      {selected.size > 0 && (
        <div className="bulk-actions">
          <span className="bulk-actions-count">
            {selected.size} selected
          </span>
          <button
            className="btn btn-accept"
            onClick={() => handleBulkAction("accepted")}
          >
            Approve Selected
          </button>
          <button
            className="btn btn-reject"
            onClick={() => handleBulkAction("rejected")}
          >
            Reject Selected
          </button>
        </div>
      )}

      {/* Pending Queue */}
      <div className="section">
        <div className="section-title">Pending</div>
        <div className="card">
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "40px" }}>
                    <input
                      type="checkbox"
                      className="checkbox"
                      checked={
                        unprocessedFindings.length > 0 &&
                        selected.size === unprocessedFindings.length
                      }
                      onChange={toggleAll}
                    />
                  </th>
                  <th>ID</th>
                  <th>Rule</th>
                  <th>Severity</th>
                  <th>Amount</th>
                  <th>Vendor</th>
                  <th>Date Flagged</th>
                  <th>Risk Score</th>
                </tr>
              </thead>
              <tbody>
                {unprocessedFindings.map((f) => (
                  <tr key={f.id} className="link-row">
                    <td>
                      <input
                        type="checkbox"
                        className="checkbox"
                        checked={selected.has(f.id)}
                        onChange={() => toggleSelect(f.id)}
                      />
                    </td>
                    <td className="cell-mono">
                      <Link
                        href={`/findings/${f.id}`}
                        style={{ color: "var(--text-primary)" }}
                      >
                        {f.id}
                      </Link>
                    </td>
                    <td>{f.rule}</td>
                    <td>
                      <span className={`badge badge-${f.severity}`}>
                        {f.severity}
                      </span>
                    </td>
                    <td className="cell-mono cell-right">
                      ${f.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </td>
                    <td>{f.vendor}</td>
                    <td className="cell-mono">{f.dateFlagged}</td>
                    <td className="cell-mono cell-right">{f.riskScore}</td>
                  </tr>
                ))}
                {unprocessedFindings.length === 0 && (
                  <tr>
                    <td
                      colSpan={8}
                      style={{
                        textAlign: "center",
                        color: "var(--text-muted)",
                        padding: "var(--space-xl)",
                      }}
                    >
                      All findings have been reviewed.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Processed in This Session */}
      {processedFindings.length > 0 && (
        <div className="section">
          <div className="section-title">
            Reviewed This Session ({processedFindings.length})
          </div>
          <div className="card">
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Rule</th>
                    <th>Severity</th>
                    <th>Amount</th>
                    <th>Vendor</th>
                    <th>Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {processedFindings.map((f) => (
                    <tr key={f.id}>
                      <td className="cell-mono">{f.id}</td>
                      <td>{f.rule}</td>
                      <td>
                        <span className={`badge badge-${f.severity}`}>
                          {f.severity}
                        </span>
                      </td>
                      <td className="cell-mono cell-right">
                        ${f.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                      </td>
                      <td>{f.vendor}</td>
                      <td>
                        <span
                          className={`badge ${
                            processed[f.id] === "accepted"
                              ? "badge-accepted"
                              : "badge-rejected"
                          }`}
                        >
                          {processed[f.id]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
