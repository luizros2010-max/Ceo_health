import { useEffect, useState } from "react";
import {
  api,
  type AnalysisPreview,
  type Overview,
  type Patient,
  type ReportListItem,
} from "../api/client";

const sevColor: Record<string, string> = { high: "bad", medium: "warn", watch: "warn", ok: "good" };

export default function Report() {
  const [ov, setOv] = useState<Overview | null>(null);
  const [pv, setPv] = useState<AnalysisPreview | null>(null);
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [keyOn, setKeyOn] = useState(false);
  const [ai, setAi] = useState("");
  const [aiBusy, setAiBusy] = useState(false);

  useEffect(() => {
    api.overview().then(setOv);
    api.analysisPreview({ include_reports: true }).then(setPv);
    api.reports().then(setReports);
    api.getPatient().then(setPatient).catch(() => {});
    api.analysisStatus().then((s) => setKeyOn(s.api_key_configured));
  }, []);

  async function addAI() {
    setAiBusy(true); setAi("");
    try {
      const res = await fetch("/api/analysis/stream", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ include_reports: true }),
      });
      if (!res.ok || !res.body) { setAi("(AI summary unavailable)"); return; }
      const reader = res.body.getReader(); const dec = new TextDecoder();
      for (;;) { const { done, value } = await reader.read(); if (done) break; setAi((s) => s + dec.decode(value, { stream: true })); }
    } finally { setAiBusy(false); }
  }

  if (!ov || !pv) return <p className="muted">Loading…</p>;

  const flags = pv.flags.filter((f) => f.severity !== "ok");
  const today = new Date().toISOString().slice(0, 10);
  const cats = Array.from(new Set(ov.cards.map((c) => c.category || "Other")));

  return (
    <div className="report">
      <div className="no-print row" style={{ justifyContent: "space-between", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Doctor Report</h2>
        <div className="row">
          {keyOn && <button className="ghost" onClick={addAI} disabled={aiBusy}>{aiBusy ? "Adding AI summary…" : "Add AI summary"}</button>}
          <button onClick={() => window.print()}>Print / Save as PDF</button>
        </div>
      </div>

      <h1>Health Summary Report</h1>
      <div className="sub">
        {patient?.name || "Patient"}
        {pv.slice.subject.age != null ? ` · age ${pv.slice.subject.age}` : ""}
        {pv.slice.subject.sex ? ` · ${pv.slice.subject.sex}` : ""}
        {" · generated "}{today}
        {ov.stats.date_span.from ? ` · data ${ov.stats.date_span.from} → ${ov.stats.date_span.to}` : ""}
        {` · ${ov.stats.observations} results`}
      </div>

      <section>
        <h3>Priority flags</h3>
        {flags.length === 0 ? <p className="muted">No out-of-range or adverse-trend markers.</p> : (
          <table>
            <thead><tr><th>Biomarker</th><th>Latest</th><th>Status</th><th>Trend</th><th>Flag</th></tr></thead>
            <tbody>
              {flags.map((f) => (
                <tr key={f.biomarker}>
                  <td>{f.biomarker}</td>
                  <td>{f.latest} {f.unit} <span className="muted">({f.latest_date})</span></td>
                  <td>{f.in_range === false ? "out of range" : "in range"}</td>
                  <td>{f.direction}</td>
                  <td><span className={`pill ${sevColor[f.severity]}`}>{f.severity}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h3>All biomarkers — latest values</h3>
        {cats.map((cat) => (
          <div key={cat}>
            <div className="cat">{cat}</div>
            <table>
              <tbody>
                {ov.cards.filter((c) => (c.category || "Other") === cat).map((c) => (
                  <tr key={c.slug}>
                    <td style={{ width: "40%" }}>{c.display_name}</td>
                    <td>{c.value} {c.unit}</td>
                    <td>ref {c.ref_low ?? "–"}–{c.ref_high ?? "–"}</td>
                    <td>{c.in_range === false ? <span className="pill bad">out</span> : c.in_range ? <span className="pill good">in</span> : "—"}</td>
                    <td className="muted">{c.last_measured}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </section>

      {reports.length > 0 && (
        <section>
          <h3>Imaging & reports</h3>
          {reports.map((r) => (
            <p key={r.id} style={{ margin: "6px 0", fontSize: 12 }}>
              <b>{r.report_date} · {r.title}</b>{r.category ? ` (${r.category})` : ""}<br />
              <span className="muted">{r.impression || r.snippet}</span>
            </p>
          ))}
        </section>
      )}

      {ai && (
        <section>
          <h3>AI summary</h3>
          <div style={{ whiteSpace: "pre-wrap", fontSize: 12.5, lineHeight: 1.5 }}>{ai}</div>
        </section>
      )}

      <p className="disclaimer">
        This report is generated from self-tracked data for informational purposes and to support a
        conversation with a healthcare professional. It is not a diagnosis or medical advice.
        Reference ranges are catalog defaults and may differ from the issuing laboratory.
      </p>
    </div>
  );
}
