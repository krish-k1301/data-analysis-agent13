"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { Finding, Severity } from "@/lib/types";
import { findingStatusBadgeClass, findingStatusLabel, formatDateTime, severityBadgeClass } from "@/lib/format";

const SEVERITY_RANK: Record<Severity, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };

interface FindingGroup {
  ruleName: string;
  findings: Finding[];
  maxSeverity: Severity;
}

function groupFindings(findings: Finding[]): FindingGroup[] {
  const groups = new Map<string, Finding[]>();
  for (const f of findings) {
    const list = groups.get(f.rule_name) ?? [];
    list.push(f);
    groups.set(f.rule_name, list);
  }

  const result: FindingGroup[] = Array.from(groups.entries()).map(([ruleName, list]) => {
    const sorted = [...list].sort((a, b) => b.risk_score - a.risk_score);
    const maxSeverity = sorted.reduce<Severity>(
      (worst, f) => (SEVERITY_RANK[f.severity] > SEVERITY_RANK[worst] ? f.severity : worst),
      sorted[0]?.severity ?? "LOW"
    );
    return { ruleName, findings: sorted, maxSeverity };
  });

  result.sort(
    (a, b) =>
      SEVERITY_RANK[b.maxSeverity] - SEVERITY_RANK[a.maxSeverity] || b.findings.length - a.findings.length
  );
  return result;
}

function AccordionRow({ group }: { group: FindingGroup }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="accordion-item">
      <div className="accordion-header" onClick={() => setOpen((o) => !o)}>
        <div className="accordion-header-left">
          <span className="accordion-icon">{open ? "▼" : "▶"}</span>
          <span className="accordion-title">{group.ruleName}</span>
          <span className="accordion-count">
            {group.findings.length} finding{group.findings.length !== 1 ? "s" : ""}
          </span>
        </div>
        <div className="accordion-header-right">
          <span className={`badge ${severityBadgeClass(group.maxSeverity)}`}>{group.maxSeverity}</span>
        </div>
      </div>
      {open && (
        <div className="accordion-body">
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Risk Score</th>
                  <th>Status</th>
                  <th>Flagged Rows</th>
                  <th>Flagged On</th>
                </tr>
              </thead>
              <tbody>
                {group.findings.map((f) => (
                  <tr key={f.finding_id} className="link-row">
                    <td>
                      <Link href={`/findings/${f.finding_id}`} style={{ color: "var(--text-primary)" }}>
                        <span className={`badge ${severityBadgeClass(f.severity)}`}>{f.severity}</span>
                      </Link>
                    </td>
                    <td className="cell-mono cell-right">{f.risk_score}</td>
                    <td>
                      <span className={`badge ${findingStatusBadgeClass(f.status)}`}>
                        {findingStatusLabel(f.status)}
                      </span>
                    </td>
                    <td className="cell-mono cell-right">{f.flagged_rows.length}</td>
                    <td className="cell-mono">{formatDateTime(f.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default function FindingsAccordion({ findings }: { findings: Finding[] }) {
  const groups = useMemo(() => groupFindings(findings), [findings]);

  if (findings.length === 0) {
    return (
      <div className="card">
        <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "var(--space-md) 0" }}>
          No findings for this dataset.
        </p>
      </div>
    );
  }

  return (
    <div>
      {groups.map((group) => (
        <AccordionRow key={group.ruleName} group={group} />
      ))}
    </div>
  );
}
