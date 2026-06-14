import { useEffect, useState } from "react";
import { api, type Biomarker, type ReviewItem } from "../api/client";

export default function Review() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [biomarkers, setBiomarkers] = useState<Biomarker[]>([]);
  const [busy, setBusy] = useState<number | null>(null);

  function load() {
    api.reviewQueue().then(setItems);
  }
  useEffect(() => {
    load();
    api.biomarkers().then(setBiomarkers);
  }, []);

  async function act(id: number, body: Record<string, unknown>) {
    setBusy(id);
    try {
      await api.patchObservation(id, body);
      load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <h2>Review queue</h2>
      <p className="muted">
        Nothing enters your longitudinal record until you confirm it. Re-mapping teaches the catalog
        a new alias, so future imports auto-map.
      </p>
      {items.length === 0 ? (
        <p className="pill good">All clear — no observations need review.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Raw name</th><th>Value</th><th>From</th><th>Map to</th><th>Conf</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => {
              const o = it.observation;
              return (
                <tr key={o.id}>
                  <td>
                    {o.raw_name}
                    {o.source_text_snippet && (
                      <div className="mono muted" style={{ maxWidth: 280, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {o.source_text_snippet}
                      </div>
                    )}
                  </td>
                  <td className="mono">{o.raw_value} {o.raw_unit}</td>
                  <td className="muted">{it.document.original_name}</td>
                  <td>
                    <select
                      defaultValue={it.suggested_biomarker?.slug ?? ""}
                      onChange={(e) => act(o.id, { biomarker_slug: e.target.value })}
                      disabled={busy === o.id}
                    >
                      <option value="">— unmapped —</option>
                      {biomarkers.map((b) => (
                        <option key={b.slug} value={b.slug}>{b.display_name}</option>
                      ))}
                    </select>
                  </td>
                  <td>{(o.mapping_confidence * 100).toFixed(0)}%</td>
                  <td className="row">
                    <button className="ok" disabled={busy === o.id || o.biomarker_id == null} onClick={() => act(o.id, { status: "confirmed" })}>Confirm</button>
                    <button className="danger" disabled={busy === o.id} onClick={() => act(o.id, { status: "rejected" })}>Reject</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
