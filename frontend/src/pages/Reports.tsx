import { useEffect, useState } from "react";
import { api, type NarrativeReport, type ReportListItem } from "../api/client";

export default function Reports() {
  const [items, setItems] = useState<ReportListItem[]>([]);
  const [open, setOpen] = useState<Record<number, NarrativeReport>>({});
  const [showForm, setShowForm] = useState(false);

  function load() {
    api.reports().then(setItems);
  }
  useEffect(load, []);

  async function toggle(id: number) {
    if (open[id]) {
      setOpen((o) => {
        const n = { ...o };
        delete n[id];
        return n;
      });
    } else {
      const full = await api.report(id);
      setOpen((o) => ({ ...o, [id]: full }));
    }
  }

  async function remove(id: number) {
    if (!confirm("Delete this report?")) return;
    await api.deleteReport(id);
    load();
  }

  return (
    <div>
      <h2>Imaging & Reports</h2>
      <p className="muted">
        Narrative reports — MRI, echocardiogram, endoscopy, specialist notes — that have
        findings as text rather than trendable numbers. They live here alongside your
        biomarker timelines.
      </p>

      <button onClick={() => setShowForm((s) => !s)} style={{ marginBottom: 14 }}>
        {showForm ? "Cancel" : "+ Add report"}
      </button>
      {showForm && <ReportForm onSaved={() => { setShowForm(false); load(); }} />}

      {items.length === 0 ? (
        <p className="muted">No reports yet.</p>
      ) : (
        items.map((r) => (
          <div className="panel" key={r.id}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div>
                <strong>{r.title}</strong>{" "}
                {r.category && <span className="pill neutral">{r.category}</span>}
                <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                  {r.report_date ?? "no date"}{r.facility ? ` · ${r.facility}` : ""}
                </div>
              </div>
              <div className="row">
                <button className="ghost" onClick={() => toggle(r.id)}>
                  {open[r.id] ? "Hide" : "View"}
                </button>
                <button className="danger" onClick={() => remove(r.id)}>Delete</button>
              </div>
            </div>
            {open[r.id] ? (
              <>
                {open[r.id].impression && (
                  <p style={{ marginTop: 12 }}><strong>Impression:</strong> {open[r.id].impression}</p>
                )}
                <pre style={{ whiteSpace: "pre-wrap", marginTop: 10, fontSize: 13, lineHeight: 1.5 }}>
                  {open[r.id].body}
                </pre>
              </>
            ) : (
              <p className="muted" style={{ marginTop: 10, fontSize: 13 }}>{r.snippet}</p>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function ReportForm({ onSaved }: { onSaved: () => void }) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [date, setDate] = useState("");
  const [facility, setFacility] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      await api.createReport({
        title,
        category: category || null,
        report_date: date || null,
        facility: facility || null,
        body,
      });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="row" style={{ marginBottom: 10 }}>
        <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} style={{ flex: 1 }} />
        <input placeholder="Category (MRI, Echo…)" value={category} onChange={(e) => setCategory(e.target.value)} />
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <input placeholder="Facility" value={facility} onChange={(e) => setFacility(e.target.value)} />
      </div>
      <textarea
        placeholder="Findings / report text"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={6}
        style={{ width: "100%", background: "var(--panel-2)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 8, padding: 10, fontSize: 13 }}
      />
      <div style={{ marginTop: 10 }}>
        <button onClick={submit} disabled={busy || !title}>Save report</button>
      </div>
    </div>
  );
}
