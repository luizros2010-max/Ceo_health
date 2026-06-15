import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Timeline } from "../api/client";

export default function TrendChart({ timeline }: { timeline: Timeline }) {
  const data = timeline.points.map((p) => ({
    date: p.date,
    value: p.value,
    source: p.source,
    inRange:
      (timeline.refLow == null || p.value >= timeline.refLow) &&
      (timeline.refHigh == null || p.value <= timeline.refHigh),
  }));

  if (data.length === 0) {
    return <p className="muted">No confirmed data points yet for this biomarker.</p>;
  }

  const values = data.map((d) => d.value);
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
        {/* Reference-range band */}
        {(timeline.refLow != null || timeline.refHigh != null) && (
          <ReferenceArea
            y1={timeline.refLow ?? undefined}
            y2={timeline.refHigh ?? undefined}
            fill="#2ecc71"
            fillOpacity={0.08}
            stroke="#2ecc71"
            strokeOpacity={0.25}
          />
        )}
        <Tooltip
          contentStyle={{ background: "#1f232c", border: "1px solid #2a2f3a", borderRadius: 8 }}
          labelStyle={{ color: "#e7ebf0" }}
          formatter={(v: number, _n, p: { payload?: { source?: string } }) => [
            `${v} ${timeline.unit}`,
            p?.payload?.source || timeline.biomarker.display_name,
          ]}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#4f8cff"
          strokeWidth={2}
          dot={(props) => {
            const { cx, cy, payload, index } = props as {
              cx: number; cy: number; payload: { inRange: boolean }; index: number;
            };
            return (
              <circle
                key={index}
                cx={cx}
                cy={cy}
                r={4}
                fill={payload.inRange ? "#4f8cff" : "#ff5c5c"}
                stroke="#0f1115"
                strokeWidth={1}
              />
            );
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
