import { NavLink, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview";
import Upload from "./pages/Upload";
import Documents from "./pages/Documents";
import DocumentDetail from "./pages/DocumentDetail";
import BiomarkerTimeline from "./pages/BiomarkerTimeline";
import Reports from "./pages/Reports";
import Insights from "./pages/Insights";
import Report from "./pages/Report";
import Review from "./pages/Review";

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>CEO of Your Health</h1>
        <div className="tag">your longitudinal record</div>
        <nav className="nav">
          <NavLink to="/" end>Overview</NavLink>
          <NavLink to="/upload">Upload</NavLink>
          <NavLink to="/documents">Documents</NavLink>
          <NavLink to="/biomarker">Timelines</NavLink>
          <NavLink to="/reports">Imaging & Reports</NavLink>
          <NavLink to="/insights">AI Insights</NavLink>
          <NavLink to="/report">Doctor Report</NavLink>
          <NavLink to="/review">Review</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/documents/:id" element={<DocumentDetail />} />
          <Route path="/biomarker" element={<BiomarkerTimeline />} />
          <Route path="/biomarker/:slug" element={<BiomarkerTimeline />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/report" element={<Report />} />
          <Route path="/review" element={<Review />} />
        </Routes>
      </main>
    </div>
  );
}
