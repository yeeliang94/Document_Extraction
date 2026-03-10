"""
Simplified pipeline: PDF → images → LLM vision extraction → agent review.
No OCR, no chunking, no TOC — just send page images to LLM and extract fields.
"""

import asyncio
import base64
import json
import logging
import time
from pathlib import Path

import fitz  # pymupdf
from openai import OpenAI
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

import database as db
from config import settings

logger = logging.getLogger(__name__)

# In-memory progress tracking (document_id -> progress dict)
_progress: dict[int, dict] = {}


def get_progress(doc_id: int) -> dict:
    return _progress.get(doc_id, {
        "stage": "idle",
        "stage_number": 0,
        "total_stages": 3,
        "percent": 0,
        "message": "",
        "done": False,
        "error": None,
    })


def _update_progress(doc_id: int, stage: str, stage_number: int, percent: int, message: str):
    _progress[doc_id] = {
        "stage": stage,
        "stage_number": stage_number,
        "total_stages": 3,
        "percent": percent,
        "message": message,
        "done": False,
        "error": None,
    }


# -----------------------------------------------------------------------
# Field definitions (simplified XBRL — income statement + balance sheet)
# -----------------------------------------------------------------------
FIELDS = [
    {"field_number": 1, "name": "Revenue", "type": "monetary"},
    {"field_number": 2, "name": "Cost of sales", "type": "monetary"},
    {"field_number": 3, "name": "Gross profit", "type": "monetary"},
    {"field_number": 4, "name": "Other income", "type": "monetary"},
    {"field_number": 5, "name": "Distribution expenses", "type": "monetary"},
    {"field_number": 6, "name": "Administrative expenses", "type": "monetary"},
    {"field_number": 7, "name": "Finance costs", "type": "monetary"},
    {"field_number": 8, "name": "Profit before tax", "type": "monetary"},
    {"field_number": 9, "name": "Tax expense", "type": "monetary"},
    {"field_number": 10, "name": "Profit for the year", "type": "monetary"},
    {"field_number": 11, "name": "Total non-current assets", "type": "monetary"},
    {"field_number": 12, "name": "Total current assets", "type": "monetary"},
    {"field_number": 13, "name": "Total assets", "type": "monetary"},
    {"field_number": 14, "name": "Total equity", "type": "monetary"},
    {"field_number": 15, "name": "Total non-current liabilities", "type": "monetary"},
    {"field_number": 16, "name": "Total current liabilities", "type": "monetary"},
    {"field_number": 17, "name": "Total liabilities", "type": "monetary"},
    {"field_number": 18, "name": "Total equity and liabilities", "type": "monetary"},
    {"field_number": 19, "name": "Cash and cash equivalents", "type": "monetary"},
    {"field_number": 20, "name": "Earnings per share (basic)", "type": "per_share"},
]


# -----------------------------------------------------------------------
# Stage 1: Render PDF pages to images
# -----------------------------------------------------------------------
def render_pages(doc_id: int, pdf_path: str) -> list[dict]:
    """Convert PDF pages to PNG images."""
    _update_progress(doc_id, "rendering", 1, 10, "Rendering PDF pages...")

    images_dir = Path(settings.images_dir) / str(doc_id)
    images_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    zoom = settings.page_image_dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pages = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        image_path = images_dir / f"page_{i + 1:03d}.png"
        pix.save(str(image_path))

        page_info = {
            "page_num": i + 1,
            "image_path": str(image_path),
            "width": pix.width,
            "height": pix.height,
        }
        pages.append(page_info)
        db.insert_page(doc_id, i + 1, str(image_path), pix.width, pix.height)

        _update_progress(doc_id, "rendering", 1, 10 + (20 * (i + 1) // len(doc)),
                         f"Rendered page {i + 1}/{len(doc)}")

    doc.close()
    return pages


# -----------------------------------------------------------------------
# Stage 2: LLM vision extraction
# -----------------------------------------------------------------------
EXTRACTION_SYSTEM_PROMPT = """\
You are a financial data extraction assistant for Malaysian annual reports.
Extract field values from the provided financial statement images.

Rules:
- Values are in RM'000 (thousands of Ringgit Malaysia) unless stated otherwise.
- Extract the CURRENT YEAR GROUP figures (most recent period, Group column).
- For expenses/costs, use POSITIVE numbers.
- If a field is not found or not applicable, set found=false and value=null.
- Copy the exact number from the document.

Respond with valid JSON only, no markdown fences."""


def extract_fields(doc_id: int, pages: list[dict]) -> list[dict]:
    """Send page images to LLM for field extraction."""
    _update_progress(doc_id, "extracting", 2, 35, "Sending pages to LLM for extraction...")

    client = OpenAI(
        api_key=settings.google_api_key,
        base_url=settings.llm_proxy_url,
    )

    # Build field list for prompt
    field_lines = [f"  - Field #{f['field_number']}: {f['name']} ({f['type']})" for f in FIELDS]
    prompt = (
        "Extract the following financial fields from these document pages.\n\n"
        "Fields to extract:\n" + "\n".join(field_lines) + "\n\n"
        "Return JSON: {\"fields\": [{\"field_number\": int, \"name\": str, "
        "\"value\": str|null, \"found\": bool, \"source_page\": int|null, \"note\": str|null}]}"
    )

    # Build multimodal content
    content: list[dict] = [{"type": "text", "text": prompt}]
    for p in pages:
        with open(p["image_path"], "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
        })

    _update_progress(doc_id, "extracting", 2, 45,
                     f"Extracting {len(FIELDS)} fields from {len(pages)} pages...")

    start = time.time()
    response = client.chat.completions.create(
        model=settings.test_model,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        temperature=settings.temperature,
        max_tokens=settings.max_output_tokens,
        response_format={"type": "json_object"},
        extra_body={"reasoning_effort": "medium"},
    )
    elapsed = time.time() - start

    text = response.choices[0].message.content
    usage = response.usage
    logger.info(f"Extraction completed in {elapsed:.1f}s — tokens: {usage.prompt_tokens}+{usage.completion_tokens}")

    try:
        data = json.loads(text)
        fields = data.get("fields", [])
    except json.JSONDecodeError:
        logger.error(f"JSON parse error: {text[:500]}")
        fields = []

    # Store in DB
    db.bulk_insert_fields(doc_id, fields)

    _update_progress(doc_id, "extracting", 2, 65,
                     f"Extracted {sum(1 for f in fields if f.get('found'))}/{len(FIELDS)} fields ({elapsed:.1f}s)")

    return fields


# -----------------------------------------------------------------------
# Stage 3: Agent review (arithmetic verification)
# -----------------------------------------------------------------------
def _build_agent_tools(doc_id: int):
    """Create tool functions bound to the document."""

    def get_all_fields() -> dict:
        """Get all extracted financial fields with their current values."""
        fields = db.get_fields(doc_id)
        return {
            "status": "ok",
            "fields": [
                {"field_number": f["field_number"], "field_name": f["field_name"],
                 "value": f["value"], "found": bool(f["found"]), "needs_review": bool(f["needs_review"])}
                for f in fields
            ],
        }

    def check_arithmetic() -> dict:
        """Check arithmetic consistency: gross profit, PBT, net profit, balance sheet equation."""
        fields = {f["field_number"]: f["value"] for f in db.get_fields(doc_id)}

        def val(n):
            v = fields.get(n)
            if not v:
                return None
            try:
                return int(v.replace(",", "").replace(" ", ""))
            except (ValueError, AttributeError):
                return None

        checks = []

        # Gross profit = Revenue - Cost of sales
        rev, cos, gp = val(1), val(2), val(3)
        if all(v is not None for v in [rev, cos, gp]):
            expected = rev - cos
            checks.append({"rule": "Gross profit = Revenue - Cost of sales",
                           "expected": str(expected), "actual": str(gp), "pass": abs(expected - gp) <= 1})

        # PBT check (approximate — may have other items)
        pbt = val(8)
        if gp is not None and pbt is not None:
            other = val(4) or 0
            dist = val(5) or 0
            admin = val(6) or 0
            fin = val(7) or 0
            expected_pbt = gp + other - dist - admin - fin
            checks.append({"rule": "PBT = GP + other - dist - admin - finance",
                           "expected": str(expected_pbt), "actual": str(pbt), "pass": abs(expected_pbt - pbt) <= 1})

        # Net profit = PBT - Tax
        tax, net = val(9), val(10)
        if pbt is not None and tax is not None and net is not None:
            expected_net = pbt - tax
            checks.append({"rule": "Net profit = PBT - Tax",
                           "expected": str(expected_net), "actual": str(net), "pass": abs(expected_net - net) <= 1})

        # Total assets = equity + liabilities
        ta, te, tl = val(13), val(14), val(17)
        if all(v is not None for v in [ta, te, tl]):
            checks.append({"rule": "Total assets = Equity + Liabilities",
                           "expected": str(te + tl), "actual": str(ta), "pass": abs((te + tl) - ta) <= 1})

        # Total equity and liabilities cross-check
        tel = val(18)
        if ta is not None and tel is not None:
            checks.append({"rule": "Total assets = Total equity and liabilities",
                           "expected": str(ta), "actual": str(tel), "pass": abs(ta - tel) <= 1})

        return {"status": "ok", "checks": checks, "all_pass": all(c["pass"] for c in checks)}

    def update_field_value(field_number: int, new_value: str, reason: str) -> dict:
        """Update a field's value after verification. Use when arithmetic reveals an error."""
        db.update_field(doc_id, field_number, new_value, reason, "review_agent")
        return {"status": "ok", "field_number": field_number, "new_value": new_value}

    def flag_field_for_review(field_number: int, reason: str) -> dict:
        """Flag a field that needs human review."""
        conn = db.get_conn()
        conn.execute(
            "UPDATE extracted_fields SET needs_review = 1, extraction_note = ? WHERE document_id = ? AND field_number = ?",
            (reason, doc_id, field_number),
        )
        conn.commit()
        return {"status": "ok", "field_number": field_number, "flagged": True}

    return [get_all_fields, check_arithmetic, update_field_value, flag_field_for_review]


async def _run_review_agent(doc_id: int) -> str:
    """Run the review agent asynchronously."""
    tools = _build_agent_tools(doc_id)

    agent = LlmAgent(
        name="review_agent",
        model=LiteLlm(
            model=settings.adk_model_name,
            api_key=settings.google_api_key,
            api_base=settings.llm_proxy_url,
        ),
        instruction=(
            "You are a financial review agent. Verify extracted data for consistency.\n"
            "1. Call get_all_fields() to see extracted values\n"
            "2. Call check_arithmetic() to verify mathematical consistency\n"
            "3. Fix errors with update_field_value() — only when confident\n"
            "4. Flag uncertain fields with flag_field_for_review()\n"
            "5. Call check_arithmetic() again after fixes to confirm\n"
            "Be precise. Provide clear reasons for all changes."
        ),
        tools=tools,
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="enterprise_test", session_service=session_service)
    session = await session_service.create_session(app_name="enterprise_test", user_id="system")

    content = types.Content(
        role="user",
        parts=[types.Part(text=(
            "Review all extracted fields. Check arithmetic consistency and fix any errors. "
            "Report what you checked and any corrections made."
        ))],
    )

    final_text = ""
    turn = 0

    async for event in runner.run_async(
        user_id="system",
        session_id=session.id,
        new_message=content,
    ):
        turn += 1
        if turn > settings.review_agent_max_turns:
            break

        if hasattr(event, "content") and event.content:
            for part in event.content.parts or []:
                if hasattr(part, "function_call") and part.function_call:
                    logger.info(f"Agent tool call: {part.function_call.name}")

        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text = part.text

    return final_text


def run_agent_review(doc_id: int) -> str:
    """Run the review agent (sync wrapper)."""
    _update_progress(doc_id, "reviewing", 3, 70, "Running review agent...")

    try:
        result = asyncio.run(_run_review_agent(doc_id))
        _update_progress(doc_id, "reviewing", 3, 90, "Agent review complete")
        return result
    except Exception as e:
        logger.error(f"Agent review failed (non-fatal): {e}")
        _update_progress(doc_id, "reviewing", 3, 90, f"Agent review failed: {e}")
        return f"Agent review failed: {e}"


# -----------------------------------------------------------------------
# Full pipeline
# -----------------------------------------------------------------------
def process_document(doc_id: int):
    """Run the full pipeline: render → extract → agent review."""
    try:
        doc = db.get_document(doc_id)
        if not doc:
            return

        db.update_document_status(doc_id, "processing")

        # Stage 1: Render pages
        pages = render_pages(doc_id, doc["file_path"])
        logger.info(f"[Doc {doc_id}] Rendered {len(pages)} pages")

        # Stage 2: Extract fields via LLM vision
        fields = extract_fields(doc_id, pages)
        found = sum(1 for f in fields if f.get("found"))
        logger.info(f"[Doc {doc_id}] Extracted {found}/{len(FIELDS)} fields")

        # Stage 3: Agent review
        agent_summary = ""
        if settings.review_agent_enabled:
            agent_summary = run_agent_review(doc_id)
            logger.info(f"[Doc {doc_id}] Agent review done")

        # Done
        _progress[doc_id] = {
            "stage": "completed",
            "stage_number": 3,
            "total_stages": 3,
            "percent": 100,
            "message": "Processing complete",
            "done": True,
            "error": None,
            "agent_summary": agent_summary,
        }
        db.update_document_status(doc_id, "completed")

    except Exception as e:
        logger.exception(f"[Doc {doc_id}] Pipeline failed: {e}")
        _progress[doc_id] = {
            "stage": "error",
            "stage_number": 0,
            "total_stages": 3,
            "percent": 0,
            "message": str(e),
            "done": True,
            "error": str(e),
        }
        db.update_document_status(doc_id, "error", str(e))
