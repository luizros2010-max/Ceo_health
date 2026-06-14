import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Biomarker, type Timeline } from "../api/client";
import TrendChart from "../components/TrendChart";

export default function BiomarkerTimeline() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [biomarkers, setBiomarkers] = useState<Biomarker[]>([]);
  const [timeline, setTimeline] = useState<Timeline | null>(null);

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
    if (slug) api.timeline(slug).then(setTimeline).catch(() => setTimeline(null));
  }, [slug]);

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
        {timeline && (
          <span className="muted">
            {timeline.points.length} point{timeline.points.length === 1 ? "" : "s"} ·{" "}
            ref {timeline.refLow ?? "–"}–{timeline.refHigh ?? "–"} {timeline.unit}
          </span>
        )}
      </div>

      <div className="panel">
        {timeline ? <TrendChart timeline={timeline} /> : <p className="muted">Loading…</p>}
      </div>
    </div>
  );
}
