import { useEffect, useState } from "react";
import { api } from "../api/client";

// Quick-entry for vitals/body metrics that feed the Health Score + Action Plan.
// Height is remembered locally (browser) so BMI can be auto-calculated from weight.
export default function VitalsEntry({ onSaved }: { onSaved?: () => void }) {
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [sys, setSys] = useState("");
  const [dia, setDia] = useState("");
  const [waist, setWaist] = useState("");
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState(() => localStorage.getItem("height_cm") || "");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (height) localStorage.setItem("height_cm", height);
  }, [height]);

  const h = parseFloat(height);
  const w = parseFloat(weight);
  const bmi = h > 0 && w > 0 ? +(w / (h / 100) ** 2).toFixed(1) : null;

  async function save() {
    setBusy(true);
    setMsg(null);
    const entries: { slug: string; value: number; unit: string }[] = [];
    if (sys) entries.push({ slug: "systolic_bp", value: parseFloat(sys), unit: "mmHg" });
    if (dia) entries.push({ slug: "diastolic_bp", value: parseFloat(dia), unit: "mmHg" });
    if (waist) entries.push({ slug: "waist_circumference", value: parseFloat(waist), unit: "cm" });
    if (weight) entries.push({ slug: "body_weight", value: w, unit: "kg" });
    if (bmi != null) entries.push({ slug: "bmi", value: bmi, unit: "kg/m2" });
    try {
      for (const e of entries) {
        await api.createObservation({ biomarker_slug: e.slug, value_num: e.value, unit: e.unit, collection_date: date });
      }
      setMsg(`Saved ${entries.length} value${entries.length === 1 ? "" : "s"} ✓`);
      setSys(""); setDia(""); setWaist(""); setWeight("");
      onSaved?.();
    } catch (err) {
      setMsg(String(err));
    } finally {
      setBusy(false);
    }
  }

  const canSave = !!(sys || dia || waist || weight);

  return (
    <div className="panel" style={{ marginBottom: 20 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>+ Log vitals <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>BP · BMI · waist · weight</span></h3>
        <button className="ghost" onClick={() => setOpen((o) => !o)}>{open ? "Close" : "Open"}</button>
      </div>
      {open && (
        <div style={{ marginTop: 12 }}>
          <div className="row" style={{ marginBottom: 10 }}>
            <label className="muted" style={{ fontSize: 12 }}>Date <input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
          </div>
          <div className="row" style={{ marginBottom: 10 }}>
            <label className="muted" style={{ fontSize: 12 }}>Systolic <input style={{ width: 80 }} value={sys} onChange={(e) => setSys(e.target.value)} placeholder="mmHg" /></label>
            <span className="muted">/</span>
            <label className="muted" style={{ fontSize: 12 }}>Diastolic <input style={{ width: 80 }} value={dia} onChange={(e) => setDia(e.target.value)} placeholder="mmHg" /></label>
            <label className="muted" style={{ fontSize: 12 }}>Waist <input style={{ width: 80 }} value={waist} onChange={(e) => setWaist(e.target.value)} placeholder="cm" /></label>
          </div>
          <div className="row">
            <label className="muted" style={{ fontSize: 12 }}>Height <input style={{ width: 80 }} value={height} onChange={(e) => setHeight(e.target.value)} placeholder="cm" /></label>
            <label className="muted" style={{ fontSize: 12 }}>Weight <input style={{ width: 80 }} value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="kg" /></label>
            <span className="muted" style={{ fontSize: 13 }}>BMI: <b style={{ color: "var(--text)" }}>{bmi ?? "—"}</b></span>
            <button onClick={save} disabled={busy || !canSave}>Save</button>
            {msg && <span className="muted">{msg}</span>}
          </div>
          <p className="muted" style={{ fontSize: 11, marginTop: 8 }}>
            Height is remembered on this device to auto-calculate BMI. Saved values feed your timelines, Health Score, and Action Plan.
          </p>
        </div>
      )}
    </div>
  );
}
