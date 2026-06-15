import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function Login({ onAuthed }: { onAuthed: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [hasProfiles, setHasProfiles] = useState<boolean | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [sex, setSex] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.authMe().then((m) => {
      setHasProfiles(m.has_profiles);
      setMode(m.has_profiles ? "login" : "register");
    }).catch(() => setHasProfiles(false));
  }, []);

  async function submit() {
    setBusy(true); setErr(null);
    try {
      if (mode === "register") {
        await api.authRegister({ username, password, name: name || username, date_of_birth: dob || null, sex: sex || null });
      } else {
        await api.authLogin({ username, password });
      }
      onAuthed();
    } catch (e) {
      setErr(String(e).replace(/^Error:\s*\d+\s*[^:]*:\s*/, ""));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="panel" style={{ width: 360 }}>
        <h1 style={{ fontSize: 18, marginTop: 0 }}>CEO of Your Health</h1>
        <p className="muted" style={{ fontSize: 13, marginTop: -4 }}>
          {mode === "register" ? "Create your profile" : "Sign in"}
        </p>
        <div style={{ display: "grid", gap: 10 }}>
          <input placeholder="username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <input type="password" placeholder="password" value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()} />
          {mode === "register" && (
            <>
              <input placeholder="display name" value={name} onChange={(e) => setName(e.target.value)} />
              <div className="row">
                <label className="muted" style={{ fontSize: 12 }}>DOB <input type="date" value={dob} onChange={(e) => setDob(e.target.value)} /></label>
                <label className="muted" style={{ fontSize: 12 }}>Sex{" "}
                  <select value={sex} onChange={(e) => setSex(e.target.value)}>
                    <option value="">—</option><option value="male">male</option><option value="female">female</option>
                  </select>
                </label>
              </div>
            </>
          )}
          <button onClick={submit} disabled={busy || !username || !password}>
            {busy ? "…" : mode === "register" ? "Create profile" : "Sign in"}
          </button>
          {err && <span className="pill bad">{err}</span>}
          <button className="ghost" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Create a new profile" : "I already have a profile"}
          </button>
          {hasProfiles === false && mode === "register" && (
            <p className="muted" style={{ fontSize: 11 }}>
              The first profile created becomes the owner of any data already loaded.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
