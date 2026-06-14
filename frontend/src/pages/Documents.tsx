import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DocumentRow } from "../api/client";

export default function Documents() {
  const [docs, setDocs] = useState<DocumentRow[]>([]);
  const [err, setErr] = useState<string | null>(null);

  function load() {
    api.documents().then(setDocs).catch((e) => setErr(String(e)));
  }
  useEffect(load, []);

  async function remove(id: number) {
    if (!confirm("Delete this document and its observations?")) return;
    await api.deleteDocument(id);
    load();
  }

  if (err) return <p className="pill bad">{err}</p>;

  return (
    <div>
      <h2>Documents</h2>
      {docs.length === 0 ? (
        <p className="muted">No documents yet. <Link to="/upload">Upload one.</Link></p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>File</th><th>Lab</th><th>Collected</th><th>Status</th>
              <th>Results</th><th>Review</th><th></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td><Link to={`/documents/${d.id}`}>{d.original_name}</Link></td>
                <td>{d.lab_name ?? "—"}</td>
                <td>{d.collection_date ?? "—"}</td>
                <td>
                  <span className={`pill ${d.ingest_status === "parsed" ? "good" : d.ingest_status === "failed" ? "bad" : "neutral"}`}>
                    {d.ingest_status}
                  </span>
                </td>
                <td>{d.confirmed}/{d.observations_total}</td>
                <td>{d.needs_review > 0 ? <Link to="/review">{d.needs_review}</Link> : "—"}</td>
                <td><button className="danger" onClick={() => remove(d.id)}>Delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
