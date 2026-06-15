import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Biomarker, type Timeline } from "../api/client";
import TrendChart from "../components/TrendChart";
import MultiSourceTrendChart from "../components/MultiSourceTrendChart";

export default function BiomarkerTimeline() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [biomarkers, setBiomarkers] = useState<Biomarker[]>([]);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [source, setSource] = useState<string>("all");
  const [overlay, setOverlay] = useState(false);

  useEffect(() => {
    api.biomarkers().then((b) => {
      setBiomarkers(b);
      if (!slug && b.length) {
        const first = b.find((x) => x.has_data) ?? b[0];
        navigate(`/biomarker/${first.slug}`, { replace: true });
      }
    });
  }, [slug, navigate]);

  useEffect(() => {
    setSource("all");
    if (slug) api.timeline(slug).then(setTimeline).catch(() => setTimeline(null));
  }, [slug]);

  const sources = timeline ? Array.from(new Set(timeline.points.map((p) => p.source))) : [];
  const filtered: Timeline | null = timeline
    ? { ...timeline, points: source === "all" ? timeline.points : timeline.points.filter((p) => p.source === source) }
    : null;

  return (
    <div>
      <h2>Biomarker Timeline</h2>
      <div className="row" style={{ marginBottom: 18 }}>
        <select value={slug ?? ""} onChange={(e) => navigate(`/biomarker/${e.target.value}`)}>
          {biomarkers.map((b) => (
            <option key={b.slug} value={b.slug}>
              {b.display_name}{b.has_data ? "" : "  (no data)"}
            </option>
          ))}
        </select>
        {sources.length > 1 && (
          <>
            <label className="muted" style={{ fontSize: 13 }}>
              <input type="checkbox" checked={overlay} onChange={(e) => setOverlay(e.target.checked)} />{" "}
              overlay sources
            </label>
            {!overlay && (
              <select value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="all">All sources ({sources.length})</option>
                {sources.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            )}
          </>
        )}
        {filtered && (
          <span className="muted">
            {filtered.points.length} point{filtered.points.length === 1 ? "" : "s"} ·{" "}
            ref {filtered.refLow ?? "–"}–{filtered.refHigh ?? "–"} {filtered.unit}
          </span>
        )}
      </div>

      <div className="panel">
        {!timeline ? (
          <p className="muted">Loading…</p>
        ) : overlay && sources.length > 1 ? (
          <MultiSourceTrendChart timeline={timeline} />
        ) : (
          filtered && <TrendChart timeline={filtered} />
        )}
      </div>
    </div>
  );
}
