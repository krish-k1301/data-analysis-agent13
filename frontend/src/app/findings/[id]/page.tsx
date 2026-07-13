"use client";

import { useState, use } from "react";
import { findings } from "@/lib/mock-data";
import Link from "next/link";

interface FindingDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function FindingDetailPage({ params }: FindingDetailPageProps) {
  const { id } = use(params);
  const finding = findings.find((f) => f.id === id);
  const [notes, setNotes] = useState(finding?.reviewerNotes || "");
  const [actionTaken, setActionTaken] = useState<string | null>(null);

  if (!finding) {
    return (
      <>
        <div className="page-header">
          <h2>Finding Not Found</h2>
          <p>
            No finding with ID {id}.{" "}
            <Link href="/findings" style={{ color: "var(--accent)" }}>
              Return to Findings
            </Link>
          </p>
        </div>
      </>
    );
  }

  const handleAction = (action: string) => {
    setActionTaken(action);
  };

  return (
    <>
      {/* Header */}
      <div className="detail-header">
        <span className="detail-header-id">{finding.id}</span>
        <div className="detail-header-meta">
          <span className={`badge badge-${finding.severity}`}>
            {finding.severity}
          </span>
          <span className={`badge badge-${finding.status}`}>
            {finding.status}
          </span>
        </div>
      </div>

      <div className="page-header" style={{ marginBottom: "var(--space-lg)" }}>
        <h2 style={{ fontSize: "16px", textTransform: "none" }}>
          {finding.rule}
        </h2>
        <p>{finding.description}</p>
      </div>

      {/* Risk Score + Meta */}
      <div
        className="card-grid"
        style={{
          gridTemplateColumns: "repeat(4, 1fr)",
          marginBottom: "var(--space-xl)",
        }}
      >
        <div className="card">
          <div className="card-title">Risk Score</div>
          <div
            className="card-value"
            style={{
              color:
                finding.riskScore >= 80
                  ? "var(--risk-high)"
                  : finding.riskScore >= 50
                  ? "var(--risk-medium)"
                  : "var(--text-secondary)",
            }}
          >
            {finding.riskScore}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Amount</div>
          <div className="card-value" style={{ fontSize: "24px" }}>
            ${finding.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Vendor</div>
          <div style={{ fontSize: "14px", marginTop: "var(--space-sm)" }}>
            {finding.vendor}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Dataset</div>
          <div style={{ fontSize: "14px", marginTop: "var(--space-sm)" }}>
            <Link
              href={`/datasets/${finding.datasetId}`}
              style={{ color: "var(--accent)" }}
            >
              {finding.datasetName}
            </Link>
          </div>
        </div>
      </div>

      <div className="two-col">
        {/* Left Column */}
        <div>
          {/* Evidence Panel */}
          <div className="section">
            <div className="section-title">Evidence</div>
            <div className="evidence-panel">
              <div className="evidence-panel-header">Flagged Record Data</div>
              {Object.entries(finding.evidence).map(([key, value]) => (
                <div className="evidence-row" key={key}>
                  <div className="evidence-key">{key.replace(/_/g, " ")}</div>
                  <div className="evidence-value">{value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div>
          {/* Explanation */}
          <div className="section">
            <div className="section-title">Rule Explanation</div>
            <div className="card">
              <p
                style={{
                  color: "var(--text-secondary)",
                  lineHeight: "1.7",
                  fontSize: "13px",
                }}
              >
                {finding.explanation}
              </p>
            </div>
          </div>

          {/* Reviewer Notes */}
          <div className="section">
            <div className="section-title">Reviewer Notes</div>
            <div className="card">
              {actionTaken ? (
                <div
                  style={{
                    padding: "var(--space-md)",
                    textAlign: "center",
                  }}
                >
                  <span
                    className={`badge ${
                      actionTaken === "accepted"
                        ? "badge-accepted"
                        : actionTaken === "rejected"
                        ? "badge-rejected"
                        : "badge-pending"
                    }`}
                    style={{ fontSize: "13px", padding: "4px 16px" }}
                  >
                    {actionTaken === "accepted"
                      ? "Finding Accepted"
                      : actionTaken === "rejected"
                      ? "Finding Rejected"
                      : "More Evidence Requested"}
                  </span>
                  {notes && (
                    <p
                      style={{
                        marginTop: "var(--space-md)",
                        color: "var(--text-secondary)",
                        fontSize: "13px",
                      }}
                    >
                      {notes}
                    </p>
                  )}
                </div>
              ) : (
                <>
                  <textarea
                    className="form-textarea"
                    placeholder="Add reviewer notes..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                  <div className="actions-row">
                    <button
                      className="btn btn-accept"
                      onClick={() => handleAction("accepted")}
                    >
                      Accept
                    </button>
                    <button
                      className="btn btn-reject"
                      onClick={() => handleAction("rejected")}
                    >
                      Reject
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={() => handleAction("needs_evidence")}
                    >
                      Request Evidence
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
