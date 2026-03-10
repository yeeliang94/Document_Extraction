"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  getDocument,
  getProgress,
  getFields,
  getCorrections,
  getPageImageUrl,
  updateField,
  type Document,
  type Progress,
  type ExtractedField,
  type Correction,
} from "@/lib/api";

export default function DocumentPage() {
  const params = useParams();
  const docId = Number(params.id);

  const [doc, setDoc] = useState<Document | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [fields, setFields] = useState<ExtractedField[]>([]);
  const [corrections, setCorrections] = useState<Correction[]>([]);
  const [selectedPage, setSelectedPage] = useState(1);
  const [editingField, setEditingField] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [agentSummary, setAgentSummary] = useState("");

  // Load document
  useEffect(() => {
    getDocument(docId).then(setDoc).catch(console.error);
  }, [docId]);

  // Poll progress while processing
  useEffect(() => {
    if (!doc || (doc.status !== "uploaded" && doc.status !== "processing")) return;

    const interval = setInterval(async () => {
      try {
        const p = await getProgress(docId);
        setProgress(p);

        if (p.agent_summary) setAgentSummary(p.agent_summary);

        if (p.done) {
          clearInterval(interval);
          // Refresh document
          const updated = await getDocument(docId);
          setDoc(updated);
        }
      } catch {
        // ignore polling errors
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [doc?.status, docId]);

  // Load results when completed
  useEffect(() => {
    if (!doc || doc.status !== "completed") return;
    getFields(docId).then((r) => setFields(r.fields)).catch(console.error);
    getCorrections(docId).then(setCorrections).catch(console.error);
  }, [doc?.status, docId]);

  const handleSaveField = useCallback(async (fieldNumber: number) => {
    await updateField(docId, fieldNumber, editValue);
    setEditingField(null);
    // Refresh
    const r = await getFields(docId);
    setFields(r.fields);
  }, [docId, editValue]);

  if (!doc) return <div className="container"><p>Loading...</p></div>;

  return (
    <div className="container">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <a href="/" className="btn">Back</a>
        <div>
          <h1 style={{ marginBottom: 2 }}>{doc.filename}</h1>
          <span className="text-muted text-sm">{doc.total_pages} pages</span>
        </div>
      </div>

      {/* Processing status */}
      {(doc.status === "uploaded" || doc.status === "processing") && (
        <div className="card">
          <h2>Processing</h2>
          {progress && (
            <>
              <div className="progress-bar" style={{ marginBottom: 12 }}>
                <div className="progress-fill" style={{ width: `${progress.percent}%` }} />
              </div>
              <p style={{ fontWeight: 500 }}>
                Stage {progress.stage_number}/{progress.total_stages}: {progress.stage}
              </p>
              <p className="text-muted text-sm">{progress.message}</p>
              {progress.error && (
                <p style={{ color: "#d1242f", marginTop: 8 }}>{progress.error}</p>
              )}
            </>
          )}
          {!progress && <p className="text-muted">Starting...</p>}
        </div>
      )}

      {/* Error state */}
      {doc.status === "error" && (
        <div className="card" style={{ borderColor: "#d1242f" }}>
          <h2 style={{ color: "#d1242f" }}>Error</h2>
          <p>{doc.error_message}</p>
        </div>
      )}

      {/* Completed — show results */}
      {doc.status === "completed" && (
        <>
          {/* Page thumbnails */}
          <div className="card">
            <h2>Pages</h2>
            <div style={{ display: "flex", gap: 12, overflowX: "auto" }}>
              {Array.from({ length: doc.total_pages }, (_, i) => i + 1).map((num) => (
                <div
                  key={num}
                  className="page-thumb"
                  onClick={() => setSelectedPage(num)}
                  style={{
                    minWidth: 120,
                    borderColor: selectedPage === num ? "#c78c2e" : undefined,
                    borderWidth: selectedPage === num ? 2 : 1,
                  }}
                >
                  <img
                    src={getPageImageUrl(docId, num)}
                    alt={`Page ${num}`}
                    loading="lazy"
                  />
                  <p style={{ textAlign: "center", padding: 4, fontSize: 12 }}>Page {num}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Selected page preview */}
          <div className="card">
            <h2>Page {selectedPage}</h2>
            <img
              src={getPageImageUrl(docId, selectedPage)}
              alt={`Page ${selectedPage}`}
              style={{ width: "100%", borderRadius: 8, border: "1px solid #e8e5df" }}
            />
          </div>

          {/* Extracted fields */}
          <div className="card">
            <h2>
              Extracted Fields
              <span className="text-muted text-sm" style={{ fontWeight: 400, marginLeft: 8 }}>
                {fields.filter((f) => f.found).length}/{fields.length} found
              </span>
            </h2>
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Field</th>
                  <th className="text-right">Value (RM&apos;000)</th>
                  <th>Status</th>
                  <th>Note</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {fields.map((f) => (
                  <tr key={f.field_number}>
                    <td className="text-muted">{f.field_number}</td>
                    <td style={{ fontWeight: 500 }}>{f.field_name}</td>
                    <td className="text-right">
                      {editingField === f.field_number ? (
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSaveField(f.field_number);
                            if (e.key === "Escape") setEditingField(null);
                          }}
                          autoFocus
                          style={{
                            width: 120,
                            padding: "4px 8px",
                            border: "1px solid #c78c2e",
                            borderRadius: 4,
                            textAlign: "right",
                            fontFamily: "inherit",
                          }}
                        />
                      ) : (
                        <span className="field-value">
                          {f.value || <span className="text-muted">—</span>}
                        </span>
                      )}
                    </td>
                    <td>
                      {f.needs_review ? (
                        <span className="badge badge-yellow">Review</span>
                      ) : f.found ? (
                        <span className="badge badge-green">OK</span>
                      ) : (
                        <span className="badge badge-gray">Not found</span>
                      )}
                      {f.source_strategy === "review_agent" && (
                        <span className="badge badge-blue" style={{ marginLeft: 4 }}>Agent</span>
                      )}
                      {f.source_strategy === "user_override" && (
                        <span className="badge badge-blue" style={{ marginLeft: 4 }}>Override</span>
                      )}
                    </td>
                    <td className="text-muted text-sm" style={{ maxWidth: 200 }}>
                      {f.extraction_note}
                    </td>
                    <td>
                      {editingField === f.field_number ? (
                        <div style={{ display: "flex", gap: 4 }}>
                          <button className="btn" style={{ padding: "4px 12px", fontSize: 12 }} onClick={() => handleSaveField(f.field_number)}>Save</button>
                          <button className="btn" style={{ padding: "4px 12px", fontSize: 12 }} onClick={() => setEditingField(null)}>Cancel</button>
                        </div>
                      ) : (
                        <button
                          className="btn"
                          style={{ padding: "4px 12px", fontSize: 12 }}
                          onClick={() => { setEditingField(f.field_number); setEditValue(f.value || ""); }}
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Agent corrections */}
          {corrections.length > 0 && (
            <div className="card">
              <h2>Agent Corrections ({corrections.length})</h2>
              <table>
                <thead>
                  <tr>
                    <th>Field #</th>
                    <th className="text-right">Old Value</th>
                    <th className="text-right">New Value</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {corrections.map((c) => (
                    <tr key={c.id}>
                      <td>{c.field_number}</td>
                      <td className="text-right field-value">{c.old_value || "—"}</td>
                      <td className="text-right field-value" style={{ color: "#1a7f37" }}>{c.new_value}</td>
                      <td className="text-sm">{c.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Agent summary */}
          {agentSummary && (
            <div className="card">
              <h2>Agent Review Summary</h2>
              <pre style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.6, color: "#333" }}>
                {agentSummary}
              </pre>
            </div>
          )}
        </>
      )}
    </div>
  );
}
