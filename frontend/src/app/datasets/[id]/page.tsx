import Link from "next/link";
import { getDatasetDetails, getDatasetProfile, getDatasetSchema, getFindings } from "@/lib/api";
import { datasetStatusBadgeClass, formatDateTime } from "@/lib/format";
import type { ColumnProfileEntry, Dataset, DatasetProfile, SchemaMapping } from "@/lib/types";
import FindingsAccordion from "@/components/FindingsAccordion";
import DatasetStatusPanel from "@/components/DatasetStatusPanel";

interface DatasetProfilePageProps {
  params: Promise<{ id: string }>;
}

const ROLE_LABELS: Record<string, string> = {
  vendor: "vendor",
  amount: "transaction amount",
  date: "posting date",
  invoice_no: "invoice number",
};

function describeSubjectMatter(schema: SchemaMapping | null): string | null {
  if (!schema || Object.keys(schema.mapping).length === 0) return null;
  const parts = Object.entries(schema.mapping).map(
    ([role, column]) => `${ROLE_LABELS[role] ?? role} (column "${column}")`
  );
  return `This looks like transaction or journal-entry data. Based on its columns, the agent identified: ${parts.join(
    ", "
  )}.`;
}

function describeStats(profile: DatasetProfile | null, dataset: Dataset): string {
  const rows = profile?.row_count ?? dataset.row_count;
  const cols = profile?.column_count ?? dataset.column_count;
  if (rows == null || cols == null) return "Stats are not available yet.";

  let quality = "";
  if (profile) {
    if (profile.completeness_pct >= 99) {
      quality = " It's essentially complete, with almost no missing values.";
    } else if (profile.completeness_pct >= 90) {
      quality = ` It's mostly complete (${profile.completeness_pct}% filled in), with a small number of missing values.`;
    } else {
      quality = ` It's only ${profile.completeness_pct}% complete — a meaningful number of cells are missing.`;
    }
  }
  return `It has ${rows.toLocaleString()} rows and ${cols} columns.${quality}`;
}

function columnDetail(entry: ColumnProfileEntry, field: "min" | "max"): string {
  if (entry.type === "numeric") {
    const v = entry[field];
    return v === undefined ? "—" : v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  if (entry.type === "date") {
    const v = field === "min" ? entry.min_date : entry.max_date;
    return v ?? "—";
  }
  return "—";
}

export default async function DatasetProfilePage({ params }: DatasetProfilePageProps) {
  const { id } = await params;

  let dataset: Dataset;
  try {
    dataset = await getDatasetDetails(id);
  } catch {
    return (
      <div className="page-header">
        <h2>Dataset Not Found</h2>
        <p>
          No dataset with ID {id}.{" "}
          <Link href="/datasets" style={{ color: "var(--accent)" }}>
            Return to Datasets
          </Link>
        </p>
      </div>
    );
  }

  const [profileResult, schemaResult, findingsResult] = await Promise.allSettled([
    getDatasetProfile(id),
    getDatasetSchema(id),
    getFindings(id),
  ]);

  const profile = profileResult.status === "fulfilled" ? profileResult.value : null;
  const schema = schemaResult.status === "fulfilled" ? schemaResult.value : null;
  const findings = findingsResult.status === "fulfilled" ? findingsResult.value : [];

  const isComplete = dataset.status === "complete";
  const subjectMatter = describeSubjectMatter(schema);

  return (
    <>
      <div className="page-header">
        <h2>{dataset.original_filename}</h2>
        <p>Dataset profile and column-level statistics</p>
      </div>

      {/* Status / progress banner + actions, live-updating while analysis runs */}
      <DatasetStatusPanel dataset={dataset} />

      {/* About This Dataset — plain language */}
      {isComplete && (
        <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
          <div className="section-title">About This Dataset</div>
          <p style={{ color: "var(--text-primary)", lineHeight: "1.6", marginBottom: "var(--space-md)" }}>
            {describeStats(profile, dataset)}
          </p>
          {subjectMatter && (
            <p style={{ color: "var(--text-primary)", lineHeight: "1.6", marginBottom: "var(--space-md)" }}>
              {subjectMatter}
            </p>
          )}
          {dataset.analysis_summary && (
            <p style={{ color: "var(--text-secondary)", lineHeight: "1.6" }}>
              <strong style={{ color: "var(--text-primary)" }}>Audit summary: </strong>
              {dataset.analysis_summary}
            </p>
          )}
        </div>
      )}

      {/* Dataset Summary Card */}
      <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
        <div className="section-title">Dataset Summary</div>
        <div className="table-container">
          <table>
            <tbody>
              <tr>
                <td style={{ color: "var(--text-secondary)", width: "200px", fontWeight: 600, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Dataset ID
                </td>
                <td className="cell-mono">{dataset.id}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--text-secondary)", fontWeight: 600, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Filename
                </td>
                <td className="cell-mono">{dataset.original_filename}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--text-secondary)", fontWeight: 600, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Row Count
                </td>
                <td className="cell-mono">{dataset.row_count?.toLocaleString() ?? "—"}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--text-secondary)", fontWeight: 600, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Column Count
                </td>
                <td className="cell-mono">{dataset.column_count ?? "—"}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--text-secondary)", fontWeight: 600, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Uploaded
                </td>
                <td className="cell-mono">{formatDateTime(dataset.created_at)}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--text-secondary)", fontWeight: 600, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Status
                </td>
                <td>
                  <span className={`badge ${datasetStatusBadgeClass(dataset.status)}`}>{dataset.status}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Column Profiles */}
      {profile && (
        <>
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
                    {Object.entries(profile.columns).map(([name, col]) => (
                      <tr key={name}>
                        <td className="cell-mono">{name}</td>
                        <td>
                          <span className="badge badge-low">{col.type}</span>
                        </td>
                        <td className="cell-mono cell-right">{col.null_count.toLocaleString()}</td>
                        <td
                          className="cell-mono cell-right"
                          style={{
                            color:
                              col.null_pct > 5
                                ? "var(--risk-medium)"
                                : col.null_pct > 0
                                ? "var(--text-primary)"
                                : "var(--text-muted)",
                          }}
                        >
                          {col.null_pct.toFixed(2)}%
                        </td>
                        <td className="cell-mono cell-right">{col.unique_count.toLocaleString()}</td>
                        <td className="cell-mono">{columnDetail(col, "min")}</td>
                        <td className="cell-mono">{columnDetail(col, "max")}</td>
                        <td className="cell-mono">
                          {col.mean !== undefined ? col.mean.toFixed(2) : "—"}
                        </td>
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
                  {Object.values(profile.columns)
                    .reduce((sum, c) => sum + c.null_count, 0)
                    .toLocaleString()}
                </div>
              </div>
              <div className="card">
                <div className="card-title">Columns with Nulls</div>
                <div className="card-value">
                  {Object.values(profile.columns).filter((c) => c.null_count > 0).length} /{" "}
                  {Object.keys(profile.columns).length}
                </div>
              </div>
              <div className="card">
                <div className="card-title">Highest Null Rate</div>
                <div className="card-value" style={{ color: "var(--risk-medium)", fontSize: "24px" }}>
                  {Math.max(0, ...Object.values(profile.columns).map((c) => c.null_pct)).toFixed(2)}%
                </div>
              </div>
              <div className="card">
                <div className="card-title">Completeness</div>
                <div className="card-value" style={{ color: "var(--status-accepted)", fontSize: "24px" }}>
                  {profile.completeness_pct.toFixed(1)}%
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Findings, grouped by type */}
      {isComplete && (
        <div className="section">
          <div className="section-title">
            Findings ({findings.length})
          </div>
          <FindingsAccordion findings={findings} />
        </div>
      )}
    </>
  );
}
