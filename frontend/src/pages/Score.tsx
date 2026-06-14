import { useEffect, useState } from "react";
import { api, type HealthScore, type ScoreDomain } from "../api/client";

function color(s: number) {
  return s >= 85 ? "var(--good)" : s >= 70 ? "var(--accent)" : s >= 60 ? "var(--warn)" : "var(--bad)";
}

export default function Score() {
  const [data, setData] = useState<HealthScore | null>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api.healthScore().then(setData);
  }, []);

  if (!data) return <p className="muted">Loading…</p>;
  const o = data.overall;
  if (o.score == null) return <p className="muted">No biomarker data yet to score.</p>;

  return (
    <div>
      <h2>Health Score <span className="pill neutral">vs age-peers</span></h2>

      <div className="panel" style={{ display: "flex", gap: 24, alignItems: "center" }}>
        <Gauge score={o.score} />
        <div>
          <div style={{ fontSize: 22, fontWeight: 600, textTransform: "capitalize" }}>{o.label}</div>
          <div className="muted">{o.band}</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
            {data.subject.age != null ? `age ${data.subject.age}` : "age not set"}
            {data.subject.sex ? ` · ${data.subject.sex}` : ""} · as of {data.as_of}
          </div>
        </div>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>By domain <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>(lowest first)</span></h3>
        {data.domains.map((d) => (
          <DomainRow key={d.name} d={d} open={!!open[d.name]} onToggle={() => setOpen((s) => ({ ...s, [d.name]: !s[d.name] }))} />
        ))}
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>How this is computed</h3>
        <ul className="muted" style={{ fontSize: 12.5, lineHeight: 1.6 }}>
          {data.caveats.map((c, i) => <li key={i}>{c}</li>)}
        </ul>
      </div>
    </div>
  );
}

function Gauge({ score }: { score: number }) {
  const r = 46, c = 2 * Math.PI * r, off = c * (1 - score / 100);
  return (
    <svg width="120" height="120" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r={r} fill="none" stroke="var(--border)" strokeWidth="10" />
      <circle cx="60" cy="60" r={r} fill="none" stroke={color(score)} strokeWidth="10"
        strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}
        transform="rotate(-90 60 60)" />
      <text x="60" y="60" textAnchor="middle" fontSize="30" fontWeight="700" fill="var(--text)">{Math.round(score)}</text>
      <text x="60" y="80" textAnchor="middle" fontSize="11" fill="var(--muted)">/ 100</text>
    </svg>
  );
}

function DomainRow({ d, open, onToggle }: { d: ScoreDomain; open: boolean; onToggle: () => void }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="row" style={{ justifyContent: "space-between", cursor: "pointer" }} onClick={onToggle}>
        <span>{open ? "▾" : "▸"} {d.name} <span className="muted" style={{ fontSize: 11 }}>· weight {(d.weight * 100).toFixed(0)}%</span></span>
        <span style={{ fontWeight: 600, color: color(d.score) }}>{d.score}</span>
      </div>
      <div style={{ height: 8, background: "var(--panel-2)", borderRadius: 6, overflow: "hidden", marginTop: 4 }}>
        <div style={{ width: `${d.score}%`, height: "100%", background: color(d.score) }} />
      </div>
      {open && (
        <table style={{ marginTop: 8 }}>
          <tbody>
            {d.markers.map((m) => (
              <tr key={m.slug}>
                <td style={{ width: "45%" }}>{m.biomarker}</td>
                <td className="mono">{m.value} {m.unit}</td>
                <td style={{ width: 90 }}>
                  <div style={{ height: 6, background: "var(--panel-2)", borderRadius: 4 }}>
                    <div style={{ width: `${m.score}%`, height: "100%", background: color(m.score), borderRadius: 4 }} />
                  </div>
                </td>
                <td style={{ color: color(m.score), fontWeight: 600, width: 40 }}>{Math.round(m.score)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
