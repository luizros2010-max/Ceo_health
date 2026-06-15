import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Timeline } from "../api/client";

const COLORS = ["#4f8cff", "#2ecc71", "#f5a623", "#a479e2", "#ff5c5c", "#16a766"];

// One line per source, colored — for comparing e.g. Oura vs Apple on one axis.
export default function MultiSourceTrendChart({ timeline }: { timeline: Timeline }) {
  const sources = Array.from(new Set(timeline.points.map((p) => p.source)));
  const byDate = new Map<string, Record<string, number | string>>();
  for (const p of timeline.points) {
    const row = byDate.get(p.date) || { date: p.date };
    row[p.source] = p.value;
    byDate.set(p.date, row);
  }
  const data = Array.from(byDate.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  if (data.length === 0) return <p className="muted">No data points.</p>;

  const values = timeline.points.map((p) => p.value);
  const lo = timeline.refLow ?? Math.min(...values);
  const hi = timeline.refHigh ?? Math.max(...values);
  const pad = (hi - lo || 1) * 0.25;

  return (
    <ResponsiveContainer width="100%" height={380}>
      <LineChart data={data} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid stroke="#2a2f3a" strokeDasharray="3 3" />
        <XAxis dataKey="date" stroke="#9aa4b2" fontSize={12} />
        <YAxis
          stroke="#9aa4b2"
          fontSize={12}
          domain={[Math.min(lo - pad, ...values), Math.max(hi + pad, ...values)]}
          label={{ value: timeline.unit, angle: -90, position: "insideLeft", fill: "#9aa4b2", fontSize: 12 }}
        />
        {(timeline.refLow != null || timeline.refHigh != null) && (
          <ReferenceArea y1={timeline.refLow ?? undefined} y2={timeline.refHigh ?? undefined}
            fill="#2ecc71" fillOpacity={0.08} stroke="#2ecc71" strokeOpacity={0.25} />
        )}
        <Tooltip
          contentStyle={{ background: "#1f232c", border: "1px solid #2a2f3a", borderRadius: 8 }}
          labelStyle={{ color: "#e7ebf0" }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {sources.map((s, i) => (
          <Line key={s} type="monotone" dataKey={s} name={s} stroke={COLORS[i % COLORS.length]}
            strokeWidth={2} connectNulls dot={{ r: 3 }} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
