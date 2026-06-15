import { useEffect, useState } from "react";
import { api } from "../api/client";

type Profile = { id: number; name: string; username: string; is_admin: boolean; is_you: boolean; observations: number };

export default function Admin() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  function load() {
    api.listProfiles().then(setProfiles).catch((e) => setErr(String(e)));
  }
  useEffect(load, []);

  async function remove(p: Profile) {
    if (!confirm(`Delete ${p.name}'s profile and ALL their data? This cannot be undone.`)) return;
    await api.deleteProfile(p.id);
    load();
  }
  async function reset(p: Profile) {
    const pw = prompt(`New password for ${p.name}:`);
    if (!pw) return;
    await api.resetProfilePassword(p.id, pw);
    alert("Password updated.");
  }

  if (err) return <p className="pill bad">{err}</p>;

  return (
    <div>
      <h2>Family Profiles <span className="pill neutral">admin</span></h2>
      <p className="muted">Manage who can use this instance. Each profile has its own isolated data.</p>

      <button onClick={() => setShowForm((s) => !s)} style={{ marginBottom: 14 }}>
        {showForm ? "Cancel" : "+ Add profile"}
      </button>
      {showForm && <NewProfile onSaved={() => { setShowForm(false); load(); }} />}

      <div className="panel">
        <table>
          <thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Results</th><th></th></tr></thead>
          <tbody>
            {profiles.map((p) => (
              <tr key={p.id}>
                <td>{p.name}{p.is_you && <span className="muted"> (you)</span>}</td>
                <td className="mono">{p.username}</td>
                <td>{p.is_admin ? <span className="pill good">admin</span> : <span className="pill neutral">member</span>}</td>
                <td>{p.observations}</td>
                <td className="row">
                  <button className="ghost" onClick={() => reset(p)}>Reset password</button>
                  {!p.is_you && <button className="danger" onClick={() => remove(p)}>Delete</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NewProfile({ onSaved }: { onSaved: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [sex, setSex] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setErr(null);
    try {
      await api.createProfile({ username, password, name: name || username, date_of_birth: dob || null, sex: sex || null });
      onSaved();
    } catch (e) {
      setErr(String(e).replace(/^Error:\s*\d+\s*[^:]*:\s*/, ""));
    }
  }

  return (
    <div className="panel">
      <div className="row" style={{ flexWrap: "wrap" }}>
        <input placeholder="username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input type="password" placeholder="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <input placeholder="display name" value={name} onChange={(e) => setName(e.target.value)} />
        <input type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
        <select value={sex} onChange={(e) => setSex(e.target.value)}>
          <option value="">sex —</option><option value="male">male</option><option value="female">female</option>
        </select>
        <button onClick={save} disabled={!username || !password}>Create</button>
      </div>
      {err && <p className="pill bad" style={{ marginTop: 8 }}>{err}</p>}
    </div>
  );
}
