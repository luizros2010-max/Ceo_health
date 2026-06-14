import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type DocumentRow, type Observation } from "../api/client";

export default function DocumentDetail() {
  const { id } = useParams();
  const docId = Number(id);
  const [doc, setDoc] = useState<DocumentRow | null>(null);
  const [obs, setObs] = useState<Observation[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  function load() {
    api.document(docId).then((d) => { setDoc(d.document); setObs(d.observations); }).catch((e) => setErr(String(e)));
  }
  useEffect(load, [docId]);

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
        <button className="ghost" onClick={() => setEditing((e) => !e)}>
          {editing ? "Cancel" : "Edit details"}
        </button>
      </div>
      {editing && (
        <DocumentEditForm doc={doc} onSaved={() => { setEditing(false); load(); }} />
      )}
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

function DocumentEditForm({ doc, onSaved }: { doc: DocumentRow; onSaved: () => void }) {
  const [labName, setLabName] = useState(doc.lab_name ?? "");
  const [date, setDate] = useState(doc.collection_date ?? "");
  const [notes, setNotes] = useState(doc.notes ?? "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      // Editing the collection date re-dates this document's observations too.
      await api.patchDocument(doc.id, {
        lab_name: labName || null,
        collection_date: date || null,
        notes: notes || null,
      });
      onSaved();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel" style={{ marginBottom: 16 }}>
      <div className="row" style={{ marginBottom: 10 }}>
        <input
          placeholder="Lab name"
          value={labName}
          onChange={(e) => setLabName(e.target.value)}
          style={{ flex: 1 }}
        />
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>
      <input
        placeholder="Notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        style={{ width: "100%", marginBottom: 10 }}
      />
      <div className="row">
        <button onClick={save} disabled={busy}>Save</button>
        {err && <span className="pill bad">{err}</span>}
      </div>
    </div>
  );
}
