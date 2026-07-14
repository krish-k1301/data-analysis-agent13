"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getAllFindings, getDatasets } from "@/lib/api";
import { findingStatusBadgeClass, findingStatusLabel, severityBadgeClass } from "@/lib/format";
import type { Finding } from "@/lib/types";

type SortKey = "rule_name" | "severity" | "flagged_rows" | "status" | "risk_score";
type SortDir = "asc" | "desc";

const SEVERITY_ORDER: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };

interface DatasetGroup {
  datasetId: string;
  datasetName: string;
  findings: Finding[];
  maxSeverity: string;
}

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [datasetNames, setDatasetNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("risk_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    Promise.all([getAllFindings(), getDatasets()])
      .then(([f, datasets]) => {
        setFindings(f);
        const names: Record<string, string> = {};
        for (const d of datasets) names[d.id] = d.original_filename;
        setDatasetNames(names);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sortIndicator = (key: SortKey) => {
    if (sortKey !== key) return "";
    return sortDir === "asc" ? " ▲" : " ▼";
  };

  const filtered = useMemo(() => {
    let result = [...findings];

    if (severityFilter !== "all") {
      result = result.filter((f) => f.severity === severityFilter);
    }
    if (statusFilter !== "all") {
      result = result.filter((f) => f.status === statusFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (f) =>
          f.rule_name.toLowerCase().includes(q) ||
          f.audit_explanation.toLowerCase().includes(q) ||
          (datasetNames[f.dataset_id] ?? "").toLowerCase().includes(q)
      );
    }

    result.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "rule_name":
          cmp = a.rule_name.localeCompare(b.rule_name);
          break;
        case "severity":
          cmp = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
          break;
        case "flagged_rows":
          cmp = a.flagged_rows.length - b.flagged_rows.length;
          break;
        case "status":
          cmp = a.status.localeCompare(b.status);
          break;
        case "risk_score":
          cmp = a.risk_score - b.risk_score;
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [findings, datasetNames, severityFilter, statusFilter, searchQuery, sortKey, sortDir]);

  const groups = useMemo<DatasetGroup[]>(() => {
    const byDataset = new Map<string, Finding[]>();
    for (const f of filtered) {
      const list = byDataset.get(f.dataset_id) ?? [];
      list.push(f);
      byDataset.set(f.dataset_id, list);
    }

    const result: DatasetGroup[] = Array.from(byDataset.entries()).map(([datasetId, list]) => {
      const maxSeverity = list.reduce(
        (worst, f) => (SEVERITY_ORDER[f.severity] > SEVERITY_ORDER[worst] ? f.severity : worst),
        list[0]?.severity ?? "LOW"
      );
      return { datasetId, datasetName: datasetNames[datasetId] ?? datasetId, findings: list, maxSeverity };
    });

    result.sort(
      (a, b) => SEVERITY_ORDER[b.maxSeverity] - SEVERITY_ORDER[a.maxSeverity] || b.findings.length - a.findings.length
    );
    return result;
  }, [filtered, datasetNames]);

  return (
    <>
      <div className="page-header">
        <h2>Findings</h2>
        <p>
          {loading ? "Loading…" : `${filtered.length} finding${filtered.length !== 1 ? "s" : ""} across all datasets`}
        </p>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <div className="form-group">
          <label className="form-label">Severity</label>
          <select className="form-select" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
            <option value="all">All Severities</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Status</label>
          <select className="form-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="DISMISSED">Dismissed</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Search</label>
          <input
            className="form-input"
            type="text"
            placeholder="Search by rule, dataset..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {loading && (
        <div className="card">
          <p style={{ textAlign: "center", color: "var(--text-muted)", padding: "var(--space-xl)" }}>Loading...</p>
        </div>
      )}

      {!loading && groups.length === 0 && (
        <div className="card">
          <p style={{ textAlign: "center", color: "var(--text-muted)", padding: "var(--space-xl)" }}>
            No findings match the current filters.
          </p>
        </div>
      )}

      {!loading &&
        groups.map((group) => (
          <div className="section" key={group.datasetId}>
            <div className="section-title" style={{ display: "flex", alignItems: "center", gap: "var(--space-md)" }}>
              <Link href={`/datasets/${group.datasetId}`} style={{ color: "var(--text-primary)" }}>
                {group.datasetName}
              </Link>
              <span className="badge badge-low">
                {group.findings.length} finding{group.findings.length !== 1 ? "s" : ""}
              </span>
              <span className={`badge ${severityBadgeClass(group.maxSeverity as Finding["severity"])}`}>
                {group.maxSeverity}
              </span>
            </div>
            <div className="card">
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th className="sortable" onClick={() => handleSort("rule_name")}>
                        Rule{sortIndicator("rule_name")}
                      </th>
                      <th className="sortable" onClick={() => handleSort("severity")}>
                        Severity{sortIndicator("severity")}
                      </th>
                      <th className="sortable" onClick={() => handleSort("flagged_rows")}>
                        Flagged Rows{sortIndicator("flagged_rows")}
                      </th>
                      <th className="sortable" onClick={() => handleSort("status")}>
                        Status{sortIndicator("status")}
                      </th>
                      <th className="sortable" onClick={() => handleSort("risk_score")}>
                        Risk Score{sortIndicator("risk_score")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.findings.map((f) => (
                      <tr key={f.finding_id} className="link-row">
                        <td>
                          <Link href={`/findings/${f.finding_id}`} style={{ color: "var(--text-primary)" }}>
                            {f.rule_name}
                          </Link>
                        </td>
                        <td>
                          <span className={`badge ${severityBadgeClass(f.severity)}`}>{f.severity}</span>
                        </td>
                        <td className="cell-mono cell-right">{f.flagged_rows.length}</td>
                        <td>
                          <span className={`badge ${findingStatusBadgeClass(f.status)}`}>
                            {findingStatusLabel(f.status)}
                          </span>
                        </td>
                        <td className="cell-mono cell-right">{f.risk_score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ))}
    </>
  );
}
