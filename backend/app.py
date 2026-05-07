from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import re
import socket
import tempfile
import urllib.error
import urllib.request

import PyPDF2
from dotenv import load_dotenv

from config import load_config
from document_intelligence import (
    DocumentCorpusStore,
    analyze_contract,
    decode_court_notice,
    extract_text,
)
from legal_doc_intel import build_legal_document_report
from rag_engine import (
    HybridRAGIndex,
    assess_urgency,
    extract_legal_keywords,
    get_rights_and_steps,
)

load_dotenv()
APP_CONFIG = load_config()

app = Flask(__name__)
CORS(app)

LLM_PROVIDER = APP_CONFIG.get("llm_provider", "gemini")
GEMINI_MODEL = APP_CONFIG.get("gemini_model", "gemini-1.5-flash")
OLLAMA_MODEL = APP_CONFIG.get("ollama_model", "phi3")
OLLAMA_HOST = APP_CONFIG.get("ollama_host", "http://localhost:11434")
try:
    OLLAMA_TIMEOUT = max(60, int(APP_CONFIG.get("ollama_timeout", 180)))
except (TypeError, ValueError):
    OLLAMA_TIMEOUT = 180
try:
    OLLAMA_NUM_PREDICT = int(APP_CONFIG.get("ollama_num_predict", 900))
except (TypeError, ValueError):
    OLLAMA_NUM_PREDICT = 900

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_available = False
model = None
if GEMINI_API_KEY and LLM_PROVIDER == "gemini":
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        gemini_available = True
        print("[INFO] Gemini model initialized successfully.")
    except Exception as e:
        print(f"[WARN] Gemini init failed: {e}")

CONSTITUTION_TEXT_PATH = "constitution.txt"
INDEX_BUILD_LOCK = False
rag_index = HybridRAGIndex()
doc_store = DocumentCorpusStore()


def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text


def save_constitution_text():
    pdf_path = "static/constitution.pdf"
    constitution_text = extract_text_from_pdf(pdf_path)
    with open(CONSTITUTION_TEXT_PATH, "w", encoding="utf-8") as f:
        f.write(constitution_text)
    print("[INFO] Constitution text extracted from PDF.")


def build_index():
    global INDEX_BUILD_LOCK
    if INDEX_BUILD_LOCK:
        return
    INDEX_BUILD_LOCK = True
    if not os.path.exists(CONSTITUTION_TEXT_PATH):
        save_constitution_text()
    with open(CONSTITUTION_TEXT_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    extra_corpus = doc_store.combined_text()
    if extra_corpus.strip():
        text = f"{text}\n\n{extra_corpus}"
    rag_index.build(text, chunk_size=2000, overlap=400)


try:
    build_index()
except Exception as e:
    print(f"[ERROR] Index build failed: {e}")


def parse_llm_json(raw: str):
    cleaned = (raw or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.replace("\ufeff", "")

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(cleaned):
        if ch != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(cleaned[idx:])
            if isinstance(candidate, dict):
                return candidate
        except json.JSONDecodeError:
            continue
    return None


def build_prompt(query: str, context_chunks: list, chat_history_text: str) -> str:
    context = "\n\n".join(f"[{c['title']}]\n{c['text'][:1000]}" for c in context_chunks)
    return f"""You are an expert Legal AI Assistant specializing in Indian Constitutional Law.
Return valid JSON only.

CONSTITUTIONAL CONTEXT:
{context}

CONVERSATION HISTORY:
{chat_history_text or "No previous conversation."}

USER QUERY:
{query}

Use this exact shape:
{{
  "meta": {{
    "domain": "constitutional | consumer | labour | property | family | other",
    "case_type": "Short case type tag",
    "confidence": 0,
    "in_scope": true,
    "ai_powered": true,
    "llm_provider": "ollama | gemini"
  }},
  "analysis": "Short analysis",
  "key_points": ["Point 1", "Point 2", "Point 3"],
  "summary": {{"one_line": "One-line summary", "signal": "Act promptly"}},
  "plain_words": {{"short_explanation": "Simple explanation"}},
  "parties": {{"complainant": "", "opposite_party": "", "subject": "", "forum": ""}},
  "applicable_laws": [{{"name": "Constitution of India", "type": "primary", "why_it_applies": "", "citations": ["Article 21"]}}],
  "rights_vs_limits": {{"rights": [], "limits": []}},
  "steps": [{{"step_no": 1, "timeframe": "Day 0", "action": "", "why": "", "urgency_tag": ""}}],
  "evidence_checklist": [],
  "do_and_avoid": {{"do": [], "avoid": []}},
  "followups": [],
  "disclaimer": "Short legal disclaimer"
}}"""


def gemini_analysis(query: str, context_chunks: list, chat_history_text: str):
    if not gemini_available or model is None:
        return None
    prompt = build_prompt(query, context_chunks, chat_history_text)
    try:
        response = model.generate_content(prompt)
        return parse_llm_json((response.text or "").strip())
    except Exception as e:
        print(f"[WARN] Gemini error: {e}")
        return None


def ollama_analysis(query: str, context_chunks: list, chat_history_text: str):
    prompt = build_prompt(query, context_chunks, chat_history_text)
    url = OLLAMA_HOST.rstrip("/") + "/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"num_predict": OLLAMA_NUM_PREDICT},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return parse_llm_json((data.get("response") or "").strip())
    except (TimeoutError, socket.timeout, urllib.error.URLError, Exception) as e:
        print(f"[WARN] Ollama error: {e}")
        return None


def generate_answer(query: str, chunks: list, chat_history_text: str):
    if LLM_PROVIDER == "gemini":
        return gemini_analysis(query, chunks, chat_history_text)
    if LLM_PROVIDER == "ollama":
        return ollama_analysis(query, chunks, chat_history_text)
    return None


def generate_text_report(prompt: str) -> str:
    if LLM_PROVIDER == "gemini" and gemini_available and model is not None:
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=4096,
                ),
            )
            return (response.text or "").strip()
        except Exception as e:
            print(f"[WARN] Gemini text generation error: {e}")
            return ""

    if LLM_PROVIDER == "ollama":
        url = OLLAMA_HOST.rstrip("/") + "/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 4096, "temperature": 0},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return (data.get("response") or "").strip()
        except Exception as e:
            print(f"[WARN] Ollama text generation error: {e}")
            return ""

    return ""


def infer_domain(query: str, legal_topics: list[str]) -> str:
    q = query.lower()
    if "consumer" in q or "warranty" in q or "refund" in q or "defect" in q:
        return "consumer"
    if any(
        t in legal_topics
        for t in [
            "right to equality",
            "right to freedom",
            "right to education",
            "police brutality / unlawful arrest",
        ]
    ):
        return "constitutional"
    if any(k in q for k in ["landlord", "tenant", "property", "eviction"]):
        return "property"
    if any(k in q for k in ["divorce", "marriage", "custody", "dowry"]):
        return "family"
    if any(k in q for k in ["wages", "salary", "employee", "labour", "worker"]):
        return "labour"
    return "other"


def build_structured_fallback(query, legal_topics, rights, next_steps, chunks, meta, disclaimer):
    article_nums = []
    for c in chunks:
        article_nums.extend(c.get("article_numbers", []))
    article_nums = list(dict.fromkeys(article_nums))[:6]

    laws = []
    if article_nums:
        laws.append(
            {
                "name": "Constitution of India",
                "type": "primary",
                "why_it_applies": "Retrieved from constitutional context based on your query.",
                "citations": [f"Article {n}" for n in article_nums],
            }
        )

    return {
        "meta": meta,
        "summary": {"one_line": "Structured legal guidance generated.", "signal": "Act promptly"},
        "plain_words": {"short_explanation": "Based on constitutional context and matching patterns."},
        "parties": {
            "complainant": "You (the user)",
            "opposite_party": "Relevant authority or party mentioned",
            "subject": query[:120],
            "forum": "Relevant authority or commission",
        },
        "applicable_laws": laws,
        "rights_vs_limits": {
            "rights": rights[:6],
            "limits": [
                "This is informational guidance only.",
                "Specific legal advice requires a qualified lawyer.",
            ],
        },
        "steps": [
            {
                "step_no": i + 1,
                "timeframe": f"Day {i + 1}-{i + 2}",
                "action": s,
                "why": "Practical next step based on your situation.",
                "urgency_tag": "Action",
            }
            for i, s in enumerate(next_steps[:5])
        ],
        "forum_comparison": {"forums": [], "rows": []},
        "relief_spectrum": [],
        "case_strength": [],
        "cost_benefit": {"invest": [], "recover": []},
        "clause_risks": [],
        "evidence_checklist": ["Relevant documents", "Receipts, notices, or records"],
        "do_and_avoid": {
            "do": ["Keep written records", "Document key dates"],
            "avoid": ["Relying only on verbal communication"],
        },
        "misconceptions": [],
        "similar_cases": [],
        "sources": {"corpus_used": "Constitution of India", "chunks_retrieved": len(chunks)},
        "followups": ["Draft a formal notice", "Prepare a complaint summary"],
        "disclaimer": disclaimer,
    }


def deep_merge(base: dict, update: dict) -> dict:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = deep_merge(base[key], value)
        elif value not in (None, "", [], {}):
            base[key] = value
    return base


@app.route("/legal-help", methods=["POST"])
def legal_help():
    data = request.json
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    query = data["query"].strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    chat_history_list = data.get("chat_history", [])
    chat_history_text = ""
    if chat_history_list:
        for msg in chat_history_list[-6:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            chat_history_text += f"{role}: {msg.get('text', '')[:500]}\n\n"

    try:
        chunks = rag_index.retrieve(query, top_k=5)
    except Exception as e:
        print(f"[ERROR] Retrieval failed: {e}")
        chunks = []

    legal_keywords = extract_legal_keywords(query, chunks)
    rights, next_steps = get_rights_and_steps(query)
    urgency = assess_urgency(query)

    top_score = chunks[0]["score"] if chunks else 0
    top_matched = 0
    if chunks and chunks[0].get("score_breakdown"):
        top_matched = len(chunks[0]["score_breakdown"].get("matched_terms", []))
    domain = infer_domain(query, legal_keywords)
    in_scope = domain == "constitutional" and top_score >= 8 and top_matched >= 2
    confidence = 75 if in_scope else 30

    ai_result = generate_answer(query, chunks, chat_history_text) if in_scope else None
    ai_powered = bool(ai_result)

    meta = {
        "domain": domain,
        "case_type": (ai_result or {}).get("case_type", "Legal Query"),
        "confidence": confidence,
        "in_scope": in_scope,
        "ai_powered": ai_powered,
        "llm_provider": LLM_PROVIDER,
    }

    structured = build_structured_fallback(
        query,
        legal_keywords,
        rights,
        next_steps,
        chunks,
        meta,
        "This is AI-generated legal information for educational purposes only. It does not constitute legal advice. Please consult a qualified lawyer for your specific situation.",
    )
    if isinstance(ai_result, dict) and "meta" in ai_result:
        structured = deep_merge(structured, ai_result)

    retrieved_sections = [
        {
            "title": c["title"],
            "excerpt": c["text"][:800],
            "score": c["score"],
            "article_numbers": c["article_numbers"],
            "score_breakdown": c.get("score_breakdown"),
        }
        for c in chunks
    ]

    return jsonify(
        {
            "query": query,
            "ai_powered": ai_powered,
            "urgency": urgency,
            "case_type": structured.get("meta", {}).get("case_type", "Legal Query"),
            "summary": structured.get("summary", {}).get("one_line", ""),
            "analysis": structured.get("analysis", structured.get("plain_words", {}).get("short_explanation", "")),
            "key_points": structured.get("key_points", []),
            "is_follow_up": False,
            "legal_topics": legal_keywords,
            "articles_cited": structured.get("applicable_laws", []),
            "your_rights": rights,
            "next_steps": next_steps,
            "retrieved_sections": retrieved_sections,
            "structured": structured,
            "disclaimer": "This is AI-generated legal information for educational purposes only. It does not constitute legal advice. Please consult a qualified lawyer for your specific situation.",
        }
    )


@app.route("/document-intel/upload", methods=["POST"])
def upload_document():
    global INDEX_BUILD_LOCK
    if "file" not in request.files:
        return jsonify({"error": "Upload a file in multipart form-data under key 'file'."}), 400

    uploaded = request.files["file"]
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "No file selected."}), 400

    suffix = os.path.splitext(uploaded.filename)[1] or ".bin"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            uploaded.save(tmp.name)
            tmp_path = tmp.name

        text = extract_text(tmp_path)
        if not text.strip():
            return jsonify({"error": "No readable text found in the uploaded document."}), 422

        doc = doc_store.add(uploaded.filename, text)
        INDEX_BUILD_LOCK = False
        build_index()
        return jsonify(
            {
                "status": "ok",
                "doc_id": doc.doc_id,
                "name": doc.name,
                "chars_extracted": len(text),
                "uploaded_docs": doc_store.list_docs(),
                "index_chunks": len(rag_index.chunks),
            }
        )
    except Exception as e:
        return jsonify({"error": f"Document ingestion failed: {e}"}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route("/document-intel/summarize", methods=["POST"])
def summarize_document():
    if "file" not in request.files:
        return jsonify({"error": "Upload a file in multipart form-data under key 'file'."}), 400

    uploaded = request.files["file"]
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "No file selected."}), 400

    export_pdf = str(request.form.get("export_pdf", "false")).lower() == "true"
    export_docx = str(request.form.get("export_docx", "false")).lower() == "true"

    suffix = os.path.splitext(uploaded.filename)[1] or ".bin"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            uploaded.save(tmp.name)
            tmp_path = tmp.name

        llm_fn = generate_text_report if ((LLM_PROVIDER == "ollama") or gemini_available) else None
        report = build_legal_document_report(
            file_path=tmp_path,
            filename=uploaded.filename,
            llm_text_fn=llm_fn,
            export_pdf=export_pdf,
            export_docx=export_docx,
        )
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": f"Document summarization failed: {e}"}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route("/document-intel/contract-analyze", methods=["POST"])
def contract_analyze():
    data = request.json or {}
    contract_text = (data.get("text") or "").strip()
    if not contract_text:
        return jsonify({"error": "Missing 'text' in request body."}), 400
    return jsonify(analyze_contract(contract_text, rag_index))


@app.route("/document-intel/court-notice-decode", methods=["POST"])
def court_notice_decode():
    data = request.json or {}
    notice_text = (data.get("text") or "").strip()
    if not notice_text:
        return jsonify({"error": "Missing 'text' in request body."}), 400
    return jsonify(decode_court_notice(notice_text, rag_index))


@app.route("/", methods=["GET"])
def home():
    return jsonify(
        {
            "service": "NyayaSetu Backend API",
            "status": "ok",
            "message": "Backend is running. Open frontend on http://localhost:3000",
            "endpoints": [
                "/health",
                "/legal-help",
                "/document-intel/upload",
                "/document-intel/summarize",
                "/document-intel/contract-analyze",
                "/document-intel/court-notice-decode",
            ],
        }
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "gemini_available": gemini_available,
            "ai_available": (LLM_PROVIDER == "ollama") or gemini_available,
            "llm_provider": LLM_PROVIDER,
            "index_chunks": len(rag_index.chunks),
            "uploaded_docs": len(doc_store.list_docs()),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555, debug=True)
