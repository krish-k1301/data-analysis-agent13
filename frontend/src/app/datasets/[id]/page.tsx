import { datasets, columnProfiles, type ColumnProfile } from "@/lib/mock-data";
import Link from "next/link";
import { getDatasetDetails, getExportUrl } from "@/lib/api";

interface DatasetProfilePageProps {
  params: Promise<{ id: string }>;
}

export default async function DatasetProfilePage({ params }: DatasetProfilePageProps) {
  const { id } = await params;

  // Try to fetch real data from API, fallback to mock data
  let dataset;
  let columnData: ColumnProfile[] = columnProfiles;

  try {
    const apiDataset = await getDatasetDetails(id);
    dataset = apiDataset;
    // If API returns column profiles, use them; otherwise use mock
    if (apiDataset.columns) {
      columnData = apiDataset.columns;
    }
  } catch {
    // Fallback to mock data
    dataset = datasets.find((d) => d.id === id);
  }

  if (!dataset) {
    return (
      <>
        <div className="page-header">
          <h2>Dataset Not Found</h2>
          <p>
            No dataset with ID {id}.{" "}
            <Link href="/" style={{ color: "var(--accent)" }}>
              Return to Dashboard
            </Link>
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="page-header">
        <h2>{dataset.name}</h2>
        <p>
          Dataset profile and column-level statistics for {dataset.filename}
        </p>
      </div>

      {/* Download Buttons - Show only when status is "complete" */}
      {dataset.status === "complete" && (
        <div
          className="card"
          style={{ marginBottom: "var(--space-xl)", padding: "var(--space-lg)" }}
        >
          <div style={{ display: "flex", gap: "var(--space-md)" }}>
            <a href={getExportUrl(dataset.id, "xlsx")}>
              <button
                style={{
                  padding: "var(--space-sm) var(--space-md)",
                  backgroundColor: "var(--accent)",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: 500,
                }}
              >
                Download XLSX
              </button>
            </a>
            <a href={getExportUrl(dataset.id, "csv")}>
              <button
                style={{
                  padding: "var(--space-sm) var(--space-md)",
                  backgroundColor: "var(--accent)",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: 500,
                }}
              >
                Download CSV
              </button>
            </a>
          </div>
        </div>
      )}

      {/* Dataset Summary Card */}
      <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
        <div className="section-title">Dataset Summary</div>
        <div className="table-container">
          <table>
            <tbody>
              <tr>
                <td
                  style={{
                    color: "var(--text-secondary)",
                    width: "200px",
                    fontWeight: 600,
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Dataset ID
                </td>
                <td className="cell-mono">{dataset.id}</td>
              </tr>
              <tr>
                <td
                  style={{
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Filename
                </td>
                <td className="cell-mono">{dataset.filename}</td>
              </tr>
              <tr>
                <td
                  style={{
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Row Count
                </td>
                <td className="cell-mono">
                  {dataset.rowCount.toLocaleString()}
                </td>
              </tr>
              <tr>
                <td
                  style={{
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Column Count
                </td>
                <td className="cell-mono">{dataset.columnCount}</td>
              </tr>
              <tr>
                <td
                  style={{
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  File Size
                </td>
                <td className="cell-mono">{dataset.fileSize}</td>
              </tr>
              <tr>
                <td
                  style={{
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Upload Date
                </td>
                <td className="cell-mono">{dataset.uploadDate}</td>
              </tr>
              <tr>
                <td
                  style={{
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Status
                </td>
                <td>
                  <span
                    className={`badge ${
                      dataset.status === "analyzed" || dataset.status === "reviewed"
                        ? "badge-accepted"
                        : dataset.status === "profiled"
                        ? "badge-pending"
                        : "badge-low"
                    }`}
                  >
                    {dataset.status}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Executive Summary Card - Show when analysis_summary is available */}
      {dataset.analysis_summary && (
        <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
          <div className="section-title">Executive Summary</div>

          {/* Executive Summary Text */}
          {dataset.analysis_summary.executive_summary && (
            <div style={{ marginBottom: "var(--space-lg)" }}>
              <p style={{ color: "var(--text-primary)", lineHeight: "1.6" }}>
                {dataset.analysis_summary.executive_summary}
              </p>
            </div>
          )}

          {/* Findings by Severity */}
          {dataset.analysis_summary.findings_by_severity && (
            <div style={{ marginBottom: "var(--space-lg)" }}>
              <div
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  color: "var(--text-secondary)",
                  marginBottom: "var(--space-md)",
                }}
              >
                Findings by Severity
              </div>
              <div style={{ display: "flex", gap: "var(--space-md)", flexWrap: "wrap" }}>
                {dataset.analysis_summary.findings_by_severity.HIGH !== undefined && (
                  <div
                    style={{
                      padding: "var(--space-sm) var(--space-md)",
                      backgroundColor: "rgba(220, 38, 38, 0.1)",
                      borderRadius: "4px",
                    }}
                  >
                    <span style={{ color: "var(--risk-high)", fontWeight: 600 }}>
                      High: {dataset.analysis_summary.findings_by_severity.HIGH}
                    </span>
                  </div>
                )}
                {dataset.analysis_summary.findings_by_severity.MEDIUM !== undefined && (
                  <div
                    style={{
                      padding: "var(--space-sm) var(--space-md)",
                      backgroundColor: "rgba(245, 158, 11, 0.1)",
                      borderRadius: "4px",
                    }}
                  >
                    <span style={{ color: "var(--risk-medium)", fontWeight: 600 }}>
                      Medium: {dataset.analysis_summary.findings_by_severity.MEDIUM}
                    </span>
                  </div>
                )}
                {dataset.analysis_summary.findings_by_severity.LOW !== undefined && (
                  <div
                    style={{
                      padding: "var(--space-sm) var(--space-md)",
                      backgroundColor: "rgba(34, 197, 94, 0.1)",
                      borderRadius: "4px",
                    }}
                  >
                    <span style={{ color: "var(--risk-low)", fontWeight: 600 }}>
                      Low: {dataset.analysis_summary.findings_by_severity.LOW}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Key Risks */}
          {dataset.analysis_summary.key_risks &&
            dataset.analysis_summary.key_risks.length > 0 && (
              <div style={{ marginBottom: "var(--space-lg)" }}>
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                    color: "var(--text-secondary)",
                    marginBottom: "var(--space-md)",
                  }}
                >
                  Key Risks
                </div>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: "var(--space-md)",
                    color: "var(--text-primary)",
                  }}
                >
                  {dataset.analysis_summary.key_risks.map((risk: string, idx: number) => (
                    <li key={idx} style={{ marginBottom: "var(--space-sm)" }}>
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>
            )}

          {/* Fraud Assessment */}
          {dataset.analysis_summary.fraud_assessment?.assessment && (
            <div>
              <div
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  color: "var(--text-secondary)",
                  marginBottom: "var(--space-md)",
                }}
              >
                Fraud Assessment
              </div>
              <p style={{ color: "var(--text-primary)", lineHeight: "1.6", margin: 0 }}>
                {dataset.analysis_summary.fraud_assessment.assessment}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Column Profiles */}
      <div className="section">
        <div className="section-title">Column Profile</div>
        <div className="card">
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Column Name</th>
                  <th>Data Type</th>
                  <th>Null Count</th>
                  <th>Null %</th>
                  <th>Unique Count</th>
                  <th>Min</th>
                  <th>Max</th>
                  <th>Mean</th>
                </tr>
              </thead>
              <tbody>
                {columnData.map((col: ColumnProfile) => (
                  <tr key={col.name}>
                    <td className="cell-mono">{col.name}</td>
                    <td>
                      <span className="badge badge-low">{col.dataType}</span>
                    </td>
                    <td className="cell-mono cell-right">
                      {col.nullCount.toLocaleString()}
                    </td>
                    <td
                      className="cell-mono cell-right"
                      style={{
                        color:
                          col.nullPercent > 5
                            ? "var(--risk-medium)"
                            : col.nullPercent > 0
                            ? "var(--text-primary)"
                            : "var(--text-muted)",
                      }}
                    >
                      {col.nullPercent.toFixed(2)}%
                    </td>
                    <td className="cell-mono cell-right">
                      {col.uniqueCount.toLocaleString()}
                    </td>
                    <td className="cell-mono">{col.min}</td>
                    <td className="cell-mono">{col.max}</td>
                    <td className="cell-mono">{col.mean}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Data Quality Summary */}
      <div className="section">
        <div className="section-title">Data Quality Summary</div>
        <div className="card-grid">
          <div className="card">
            <div className="card-title">Total Nulls</div>
            <div className="card-value">
              {columnData
                .reduce((sum: number, c: ColumnProfile) => sum + c.nullCount, 0)
                .toLocaleString()}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Columns with Nulls</div>
            <div className="card-value">
              {columnData.filter((c: ColumnProfile) => c.nullCount > 0).length} /{" "}
              {columnData.length}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Highest Null Rate</div>
            <div
              className="card-value"
              style={{ color: "var(--risk-medium)", fontSize: "24px" }}
            >
              {Math.max(...columnData.map((c: ColumnProfile) => c.nullPercent)).toFixed(2)}%
            </div>
          </div>
          <div className="card">
            <div className="card-title">Completeness</div>
            <div
              className="card-value"
              style={{ color: "var(--status-accepted)", fontSize: "24px" }}
            >
              {(
                100 -
                columnData.reduce((s: number, c: ColumnProfile) => s + c.nullPercent, 0) /
                  columnData.length
              ).toFixed(1)}
              %
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
