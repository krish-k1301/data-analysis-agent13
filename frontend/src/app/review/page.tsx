"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getAllFindings, getDatasets, reviewFinding } from "@/lib/api";
import { severityBadgeClass } from "@/lib/format";
import type { Finding } from "@/lib/types";

export default function ReviewQueuePage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [datasetNames, setDatasetNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [justProcessed, setJustProcessed] = useState<{ finding: Finding; action: string }[]>([]);
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);

  const loadFindings = () =>
    getAllFindings()
      .then((f) => {
        setFindings(f);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });

  useEffect(() => {
    loadFindings();
    getDatasets()
      .then((datasets) => {
        const names: Record<string, string> = {};
        for (const d of datasets) names[d.id] = d.original_filename;
        setDatasetNames(names);
      })
      .catch(() => {});
  }, []);

  const pendingFindings = useMemo(() => findings.filter((f) => f.status === "PENDING"), [findings]);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === pendingFindings.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(pendingFindings.map((f) => f.finding_id)));
    }
  };

  const handleBulkAction = async (action: "CONFIRM" | "DISMISS") => {
    setBulkSubmitting(true);
    setBulkError(null);
    const ids = Array.from(selected);
    try {
      const updated = await Promise.all(ids.map((id) => reviewFinding(id, action)));
      setJustProcessed((prev) => [...updated.map((finding) => ({ finding, action })), ...prev]);
      setSelected(new Set());
      await loadFindings();
    } catch (e) {
      setBulkError(e instanceof Error ? e.message : "Bulk review failed");
    } finally {
      setBulkSubmitting(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>Review Queue</h2>
        <p>{loading ? "Loading…" : `${pendingFindings.length} finding${pendingFindings.length !== 1 ? "s" : ""} pending review`}</p>
      </div>

      {/* Bulk Actions */}
      {selected.size > 0 && (
        <div className="bulk-actions">
          <span className="bulk-actions-count">{selected.size} selected</span>
          <button className="btn btn-accept" onClick={() => handleBulkAction("CONFIRM")} disabled={bulkSubmitting}>
            Approve Selected
          </button>
          <button className="btn btn-reject" onClick={() => handleBulkAction("DISMISS")} disabled={bulkSubmitting}>
            Reject Selected
          </button>
          {bulkError && <span style={{ color: "var(--risk-high)", fontSize: "13px" }}>{bulkError}</span>}
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
                      checked={pendingFindings.length > 0 && selected.size === pendingFindings.length}
                      onChange={toggleAll}
                    />
                  </th>
                  <th>ID</th>
                  <th>Rule</th>
                  <th>Severity</th>
                  <th>Dataset</th>
                  <th>Flagged Rows</th>
                  <th>Risk Score</th>
                </tr>
              </thead>
              <tbody>
                {!loading &&
                  pendingFindings.map((f) => (
                    <tr key={f.finding_id} className="link-row">
                      <td>
                        <input
                          type="checkbox"
                          className="checkbox"
                          checked={selected.has(f.finding_id)}
                          onChange={() => toggleSelect(f.finding_id)}
                        />
                      </td>
                      <td className="cell-mono">
                        <Link href={`/findings/${f.finding_id}`} style={{ color: "var(--text-primary)" }}>
                          {f.finding_id}
                        </Link>
                      </td>
                      <td>{f.rule_name}</td>
                      <td>
                        <span className={`badge ${severityBadgeClass(f.severity)}`}>{f.severity}</span>
                      </td>
                      <td>
                        <Link href={`/datasets/${f.dataset_id}`} style={{ color: "var(--accent)" }}>
                          {datasetNames[f.dataset_id] ?? f.dataset_id}
                        </Link>
                      </td>
                      <td className="cell-mono cell-right">{f.flagged_rows.length}</td>
                      <td className="cell-mono cell-right">{f.risk_score}</td>
                    </tr>
                  ))}
                {loading && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", color: "var(--text-muted)", padding: "var(--space-xl)" }}>
                      Loading...
                    </td>
                  </tr>
                )}
                {!loading && pendingFindings.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", color: "var(--text-muted)", padding: "var(--space-xl)" }}>
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
      {justProcessed.length > 0 && (
        <div className="section">
          <div className="section-title">Reviewed This Session ({justProcessed.length})</div>
          <div className="card">
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Rule</th>
                    <th>Severity</th>
                    <th>Dataset</th>
                    <th>Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {justProcessed.map(({ finding: f, action }) => (
                    <tr key={f.finding_id}>
                      <td className="cell-mono">{f.finding_id}</td>
                      <td>{f.rule_name}</td>
                      <td>
                        <span className={`badge ${severityBadgeClass(f.severity)}`}>{f.severity}</span>
                      </td>
                      <td>{datasetNames[f.dataset_id] ?? f.dataset_id}</td>
                      <td>
                        <span className={`badge ${action === "CONFIRM" ? "badge-accepted" : "badge-rejected"}`}>
                          {action === "CONFIRM" ? "accepted" : "rejected"}
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
