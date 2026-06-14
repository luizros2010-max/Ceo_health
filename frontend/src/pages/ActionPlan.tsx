import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type ActionPlan, type PlanLever } from "../api/client";

const leverIcon: Record<string, string> = {
  workout: "🏋️ Workout",
  nutrition: "🥗 Nutrition",
  lifestyle: "🌙 Lifestyle",
  medical: "🩺 Discuss with physician",
};

export default function ActionPlanPage() {
  const [plan, setPlan] = useState<ActionPlan | null>(null);
  const [keyOn, setKeyOn] = useState(false);
  const [ai, setAi] = useState("");
  const [aiErr, setAiErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.actionPlan().then(setPlan);
    api.analysisStatus().then((s) => setKeyOn(s.api_key_configured));
  }, []);

  async function draft() {
    setBusy(true); setAi(""); setAiErr(null);
    try {
      const res = await fetch("/api/analysis/plan/stream", { method: "POST" });
      if (!res.ok || !res.body) {
        const j = await res.json().catch(() => ({ error: res.statusText }));
        setAiErr(j.error || "error"); return;
      }
      const reader = res.body.getReader(); const dec = new TextDecoder();
      for (;;) { const { done, value } = await reader.read(); if (done) break; setAi((s) => s + dec.decode(value, { stream: true })); }
    } finally { setBusy(false); }
  }

  if (!plan) return <p className="muted">Loading…</p>;
  const o = plan.overall;

  return (
    <div>
      <h2>Action Plan</h2>
      <p className="muted">
        Auto-generated from your score gaps. Current score <b>{o.score}/100</b> ({o.label}). Targets
        below are the values that would earn full marks — close them to raise your score.
      </p>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Targets (biggest gaps first)</h3>
        {plan.targets.length === 0 ? <p className="muted">All tracked markers are near-optimal.</p> : (
          <table>
            <thead><tr><th>Marker</th><th>Now</th><th>Goal</th><th>Domain</th><th>Score</th></tr></thead>
            <tbody>
              {plan.targets.map((t) => (
                <tr key={t.slug}>
                  <td>{t.biomarker}</td>
                  <td className="mono">{t.current} {t.unit}</td>
                  <td><b>{t.direction} {t.target} {t.unit}</b></td>
                  <td className="muted">{t.domain}</td>
                  <td><span className={`pill ${t.current_score >= 70 ? "warn" : "bad"}`}>{Math.round(t.current_score)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {plan.levers.map((lev) => <LeverCard key={lev.domain} lev={lev} />)}

      {plan.missing_trackers.length > 0 && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Start tracking these</h3>
          <p className="muted">
            These risk factors aren't in your data yet but feed the score once added. Enter them on the{" "}
            <Link to="/upload">Upload page → Manual entry</Link>:
          </p>
          <div className="row">
            {plan.missing_trackers.map((m) => <span key={m.slug} className="pill neutral">{m.label}</span>)}
          </div>
        </div>
      )}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>AI-drafted plan</h3>
        {!keyOn && <p className="pill warn">Set ANTHROPIC_API_KEY to draft a narrative plan. The targets and levers above work without it.</p>}
        <button onClick={draft} disabled={busy || !keyOn}>{busy ? "Drafting…" : "Draft my plan with AI"}</button>
        {aiErr && <p className="pill bad" style={{ marginTop: 10 }}>Error: {aiErr}</p>}
        {ai && (
          <div style={{ marginTop: 14, whiteSpace: "pre-wrap", fontSize: 13.5, lineHeight: 1.55 }}>
            {ai}{busy && <span className="muted">▍</span>}
          </div>
        )}
      </div>

      <p className="muted" style={{ fontSize: 11 }}>{plan.note}</p>
    </div>
  );
}

function LeverCard({ lev }: { lev: PlanLever }) {
  return (
    <div className="panel">
      <h3 style={{ marginTop: 0 }}>
        {lev.domain} <span className="muted" style={{ fontSize: 12, fontWeight: 400 }}>· score {lev.score}</span>
      </h3>
      {(["medical", "nutrition", "workout", "lifestyle"] as const).map((k) =>
        lev[k] && lev[k]!.length ? (
          <div key={k} style={{ marginBottom: 8 }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{leverIcon[k]}</div>
            <ul style={{ margin: "4px 0", fontSize: 13, lineHeight: 1.5 }}>
              {lev[k]!.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          </div>
        ) : null,
      )}
    </div>
  );
}
