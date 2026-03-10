/** Minimal API client — mirrors real DocWeaver2 api.ts */

export interface Document {
  id: number;
  filename: string;
  total_pages: number;
  status: "uploaded" | "processing" | "completed" | "error";
  error_message?: string;
  created_at: string;
}

export interface Progress {
  stage: string;
  stage_number: number;
  total_stages: number;
  percent: number;
  message: string;
  done: boolean;
  error: string | null;
  agent_summary?: string;
}

export interface ExtractedField {
  id: number;
  document_id: number;
  field_number: number;
  field_name: string;
  value: string | null;
  found: boolean;
  needs_review: boolean;
  source_page: number | null;
  extraction_note: string | null;
  source_strategy: string;
}

export interface FieldsResponse {
  document_id: number;
  total: number;
  found: number;
  flagged: number;
  fields: ExtractedField[];
}

export interface Correction {
  id: number;
  field_number: number;
  old_value: string | null;
  new_value: string;
  reason: string;
  created_at: string;
}

const API = "/api";

export async function uploadDocument(file: File): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/documents/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listDocuments(): Promise<Document[]> {
  const res = await fetch(`${API}/documents`);
  return res.json();
}

export async function getDocument(id: number): Promise<Document> {
  const res = await fetch(`${API}/documents/${id}`);
  if (!res.ok) throw new Error("Document not found");
  return res.json();
}

export async function getProgress(id: number): Promise<Progress> {
  const res = await fetch(`${API}/documents/${id}/progress`);
  return res.json();
}

export async function getFields(id: number): Promise<FieldsResponse> {
  const res = await fetch(`${API}/documents/${id}/fields`);
  return res.json();
}

export async function updateField(docId: number, fieldNumber: number, value: string): Promise<void> {
  await fetch(`${API}/documents/${docId}/fields/${fieldNumber}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value }),
  });
}

export async function getCorrections(docId: number): Promise<Correction[]> {
  const res = await fetch(`${API}/documents/${docId}/corrections`);
  return res.json();
}

export function getPageImageUrl(docId: number, pageNum: number): string {
  return `${API}/documents/${docId}/pages/${pageNum}/image`;
}
