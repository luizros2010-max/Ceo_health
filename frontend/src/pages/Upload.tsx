import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Biomarker, type IngestSummary } from "../api/client";

export default function Upload() {
  const [drag, setDrag] = useState(false);
  const [results, setResults] = useState<{ name: string; summary?: IngestSummary; error?: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [keyConfigured, setKeyConfigured] = useState<boolean | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.analysisStatus().then((s) => setKeyConfigured(s.api_key_configured)).catch(() => {});
  }, []);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setBusy(true);
    for (const file of Array.from(files)) {
      try {
        const summary = await api.uploadDocument(file);
        setResults((r) => [{ name: file.name, summary }, ...r]);
      } catch (e) {
        setResults((r) => [{ name: file.name, error: String(e) }, ...r]);
      }
    }
    setBusy(false);
  }

  return (
    <div>
      <h2>Upload</h2>
      {keyConfigured === false && (
        <p className="pill neutral">
          Built-in reader: lab PDFs are parsed for biomarker values automatically (no API key needed).
          Set ANTHROPIC_API_KEY for AI extraction of unusual/messy formats.
        </p>
      )}

      <div
        className={`dropzone ${drag ? "drag" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files); }}
      >
        {busy ? "Processing…" : "Drag & drop lab PDFs / scans here, or click to choose"}
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="application/pdf,image/*"
          style={{ display: "none" }}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {results.length > 0 && (
        <div className="panel" style={{ marginTop: 18 }}>
          <h3>Ingest results</h3>
          {results.map((r, i) => (
            <div key={i} className="row" style={{ justifyContent: "space-between", borderBottom: "1px solid var(--border)", padding: "8px 0" }}>
              <span className="mono">{r.name}</span>
              {r.error ? (
                <span className="pill bad">{r.error}</span>
              ) : r.summary ? (
                <span className="row">
                  {r.summary.is_duplicate && <span className="pill neutral">duplicate</span>}
                  <span className="muted">{r.summary.message}</span>
                  {r.summary.needs_review > 0 && <Link to="/review">review {r.summary.needs_review} →</Link>}
                </span>
              ) : null}
            </div>
          ))}
        </div>
      )}

      <ManualEntry />
    </div>
  );
}

function ManualEntry() {
  const [biomarkers, setBiomarkers] = useState<Biomarker[]>([]);
  const [slug, setSlug] = useState("");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("");
  const [date, setDate] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    api.biomarkers().then((b) => {
      setBiomarkers(b);
      if (b.length) { setSlug(b[0].slug); setUnit(b[0].canonical_unit); }
    });
  }, []);

  async function submit() {
    setMsg(null);
    try {
      await api.createObservation({
        biomarker_slug: slug,
        value_num: parseFloat(value),
        unit,
        collection_date: date,
      });
      setMsg("Saved ✓ (confirmed)");
      setValue("");
    } catch (e) {
      setMsg(String(e));
    }
  }

  return (
    <div className="panel" style={{ marginTop: 18 }}>
      <h3>Manual entry</h3>
      <div className="row">
        <select value={slug} onChange={(e) => {
          setSlug(e.target.value);
          const bm = biomarkers.find((b) => b.slug === e.target.value);
          if (bm) setUnit(bm.canonical_unit);
        }}>
          {biomarkers.map((b) => (
            <option key={b.slug} value={b.slug}>{b.display_name}</option>
          ))}
        </select>
        <input placeholder="value" value={value} onChange={(e) => setValue(e.target.value)} style={{ width: 100 }} />
        <input placeholder="unit" value={unit} onChange={(e) => setUnit(e.target.value)} style={{ width: 100 }} />
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <button onClick={submit} disabled={!slug || !value || !date}>Add</button>
        {msg && <span className="muted">{msg}</span>}
      </div>
    </div>
  );
}
