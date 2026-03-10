"""
Minimal FastAPI backend for enterprise proxy testing.
Mirrors the real DocWeaver2 API structure but with only the essential endpoints.
"""

import logging
import os
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import database as db
import pipeline
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, create dirs."""
    db.init_db()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.images_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"Database initialized at {settings.db_path}")
    yield


app = FastAPI(title="DocWeaver2 Enterprise Test", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permissive for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve page images as static files
images_path = Path(settings.images_dir)
images_path.mkdir(parents=True, exist_ok=True)
app.mount("/static/images", StaticFiles(directory=str(images_path)), name="images")


# -----------------------------------------------------------------------
# Document endpoints
# -----------------------------------------------------------------------

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile):
    """Upload a PDF and start processing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    # Save file
    safe_name = os.path.basename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    upload_path = Path(settings.upload_dir) / unique_name
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    # Count pages
    import fitz
    doc = fitz.open(str(upload_path))
    total_pages = len(doc)
    doc.close()

    # Create DB record
    doc_id = db.create_document(safe_name, str(upload_path), total_pages)

    # Start pipeline in background thread
    thread = threading.Thread(target=pipeline.process_document, args=(doc_id,), daemon=True)
    thread.start()

    return {"id": doc_id, "filename": safe_name, "total_pages": total_pages, "status": "uploaded"}


@app.get("/api/documents")
def list_documents():
    """List all documents."""
    return db.list_documents()


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: int):
    """Get document details."""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@app.get("/api/documents/{doc_id}/progress")
def get_progress(doc_id: int):
    """Poll processing progress."""
    return pipeline.get_progress(doc_id)


# -----------------------------------------------------------------------
# Page endpoints
# -----------------------------------------------------------------------

@app.get("/api/documents/{doc_id}/pages")
def list_pages(doc_id: int):
    """List all pages with image URLs."""
    pages = db.get_pages(doc_id)
    for p in pages:
        p["image_url"] = f"/api/documents/{doc_id}/pages/{p['page_num']}/image"
    return pages


@app.get("/api/documents/{doc_id}/pages/{page_num}/image")
def get_page_image(doc_id: int, page_num: int):
    """Serve a rendered page image."""
    pages = db.get_pages(doc_id)
    page = next((p for p in pages if p["page_num"] == page_num), None)
    if not page or not page["image_path"]:
        raise HTTPException(404, "Page image not found")

    image_path = Path(page["image_path"])
    if not image_path.exists():
        raise HTTPException(404, "Image file not found on disk")

    return FileResponse(str(image_path), media_type="image/png")


# -----------------------------------------------------------------------
# Extraction results endpoints
# -----------------------------------------------------------------------

@app.get("/api/documents/{doc_id}/fields")
def get_fields(doc_id: int):
    """Get all extracted fields."""
    fields = db.get_fields(doc_id)
    return {
        "document_id": doc_id,
        "total": len(fields),
        "found": sum(1 for f in fields if f["found"]),
        "flagged": sum(1 for f in fields if f["needs_review"]),
        "fields": fields,
    }


@app.patch("/api/documents/{doc_id}/fields/{field_number}")
def update_field(doc_id: int, field_number: int, body: dict):
    """Update a field value (user override)."""
    value = body.get("value")
    if value is None:
        raise HTTPException(400, "Missing 'value' in body")
    db.update_field(doc_id, field_number, value, "User override", "user_override")
    return {"status": "ok", "field_number": field_number, "value": value}


@app.get("/api/documents/{doc_id}/corrections")
def get_corrections(doc_id: int):
    """Get agent corrections for a document."""
    return db.get_corrections(doc_id)


# -----------------------------------------------------------------------
# Health check
# -----------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "proxy_url": settings.llm_proxy_url,
        "model": settings.test_model,
        "agent_enabled": settings.review_agent_enabled,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
