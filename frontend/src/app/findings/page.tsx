"use client";

import { useState, useMemo } from "react";
import { findings } from "@/lib/mock-data";
import Link from "next/link";

type SortKey = "id" | "rule" | "severity" | "amount" | "vendor" | "riskScore" | "status";
type SortDir = "asc" | "desc";

const severityOrder = { high: 3, medium: 2, low: 1 };

export default function FindingsPage() {
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("riskScore");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

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
    return sortDir === "asc" ? " \u25B2" : " \u25BC";
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
          f.id.toLowerCase().includes(q) ||
          f.rule.toLowerCase().includes(q) ||
          f.vendor.toLowerCase().includes(q) ||
          f.description.toLowerCase().includes(q)
      );
    }

    result.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "id":
          cmp = a.id.localeCompare(b.id);
          break;
        case "rule":
          cmp = a.rule.localeCompare(b.rule);
          break;
        case "severity":
          cmp = severityOrder[a.severity] - severityOrder[b.severity];
          break;
        case "amount":
          cmp = a.amount - b.amount;
          break;
        case "vendor":
          cmp = a.vendor.localeCompare(b.vendor);
          break;
        case "riskScore":
          cmp = a.riskScore - b.riskScore;
          break;
        case "status":
          cmp = a.status.localeCompare(b.status);
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [severityFilter, statusFilter, searchQuery, sortKey, sortDir]);

  return (
    <>
      <div className="page-header">
        <h2>Findings</h2>
        <p>
          {filtered.length} finding{filtered.length !== 1 ? "s" : ""} across all
          datasets
        </p>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <div className="form-group">
          <label className="form-label">Severity</label>
          <select
            className="form-select"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="all">All Severities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Status</label>
          <select
            className="form-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Search</label>
          <input
            className="form-input"
            type="text"
            placeholder="Search by ID, rule, vendor..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Findings Table */}
      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th
                  className="sortable"
                  onClick={() => handleSort("id")}
                >
                  ID{sortIndicator("id")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("rule")}
                >
                  Rule{sortIndicator("rule")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("severity")}
                >
                  Severity{sortIndicator("severity")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("amount")}
                >
                  Amount{sortIndicator("amount")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("vendor")}
                >
                  Vendor{sortIndicator("vendor")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("status")}
                >
                  Status{sortIndicator("status")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("riskScore")}
                >
                  Risk Score{sortIndicator("riskScore")}
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((f) => (
                <tr key={f.id} className="link-row">
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
                  <td>
                    <span className={`badge badge-${f.status}`}>
                      {f.status}
                    </span>
                  </td>
                  <td className="cell-mono cell-right">{f.riskScore}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    style={{
                      textAlign: "center",
                      color: "var(--text-muted)",
                      padding: "var(--space-xl)",
                    }}
                  >
                    No findings match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
