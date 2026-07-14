"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getDatasetDetails, getFinding, getFindingReviews, reviewFinding } from "@/lib/api";
import { findingStatusBadgeClass, findingStatusLabel, formatDateTime, severityBadgeClass } from "@/lib/format";
import type { Dataset, Finding, ReviewAction } from "@/lib/types";

interface FindingDetailPageProps {
  params: Promise<{ id: string }>;
}

const MAX_EVIDENCE_ROWS = 25;

function evidenceColumns(rows: Record<string, unknown>[]): string[] {
  const cols = new Set<string>();
  for (const row of rows.slice(0, MAX_EVIDENCE_ROWS)) {
    Object.keys(row).forEach((k) => cols.add(k));
  }
  return Array.from(cols);
}

export default function FindingDetailPage({ params }: FindingDetailPageProps) {
  const { id } = use(params);
  const [finding, setFinding] = useState<Finding | null>(null);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [reviews, setReviews] = useState<ReviewAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  useEffect(() => {
    getFinding(id)
      .then((f) => {
        setFinding(f);
        setLoading(false);
      })
      .catch(() => {
        setNotFound(true);
        setLoading(false);
      });
    getFindingReviews(id)
      .then(setReviews)
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    if (finding) {
      getDatasetDetails(finding.dataset_id)
        .then(setDataset)
        .catch(() => {});
    }
  }, [finding]);

  const handleReview = async (action: "CONFIRM" | "DISMISS" | "NOTE") => {
    if (!finding) return;
    setSubmitting(true);
    setReviewError(null);
    try {
      const updated = await reviewFinding(finding.finding_id, action, note.trim() || undefined);
      setFinding(updated);
      const freshReviews = await getFindingReviews(finding.finding_id);
      setReviews(freshReviews);
      setNote("");
    } catch (e) {
      setReviewError(e instanceof Error ? e.message : "Failed to submit review");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page-header">
        <p>Loading…</p>
      </div>
    );
  }

  if (notFound || !finding) {
    return (
      <div className="page-header">
        <h2>Finding Not Found</h2>
        <p>
          No finding with ID {id}.{" "}
          <Link href="/findings" style={{ color: "var(--accent)" }}>
            Return to Findings
          </Link>
        </p>
      </div>
    );
  }

  const rows = finding.flagged_rows;
  const columns = evidenceColumns(rows);
  const metrics = Object.entries(finding.supporting_metrics ?? {});

  return (
    <>
      {/* Header */}
      <div className="detail-header">
        <span className="detail-header-id">{finding.rule_name}</span>
        <div className="detail-header-meta">
          <span className={`badge ${severityBadgeClass(finding.severity)}`}>{finding.severity}</span>
          <span className={`badge ${findingStatusBadgeClass(finding.status)}`}>
            {findingStatusLabel(finding.status)}
          </span>
        </div>
      </div>

      <div className="page-header" style={{ marginBottom: "var(--space-lg)" }}>
        <p>
          Dataset:{" "}
          <Link href={`/datasets/${finding.dataset_id}`} style={{ color: "var(--accent)" }}>
            {dataset?.original_filename ?? finding.dataset_id}
          </Link>
        </p>
      </div>

      {/* Risk Score + Meta */}
      <div className="card-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: "var(--space-xl)" }}>
        <div className="card">
          <div className="card-title">Risk Score</div>
          <div
            className="card-value"
            style={{
              color:
                finding.risk_score >= 80
                  ? "var(--risk-high)"
                  : finding.risk_score >= 50
                  ? "var(--risk-medium)"
                  : "var(--text-secondary)",
            }}
          >
            {finding.risk_score}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Flagged Rows</div>
          <div className="card-value" style={{ fontSize: "24px" }}>
            {rows.length}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Rule ID</div>
          <div className="cell-mono" style={{ fontSize: "14px", marginTop: "var(--space-sm)" }}>
            {finding.rule_id}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Flagged On</div>
          <div className="cell-mono" style={{ fontSize: "14px", marginTop: "var(--space-sm)" }}>
            {formatDateTime(finding.created_at)}
          </div>
        </div>
      </div>

      <div className="two-col">
        {/* Left Column */}
        <div>
          {/* Evidence Panel */}
          <div className="section">
            <div className="section-title">Evidence ({rows.length} flagged row{rows.length !== 1 ? "s" : ""})</div>
            {rows.length === 0 ? (
              <div className="card">
                <p style={{ color: "var(--text-muted)" }}>No flagged rows recorded for this finding.</p>
              </div>
            ) : (
              <div className="card" style={{ padding: 0 }}>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        {columns.map((c) => (
                          <th key={c}>{c.replace(/_/g, " ")}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.slice(0, MAX_EVIDENCE_ROWS).map((row, i) => (
                        <tr key={i}>
                          {columns.map((c) => (
                            <td key={c} className="cell-mono">
                              {row[c] === null || row[c] === undefined ? "—" : String(row[c])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {rows.length > MAX_EVIDENCE_ROWS && (
                  <p style={{ padding: "var(--space-md) var(--space-lg)", color: "var(--text-muted)", fontSize: "12px" }}>
                    Showing {MAX_EVIDENCE_ROWS} of {rows.length} rows.{" "}
                    <Link href={`/datasets/${finding.dataset_id}/query`} style={{ color: "var(--accent)" }}>
                      Explore all of them via SQL query
                    </Link>
                    .
                  </p>
                )}
              </div>
            )}
          </div>

          {metrics.length > 0 && (
            <div className="section">
              <div className="section-title">Supporting Metrics</div>
              <div className="evidence-panel">
                {metrics.map(([key, value]) => (
                  <div className="evidence-row" key={key}>
                    <div className="evidence-key">{key.replace(/_/g, " ")}</div>
                    <div className="evidence-value">{String(value)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column */}
        <div>
          {/* Explanation */}
          <div className="section">
            <div className="section-title">Rule Explanation</div>
            <div className="card">
              <p style={{ color: "var(--text-secondary)", lineHeight: "1.7", fontSize: "13px" }}>
                {finding.audit_explanation}
              </p>
            </div>
          </div>

          {finding.llm_enriched_explanation && (
            <div className="section">
              <div className="section-title">AI-Enriched Explanation</div>
              <div className="card">
                <p style={{ color: "var(--text-primary)", lineHeight: "1.7", fontSize: "13px" }}>
                  {finding.llm_enriched_explanation}
                </p>
              </div>
            </div>
          )}

          {finding.risk_justification && (
            <div className="section">
              <div className="section-title">Risk Justification</div>
              <div className="card">
                <p style={{ color: "var(--text-secondary)", lineHeight: "1.7", fontSize: "13px" }}>
                  {finding.risk_justification}
                </p>
              </div>
            </div>
          )}

          {/* Reviewer Notes */}
          <div className="section">
            <div className="section-title">Review</div>
            <div className="card">
              <textarea
                className="form-textarea"
                placeholder="Add reviewer notes..."
                value={note}
                onChange={(e) => setNote(e.target.value)}
                disabled={submitting}
              />
              <div className="actions-row">
                <button
                  className="btn btn-accept"
                  onClick={() => handleReview("CONFIRM")}
                  disabled={submitting}
                >
                  Accept
                </button>
                <button
                  className="btn btn-reject"
                  onClick={() => handleReview("DISMISS")}
                  disabled={submitting}
                >
                  Reject
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => handleReview("NOTE")}
                  disabled={submitting || !note.trim()}
                >
                  Save Note
                </button>
              </div>
              {reviewError && (
                <p style={{ color: "var(--risk-high)", marginTop: "var(--space-md)", fontSize: "13px" }}>
                  {reviewError}
                </p>
              )}
            </div>
          </div>

          {reviews.length > 0 && (
            <div className="section">
              <div className="section-title">Review History</div>
              <div className="evidence-panel">
                {reviews.map((r) => (
                  <div className="evidence-row" key={r.id}>
                    <div className="evidence-key">{formatDateTime(r.created_at)}</div>
                    <div className="evidence-value">
                      <strong>{r.action}</strong>
                      {r.reviewer ? ` by ${r.reviewer}` : ""}
                      {r.note ? ` — ${r.note}` : ""}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
