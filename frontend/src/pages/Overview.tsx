import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Line,
  LineChart,
  ResponsiveContainer,
} from "recharts";
import { api, type Overview as OverviewData } from "../api/client";

export default function Overview() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.overview().then(setData).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <p className="pill bad">{err}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  const span = data.stats.date_span;

  return (
    <div>
      <h2>Overview</h2>
      <div className="stats">
        <div className="stat"><div className="n">{data.stats.documents}</div><div className="l">Documents</div></div>
        <div className="stat"><div className="n">{data.stats.observations}</div><div className="l">Confirmed results</div></div>
        <div className="stat"><div className="n">{data.stats.needs_review}</div><div className="l">Needs review</div></div>
        <div className="stat">
          <div className="n">{span.from ? `${span.from.slice(0, 4)}–${span.to?.slice(0, 4)}` : "—"}</div>
          <div className="l">Date span</div>
        </div>
      </div>

      {data.cards.length === 0 ? (
        <div className="panel">
          <p>No confirmed biomarkers yet.</p>
          <p className="muted">
            <Link to="/upload">Upload a lab PDF</Link> or add a value manually, then confirm it in{" "}
            <Link to="/review">Review</Link>.
          </p>
        </div>
      ) : (
        <div className="cards">
          {data.cards.map((c) => (
            <Link to={`/biomarker/${c.slug}`} className="card" key={c.slug} style={{ color: "inherit" }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="name">{c.display_name}</span>
                <span className={`pill ${c.in_range === false ? "bad" : c.in_range ? "good" : "neutral"}`}>
                  {c.in_range === false ? "out of range" : c.in_range ? "in range" : "—"}
                </span>
              </div>
              <div className="val">
                {c.value}
                <small> {c.unit}</small>
              </div>
              {c.sparkline.length > 1 && (
                <ResponsiveContainer width="100%" height={36}>
                  <LineChart data={c.sparkline}>
                    <Line type="monotone" dataKey="value" stroke="#4f8cff" strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
              <div className="meta">
                last: {c.last_measured}
                {c.ref_low != null || c.ref_high != null
                  ? ` · ref ${c.ref_low ?? "–"}–${c.ref_high ?? "–"}`
                  : ""}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
