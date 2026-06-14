import { useEffect, useState } from "react";
import {
  api,
  type AnalysisPreview,
  type AnalysisResult,
  type Patient,
  type TrendFlag,
} from "../api/client";

const sevColor: Record<string, string> = {
  high: "bad",
  medium: "warn",
  watch: "warn",
  ok: "good",
};

export default function Insights() {
  const [keyOn, setKeyOn] = useState<boolean | null>(null);
  const [preview, setPreview] = useState<AnalysisPreview | null>(null);
  const [includeReports, setIncludeReports] = useState(true);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [running, setRunning] = useState(false);
  const [showShare, setShowShare] = useState(false);
  const [patient, setPatient] = useState<Patient | null>(null);

  function loadPreview() {
    api.analysisPreview({ include_reports: includeReports }).then(setPreview);
  }
  useEffect(() => {
    api.analysisStatus().then((s) => setKeyOn(s.api_key_configured));
    api.getPatient().then(setPatient).catch(() => {});
  }, []);
  useEffect(loadPreview, [includeReports]);

  async function savePatient(dob: string, sex: string) {
    const p = await api.patchPatient({ date_of_birth: dob || null, sex: sex || null });
    setPatient(p);
    loadPreview();
  }

  async function run() {
    setRunning(true);
    setResult(null);
    try {
      const r = await api.analysisRun({ include_reports: includeReports, question: question || null });
      setResult(r);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <h2>AI Insights <span className="pill neutral">Phase 4</span></h2>
      <p className="muted">
        A longevity-focused read of your trends. The factual <b>trend flags</b> below are computed
        locally (no AI). The AI summary is optional, runs only when you click it, and is sent only
        the minimal slice shown under “What will be shared”.
      </p>

      <PatientCard patient={patient} onSave={savePatient} />

      {/* Trend flags — deterministic */}
      <div className="panel">
        <h3>Trend flags</h3>
        {!preview ? <p className="muted">Loading…</p> : <FlagTable flags={preview.flags} />}
      </div>

      {/* What will be shared */}
      <div className="panel">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h3 style={{ margin: 0 }}>What will be shared with Claude</h3>
          <button className="ghost" onClick={() => setShowShare((s) => !s)}>
            {showShare ? "Hide JSON" : "Show exact JSON"}
          </button>
        </div>
        {preview && (
          <>
            <p className="muted" style={{ marginTop: 10 }}>
              {preview.summary.biomarkers} biomarkers · {preview.summary.data_points} data points ·{" "}
              {preview.summary.reports} report impressions ·{" "}
              age/sex: {preview.summary.shares_age_sex ? "included" : "not set"}. No names, IDs, raw
              text, or original files are ever sent.
            </p>
            <label className="row" style={{ fontSize: 13 }}>
              <input
                type="checkbox"
                checked={includeReports}
                onChange={(e) => setIncludeReports(e.target.checked)}
              />
              include imaging/report impressions
            </label>
            {showShare && (
              <pre className="mono" style={{ maxHeight: 280, overflow: "auto", marginTop: 10, background: "var(--panel-2)", padding: 12, borderRadius: 8 }}>
                {JSON.stringify(preview.slice, null, 2)}
              </pre>
            )}
          </>
        )}
      </div>

      {/* Run */}
      <div className="panel">
        <h3>Ask the AI</h3>
        {keyOn === false && (
          <p className="pill warn">
            No ANTHROPIC_API_KEY set — set it in .env to enable the AI summary. The trend flags above
            work without it.
          </p>
        )}
        <textarea
          placeholder="Optional: a focus question, e.g. 'What should I watch on my lipids and cardiovascular risk?'"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          style={{ width: "100%", background: "var(--panel-2)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 8, padding: 10, fontSize: 13 }}
        />
        <div style={{ marginTop: 10 }}>
          <button onClick={run} disabled={running || keyOn === false}>
            {running ? "Analyzing…" : "Run AI analysis"}
          </button>
        </div>
        {result && (
          result.ok ? (
            <div style={{ marginTop: 14 }}>
              <Markdown text={result.insights || ""} />
              <p className="muted" style={{ fontSize: 11, marginTop: 12 }}>
                Informational only — not a diagnosis or medical advice. Model: {result.model}
              </p>
            </div>
          ) : (
            <p className="pill bad" style={{ marginTop: 12 }}>Error: {result.error}</p>
          )
        )}
      </div>
    </div>
  );
}

function FlagTable({ flags }: { flags: TrendFlag[] }) {
  if (flags.length === 0) return <p className="muted">No biomarker data yet.</p>;
  return (
    <table>
      <thead>
        <tr><th>Biomarker</th><th>Latest</th><th>Range</th><th>Trend</th><th>Points</th><th>Flag</th></tr>
      </thead>
      <tbody>
        {flags.map((f) => (
          <tr key={f.biomarker}>
            <td>{f.biomarker}</td>
            <td className="mono">{f.latest} {f.unit} <span className="muted">({f.latest_date})</span></td>
            <td>{f.in_range === false ? <span className="pill bad">out</span> : f.in_range ? <span className="pill good">in</span> : "—"}</td>
            <td>{f.direction === "rising" ? "↑ rising" : f.direction === "falling" ? "↓ falling" : f.direction === "stable" ? "→ stable" : "—"}</td>
            <td>{f.n_points}</td>
            <td><span className={`pill ${sevColor[f.severity]}`}>{f.severity}</span></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PatientCard({ patient, onSave }: { patient: Patient | null; onSave: (dob: string, sex: string) => void }) {
  const [dob, setDob] = useState("");
  const [sex, setSex] = useState("");
  useEffect(() => {
    if (patient) { setDob(patient.date_of_birth || ""); setSex(patient.sex || ""); }
  }, [patient]);
  return (
    <div className="panel">
      <h3>Profile (for age/sex context)</h3>
      <div className="row">
        <label className="muted" style={{ fontSize: 13 }}>Date of birth <input type="date" value={dob} onChange={(e) => setDob(e.target.value)} /></label>
        <label className="muted" style={{ fontSize: 13 }}>Sex{" "}
          <select value={sex} onChange={(e) => setSex(e.target.value)}>
            <option value="">—</option>
            <option value="male">male</option>
            <option value="female">female</option>
          </select>
        </label>
        <button className="ghost" onClick={() => onSave(dob, sex)}>Save</button>
      </div>
    </div>
  );
}

// Minimal Markdown renderer (headings, bold, bullet lists, paragraphs).
function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const out: JSX.Element[] = [];
  let list: string[] = [];
  const flush = () => {
    if (list.length) {
      out.push(<ul key={out.length}>{list.map((li, i) => <li key={i} dangerouslySetInnerHTML={{ __html: inline(li) }} />)}</ul>);
      list = [];
    }
  };
  lines.forEach((ln) => {
    if (/^#{1,6}\s/.test(ln)) {
      flush();
      const lvl = ln.match(/^#+/)![0].length;
      const txt = ln.replace(/^#+\s/, "");
      out.push(<div key={out.length} style={{ fontWeight: 600, fontSize: lvl <= 2 ? 16 : 14, marginTop: 12 }} dangerouslySetInnerHTML={{ __html: inline(txt) }} />);
    } else if (/^\s*[-*]\s+/.test(ln)) {
      list.push(ln.replace(/^\s*[-*]\s+/, ""));
    } else if (ln.trim() === "") {
      flush();
    } else {
      flush();
      out.push(<p key={out.length} style={{ margin: "6px 0" }} dangerouslySetInnerHTML={{ __html: inline(ln) }} />);
    }
  });
  flush();
  return <div style={{ fontSize: 14, lineHeight: 1.55 }}>{out}</div>;
}
function inline(s: string) {
  return s
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/\*(.+?)\*/g, "<i>$1</i>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}
