import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export default function Connectors() {
  const [status, setStatus] = useState<{ oura: { configured: boolean } } | null>(null);
  useEffect(() => {
    api.connectorsStatus().then(setStatus).catch(() => {});
  }, []);

  return (
    <div>
      <h2>Connectors</h2>
      <p className="muted">
        Pull wearable data into your record. Everything is fetched server-side and stored locally —
        new metrics feed your timelines, <Link to="/score">Health Score</Link>, and{" "}
        <Link to="/plan">Action Plan</Link> automatically.
      </p>
      <Oura configured={!!status?.oura.configured} />
      <Apple />
    </div>
  );
}

function Oura({ configured }: { configured: boolean }) {
  const [token, setToken] = useState("");
  const [days, setDays] = useState(90);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function sync() {
    setBusy(true); setMsg(null);
    try {
      const r = await api.ouraSync({ token: token || null, days });
      setMsg(`Synced ${r.added} new readings (${r.range.from} → ${r.range.to})` + (r.errors.length ? ` · issues: ${r.errors.join("; ")}` : ""));
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>💍 Oura Ring</h3>
        <span className={`pill ${configured ? "good" : "neutral"}`}>{configured ? "token configured" : "needs token"}</span>
      </div>
      <p className="muted" style={{ fontSize: 13 }}>
        Resting HR, HRV, sleep duration, SpO₂, and steps. Create a Personal Access Token at{" "}
        <a href="https://cloud.ouraring.com/personal-access-tokens" target="_blank" rel="noreferrer">cloud.ouraring.com</a>{" "}
        (or set <code>OURA_TOKEN</code> in <code>.env</code>).
      </p>
      <div className="row">
        {!configured && (
          <input type="password" placeholder="Personal Access Token" value={token}
            onChange={(e) => setToken(e.target.value)} style={{ width: 280 }} />
        )}
        <label className="muted" style={{ fontSize: 13 }}>days{" "}
          <input type="number" value={days} onChange={(e) => setDays(+e.target.value)} style={{ width: 70 }} />
        </label>
        <button onClick={sync} disabled={busy || (!configured && !token)}>{busy ? "Syncing…" : "Sync now"}</button>
        {msg && <span className="muted">{msg}</span>}
      </div>
    </div>
  );
}

function Apple() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function upload(file: File) {
    setBusy(true); setMsg(null);
    try {
      const r = await api.appleHealthUpload(file);
      setMsg(`Imported ${r.added} readings · metrics: ${r.metrics.join(", ") || "none"}`);
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>⌚ Apple Watch / Health</h3>
        <span className="pill neutral">file import</span>
      </div>
      <p className="muted" style={{ fontSize: 13 }}>
        Apple has no cloud API, so import the export: iPhone <b>Health app → your profile → Export All
        Health Data</b> → <code>export.zip</code>. Maps resting HR, HRV, VO₂max, steps, weight, SpO₂,
        blood pressure, and sleep.
      </p>
      <div className="row">
        <button onClick={() => inputRef.current?.click()} disabled={busy}>
          {busy ? "Importing…" : "Choose export.zip / export.xml"}
        </button>
        <input ref={inputRef} type="file" accept=".zip,.xml" style={{ display: "none" }}
          onChange={(e) => e.target.files && upload(e.target.files[0])} />
        {msg && <span className="muted">{msg}</span>}
      </div>
      <p className="muted" style={{ fontSize: 11, marginTop: 8 }}>
        Large export? Use the CLI instead: <code>python backend/import_apple_health.py path/to/export.zip</code>
      </p>
    </div>
  );
}
