"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { askDataset, getDatasetDetails, getDatasetProfile, runQuery } from "@/lib/api";
import type { Dataset, DatasetProfile, QueryResult } from "@/lib/types";

interface QueryPageProps {
  params: Promise<{ id: string }>;
}

const DEFAULT_SQL = "SELECT * FROM dataset LIMIT 100";
type QueryMode = "ask" | "sql";

export default function DatasetQueryPage({ params }: QueryPageProps) {
  const { id } = use(params);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [mode, setMode] = useState<QueryMode>("ask");
  const [sql, setSql] = useState(DEFAULT_SQL);
  const [question, setQuestion] = useState("");
  const [generatedSql, setGeneratedSql] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    getDatasetDetails(id)
      .then(setDataset)
      .catch(() => {});
    getDatasetProfile(id)
      .then(setProfile)
      .catch(() => {});
  }, [id]);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      if (mode === "ask") {
        const res = await askDataset(id, question);
        setGeneratedSql(res.sql);
        setResult(res);
      } else {
        setGeneratedSql(null);
        const res = await runQuery(id, sql);
        setResult(res);
      }
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Query failed");
    } finally {
      setRunning(false);
    }
  };

  const canRun = mode === "ask" ? question.trim().length > 0 : sql.trim().length > 0;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleRun();
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>SQL Query</h2>
        <p>
          {dataset ? (
            <>
              Querying <strong>{dataset.original_filename}</strong> —{" "}
              <Link href={`/datasets/${id}`} style={{ color: "var(--accent)" }}>
                Back to dataset
              </Link>
            </>
          ) : (
            "Loading dataset…"
          )}
        </p>
      </div>

      <div className="two-col" style={{ gridTemplateColumns: "3fr 1fr" }}>
        <div>
          <div className="section">
            <div className="section-title">Query</div>
            <div className="card">
              <div className="actions-row" style={{ marginBottom: "var(--space-md)" }}>
                <button
                  className={mode === "ask" ? "btn btn-primary" : "btn"}
                  onClick={() => setMode("ask")}
                >
                  Ask in plain English
                </button>
                <button
                  className={mode === "sql" ? "btn btn-primary" : "btn"}
                  onClick={() => setMode("sql")}
                >
                  Write SQL
                </button>
              </div>

              {mode === "ask" ? (
                <textarea
                  className="form-textarea"
                  style={{ minHeight: "160px" }}
                  placeholder='e.g. "Which vendor has the most transactions over $10,000?"'
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={handleKeyDown}
                  spellCheck={false}
                />
              ) : (
                <textarea
                  className="form-textarea"
                  style={{ fontFamily: "var(--font-mono)", minHeight: "160px" }}
                  value={sql}
                  onChange={(e) => setSql(e.target.value)}
                  onKeyDown={handleKeyDown}
                  spellCheck={false}
                />
              )}

              <div className="actions-row" style={{ marginTop: "var(--space-md)", alignItems: "center" }}>
                <button className="btn btn-primary" onClick={handleRun} disabled={running || !canRun}>
                  {running ? "Running…" : mode === "ask" ? "Ask" : "Run Query"}
                </button>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  {mode === "ask"
                    ? "AI translates your question into a read-only SQL query."
                    : "Read-only SELECT."}{" "}
                  Table name: <code>dataset</code>. Ctrl+Enter to run.
                </span>
              </div>
            </div>
          </div>

          {generatedSql && (
            <div className="section">
              <div className="section-title">Generated SQL</div>
              <div className="card">
                <pre
                  className="cell-mono"
                  style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "var(--font-mono)" }}
                >
                  {generatedSql}
                </pre>
              </div>
            </div>
          )}

          {error && (
            <div className="section">
              <div className="card" style={{ borderColor: "var(--risk-high)" }}>
                <p style={{ color: "var(--risk-high)" }}>{error}</p>
              </div>
            </div>
          )}

          {result && (
            <div className="section">
              <div className="section-title">
                Results ({result.row_count} row{result.row_count !== 1 ? "s" : ""})
              </div>
              <div className="card">
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        {result.columns.map((c) => (
                          <th key={c}>{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row, i) => (
                        <tr key={i}>
                          {result.columns.map((c) => (
                            <td key={c} className="cell-mono">
                              {row[c] === null || row[c] === undefined ? (
                                <span style={{ color: "var(--text-muted)" }}>NULL</span>
                              ) : (
                                String(row[c])
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                      {result.rows.length === 0 && (
                        <tr>
                          <td
                            colSpan={result.columns.length || 1}
                            style={{ textAlign: "center", color: "var(--text-muted)", padding: "var(--space-lg)" }}
                          >
                            Query returned no rows.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        <div>
          <div className="section">
            <div className="section-title">Available Columns</div>
            <div className="card">
              {profile ? (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Column</th>
                        <th>Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(profile.columns).map(([name, col]) => (
                        <tr key={name}>
                          <td className="cell-mono">{name}</td>
                          <td>
                            <span className="badge badge-low">{col.type}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p style={{ color: "var(--text-muted)" }}>Loading columns…</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
