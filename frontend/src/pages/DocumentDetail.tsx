import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type DocumentRow, type Observation } from "../api/client";

export default function DocumentDetail() {
  const { id } = useParams();
  const docId = Number(id);
  const [doc, setDoc] = useState<DocumentRow | null>(null);
  const [obs, setObs] = useState<Observation[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.document(docId).then((d) => { setDoc(d.document); setObs(d.observations); }).catch((e) => setErr(String(e)));
  }, [docId]);

  if (err) return <p className="pill bad">{err}</p>;
  if (!doc) return <p className="muted">Loading…</p>;

  const isPdf = doc.source_type === "pdf";

  return (
    <div>
      <Link to="/documents">← Documents</Link>
      <h2>{doc.original_name}</h2>
      <div className="row muted" style={{ marginBottom: 16 }}>
        <span>Lab: {doc.lab_name ?? "—"}</span>
        <span>Collected: {doc.collection_date ?? "—"}</span>
        <span className={`pill ${doc.ingest_status === "parsed" ? "good" : "neutral"}`}>{doc.ingest_status}</span>
      </div>
      {doc.notes && <p className="pill warn">{doc.notes}</p>}

      <div className="split">
        <div className="panel">
          <h3>Original</h3>
          {isPdf ? (
            <iframe className="viewer" src={`/api/documents/${docId}/file`} title="original" />
          ) : doc.source_type === "scan" ? (
            <img src={`/api/documents/${docId}/file`} style={{ maxWidth: "100%", borderRadius: 8 }} />
          ) : (
            <p className="muted">No file (manual entry).</p>
          )}
        </div>
        <div className="panel">
          <h3>Parsed observations ({obs.length})</h3>
          <table>
            <thead>
              <tr><th>Raw name</th><th>Value</th><th>Normalized</th><th>Conf</th><th>Status</th></tr>
            </thead>
            <tbody>
              {obs.map((o) => (
                <tr key={o.id}>
                  <td>{o.raw_name}</td>
                  <td className="mono">{o.raw_value} {o.raw_unit}</td>
                  <td>{o.value_num != null ? `${o.value_num} ${o.canonical_unit ?? ""}` : "—"}</td>
                  <td>{(o.mapping_confidence * 100).toFixed(0)}%</td>
                  <td>
                    <span className={`pill ${o.status === "confirmed" ? "good" : o.status === "rejected" ? "bad" : "warn"}`}>
                      {o.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
