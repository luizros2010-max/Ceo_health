import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import Login from "./pages/Login";
import Overview from "./pages/Overview";
import Upload from "./pages/Upload";
import Documents from "./pages/Documents";
import Connectors from "./pages/Connectors";
import DocumentDetail from "./pages/DocumentDetail";
import BiomarkerTimeline from "./pages/BiomarkerTimeline";
import Reports from "./pages/Reports";
import Insights from "./pages/Insights";
import Score from "./pages/Score";
import ActionPlanPage from "./pages/ActionPlan";
import Report from "./pages/Report";
import Review from "./pages/Review";

export default function App() {
  const [profile, setProfile] = useState<{ name: string } | null | undefined>(undefined);

  function refresh() {
    api.authWhoami().then((p) => setProfile(p)).catch(() => setProfile(null));
  }
  useEffect(refresh, []);

  async function logout() {
    await api.authLogout();
    setProfile(null);
  }

  if (profile === undefined) {
    return <div style={{ padding: 40, color: "var(--muted)" }}>Loading…</div>;
  }
  if (profile === null) {
    return <Login onAuthed={refresh} />;
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>CEO of Your Health</h1>
        <div className="tag">{profile.name}</div>
        <nav className="nav">
          <NavLink to="/" end>Overview</NavLink>
          <NavLink to="/upload">Upload</NavLink>
          <NavLink to="/documents">Documents</NavLink>
          <NavLink to="/connectors">Connectors</NavLink>
          <NavLink to="/biomarker">Timelines</NavLink>
          <NavLink to="/reports">Imaging & Reports</NavLink>
          <NavLink to="/score">Health Score</NavLink>
          <NavLink to="/plan">Action Plan</NavLink>
          <NavLink to="/insights">AI Insights</NavLink>
          <NavLink to="/report">Doctor Report</NavLink>
          <NavLink to="/review">Review</NavLink>
        </nav>
        <button className="ghost" onClick={logout} style={{ marginTop: 18, width: "100%" }}>
          Sign out
        </button>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/documents/:id" element={<DocumentDetail />} />
          <Route path="/connectors" element={<Connectors />} />
          <Route path="/biomarker" element={<BiomarkerTimeline />} />
          <Route path="/biomarker/:slug" element={<BiomarkerTimeline />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/score" element={<Score />} />
          <Route path="/plan" element={<ActionPlanPage />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/report" element={<Report />} />
          <Route path="/review" element={<Review />} />
        </Routes>
      </main>
    </div>
  );
}
