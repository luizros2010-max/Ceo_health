// Typed API client. All calls go to the local FastAPI backend; the Claude key
// lives server-side only and never reaches this bundle.

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export interface OverviewCard {
  slug: string;
  display_name: string;
  category: string | null;
  value: number;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  in_range: boolean | null;
  last_measured: string;
  sparkline: { date: string; value: number }[];
}

export interface Overview {
  stats: {
    documents: number;
    observations: number;
    needs_review: number;
    date_span: { from: string | null; to: string | null };
  };
  cards: OverviewCard[];
}

export interface Biomarker {
  slug: string;
  display_name: string;
  category: string | null;
  canonical_unit: string;
  default_ref_low: number | null;
  default_ref_high: number | null;
  higher_is_better: boolean | null;
  has_data: boolean;
}

export interface TimelinePoint {
  date: string;
  value: number;
  operator: string;
  refLow: number | null;
  refHigh: number | null;
  sourceDocId: number;
  source: string;
  status: string;
}

export interface Timeline {
  biomarker: { slug: string; display_name: string; category: string | null };
  unit: string;
  refLow: number | null;
  refHigh: number | null;
  higherIsBetter: boolean | null;
  points: TimelinePoint[];
}

export interface DocumentRow {
  id: number;
  original_name: string;
  lab_name: string | null;
  source_type: string;
  collection_date: string | null;
  report_date: string | null;
  ingest_status: string;
  notes: string | null;
  created_at: string;
  observations_total: number;
  confirmed: number;
  needs_review: number;
}

export interface Observation {
  id: number;
  source_document_id: number;
  raw_name: string;
  raw_value: string | null;
  raw_unit: string | null;
  raw_ref_range: string | null;
  biomarker_id: number | null;
  value_num: number | null;
  canonical_unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  ref_source: string | null;
  operator: string;
  collection_date: string | null;
  source_text_snippet: string | null;
  mapping_confidence: number;
  status: string;
}

export interface IngestSummary {
  document_id: number;
  is_duplicate: boolean;
  status: string;
  observations_total: number;
  confirmed: number;
  needs_review: number;
  extraction_error: string | null;
  message: string;
}

export interface ReviewItem {
  observation: Observation;
  suggested_biomarker: { slug: string; display_name: string } | null;
  document: { id: number | null; original_name: string | null; lab_name: string | null };
}

export interface ReportListItem {
  id: number;
  title: string;
  category: string | null;
  report_date: string | null;
  facility: string | null;
  impression: string | null;
  snippet: string;
}

export interface NarrativeReport {
  id: number;
  title: string;
  category: string | null;
  report_date: string | null;
  facility: string | null;
  body: string;
  impression: string | null;
}

export interface TrendFlag {
  biomarker: string;
  unit: string;
  latest: number;
  latest_date: string;
  in_range: boolean | null;
  direction: string;
  n_points: number;
  severity: "high" | "medium" | "watch" | "ok";
}

export interface AnalysisPreview {
  slice: {
    subject: { age: number | null; sex: string | null };
    biomarkers: { biomarker: string; unit: string; points: unknown[] }[];
    reports?: unknown[];
  };
  flags: TrendFlag[];
  summary: { biomarkers: number; data_points: number; reports: number; shares_age_sex: boolean };
}

export interface AnalysisResult {
  ok: boolean;
  insights?: string;
  error?: string;
  model?: string;
  flags: TrendFlag[];
}

export interface ScoreMarker {
  biomarker: string;
  slug: string;
  value: number;
  unit: string;
  date: string;
  score: number;
  optimal: number | null;
}
export interface ScoreDomain {
  name: string;
  weight: number;
  score: number;
  markers: ScoreMarker[];
}
export interface HealthScore {
  overall: { score: number | null; band: string; label: string };
  subject: { age: number | null; sex: string | null };
  domains: ScoreDomain[];
  as_of: string | null;
  caveats: string[];
}

export interface PlanTarget {
  biomarker: string;
  slug: string;
  domain: string;
  current: number;
  unit: string;
  current_score: number;
  target: number;
  direction: string;
}
export interface PlanLever {
  domain: string;
  score: number;
  nutrition?: string[];
  workout?: string[];
  lifestyle?: string[];
  medical?: string[];
}
export interface ActionPlan {
  overall: { score: number | null; band: string; label: string };
  subject: { age: number | null; sex: string | null };
  targets: PlanTarget[];
  levers: PlanLever[];
  missing_trackers: { slug: string; label: string }[];
  note: string;
}

export interface Patient {
  id: number;
  name: string;
  date_of_birth: string | null;
  sex: string | null;
}

export const api = {
  health: () => req<{ status: string }>("/health"),
  analysisStatus: () =>
    req<{ api_key_configured: boolean; extract_model: string; phase4_enabled: boolean }>(
      "/analysis/status",
    ),
  overview: () => req<Overview>("/overview"),
  biomarkers: () => req<Biomarker[]>("/biomarkers"),
  timeline: (slug: string) => req<Timeline>(`/biomarkers/${slug}/timeline`),
  documents: () => req<DocumentRow[]>("/documents"),
  document: (id: number) =>
    req<{ document: DocumentRow & { raw_text?: string }; observations: Observation[] }>(
      `/documents/${id}`,
    ),
  uploadDocument: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<IngestSummary>("/documents", { method: "POST", body: fd });
  },
  importCsv: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<{ imported: number; duplicates: number; skipped: number; unmatched: number; unmatched_names: string[] }>(
      "/observations/import-csv", { method: "POST", body: fd },
    );
  },
  importReportsJson: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<{ imported: number; duplicates: number }>("/reports/import-json", { method: "POST", body: fd });
  },
  patchDocument: (id: number, body: Record<string, unknown>) =>
    req<DocumentRow>(`/documents/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  deleteDocument: (id: number) =>
    req<{ deleted: number }>(`/documents/${id}`, { method: "DELETE" }),
  reviewQueue: () => req<ReviewItem[]>("/observations/review"),
  patchObservation: (id: number, body: Record<string, unknown>) =>
    req<Observation>(`/observations/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  createObservation: (body: Record<string, unknown>) =>
    req<Observation>("/observations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  reports: () => req<ReportListItem[]>("/reports"),
  report: (id: number) => req<NarrativeReport>(`/reports/${id}`),
  createReport: (body: Record<string, unknown>) =>
    req<NarrativeReport>("/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  deleteReport: (id: number) =>
    req<{ deleted: number }>(`/reports/${id}`, { method: "DELETE" }),
  healthScore: () => req<HealthScore>("/analysis/score"),
  actionPlan: () => req<ActionPlan>("/analysis/plan"),
  authMe: () => req<{ has_profiles: boolean }>("/auth/me"),
  authWhoami: () =>
    req<{ id: number; name: string; username: string; is_admin: boolean }>("/auth/session"),
  listProfiles: () =>
    req<{ id: number; name: string; username: string; is_admin: boolean; is_you: boolean; observations: number }[]>(
      "/auth/profiles",
    ),
  createProfile: (body: Record<string, unknown>) =>
    req<{ id: number }>("/auth/profiles", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }),
  resetProfilePassword: (id: number, password: string) =>
    req<{ ok: boolean }>(`/auth/profiles/${id}/reset-password`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }),
    }),
  deleteProfile: (id: number) =>
    req<{ deleted: number }>(`/auth/profiles/${id}`, { method: "DELETE" }),
  authLogin: (body: Record<string, unknown>) =>
    req<{ id: number; name: string }>("/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }),
  authRegister: (body: Record<string, unknown>) =>
    req<{ id: number; name: string }>("/auth/register", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }),
  authLogout: () => req<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  connectorsStatus: () =>
    req<{ oura: { configured: boolean }; apple_health: { available: boolean } }>("/connectors/status"),
  ouraSync: (body: Record<string, unknown>) =>
    req<{ ok: boolean; added: number; errors: string[]; range: { from: string; to: string } }>(
      "/connectors/oura/sync",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    ),
  appleHealthUpload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<{ ok: boolean; added: number; metrics: string[] }>("/connectors/apple-health", {
      method: "POST",
      body: fd,
    });
  },
  getPatient: () => req<Patient>("/patient"),
  patchPatient: (body: Record<string, unknown>) =>
    req<Patient>("/patient", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  analysisPreview: (body: Record<string, unknown>) =>
    req<AnalysisPreview>("/analysis/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  analysisRun: (body: Record<string, unknown>) =>
    req<AnalysisResult>("/analysis/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};
