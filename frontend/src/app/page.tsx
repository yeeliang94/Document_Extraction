"use client";

import { useEffect, useState, useRef } from "react";
import { listDocuments, uploadDocument, type Document } from "@/lib/api";

export default function HomePage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragover, setDragover] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listDocuments().then(setDocuments).catch(console.error);
  }, []);

  async function handleUpload(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Please select a PDF file");
      return;
    }
    setUploading(true);
    try {
      const doc = await uploadDocument(file);
      window.location.href = `/document/${doc.id}`;
    } catch (e: unknown) {
      alert(`Upload failed: ${e instanceof Error ? e.message : e}`);
      setUploading(false);
    }
  }

  function statusBadge(status: string) {
    const cls =
      status === "completed" ? "badge-green" :
      status === "processing" ? "badge-yellow" :
      status === "error" ? "badge-red" : "badge-gray";
    return <span className={`badge ${cls}`}>{status}</span>;
  }

  return (
    <div className="container">
      <h1>Documents</h1>

      {/* Upload zone */}
      <div
        className={`upload-zone ${dragover ? "dragover" : ""}`}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
        onDragLeave={() => setDragover(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragover(false);
          const file = e.dataTransfer.files[0];
          if (file) handleUpload(file);
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleUpload(file);
          }}
        />
        {uploading ? (
          <p>Uploading...</p>
        ) : (
          <>
            <p style={{ fontSize: 16, fontWeight: 500, marginBottom: 4 }}>
              Drop a PDF here or click to upload
            </p>
            <p className="text-muted text-sm">Financial statements (up to 5 pages)</p>
          </>
        )}
      </div>

      {/* Document list */}
      {documents.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Pages</th>
                <th>Status</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>
                    <a href={`/document/${doc.id}`} style={{ fontWeight: 500 }}>
                      {doc.filename}
                    </a>
                  </td>
                  <td>{doc.total_pages}</td>
                  <td>{statusBadge(doc.status)}</td>
                  <td className="text-muted text-sm">
                    {new Date(doc.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {documents.length === 0 && !uploading && (
        <p className="text-muted" style={{ marginTop: 20, textAlign: "center" }}>
          No documents yet. Upload a PDF to get started.
        </p>
      )}
    </div>
  );
}
