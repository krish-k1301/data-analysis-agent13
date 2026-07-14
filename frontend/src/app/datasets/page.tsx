"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDatasets } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Dataset } from "@/lib/types";
import DatasetProgress from "@/components/DatasetProgress";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    return getDatasets()
      .then((d) => {
        setDatasets(d);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <>
      <div className="page-header">
        <h2>Datasets</h2>
        <p>All uploaded datasets and their analysis status</p>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Filename</th>
                <th>Rows</th>
                <th>Columns</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "var(--space-xl)", color: "var(--text-muted)" }}>
                    Loading...
                  </td>
                </tr>
              )}
              {!loading && datasets.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "var(--space-xl)", color: "var(--text-muted)" }}>
                    No datasets found.{" "}
                    <Link href="/" style={{ color: "var(--accent)" }}>
                      Upload one to get started
                    </Link>
                    .
                  </td>
                </tr>
              )}
              {!loading &&
                datasets.map((ds) => (
                  <tr key={ds.id} className="link-row">
                    <td className="cell-mono">{ds.id}</td>
                    <td>
                      <Link href={`/datasets/${ds.id}`} style={{ color: "var(--text-primary)" }}>
                        {ds.original_filename}
                      </Link>
                    </td>
                    <td className="cell-mono cell-right">{ds.row_count?.toLocaleString() ?? "—"}</td>
                    <td className="cell-mono cell-right">{ds.column_count ?? "—"}</td>
                    <td>
                      <DatasetProgress
                        datasetId={ds.id}
                        initialStatus={ds.status}
                        initialProgressPct={ds.progress_pct}
                        initialCurrentStep={ds.current_step}
                        initialError={ds.error}
                        onSettled={refresh}
                      />
                    </td>
                    <td className="cell-mono">{formatDateTime(ds.created_at)}</td>
                    <td className="cell-right">
                      <Link href={`/datasets/${ds.id}/query`}>
                        <button
                          className="btn btn-primary"
                          style={{ fontSize: "11px", padding: "4px 10px" }}
                          disabled={ds.status !== "complete"}
                        >
                          Query
                        </button>
                      </Link>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
