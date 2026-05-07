from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import re
import os
import sys
import json
import socket
import urllib.request
import urllib.error
from dotenv import load_dotenv
from config import load_config
from comparison_explainer import build_comparison_response, is_comparison_query
from rag_engine import (
    HybridRAGIndex,
    extract_legal_keywords,
    get_rights_and_steps,
    assess_urgency,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rights_module.situation_classifier import situation_classifier
from rights_module.rights_handler import handle_rights_query
from rights_module.corpus_loader import load_legal_corpus
from rights_module.compliance_checker import (
    parse_business_input,
    generate_compliance_checklist,
    format_checklist_output,
)

load_dotenv()
APP_CONFIG = load_config()

app = Flask(__name__)
CORS(app)

# ── LLM config ──────────────────────────────────────────────
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

# ── Gemini setup ─────────────────────────────────────────────
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

# ── Paths ────────────────────────────────────────────────────
CONSTITUTION_TEXT_PATH = "constitution.txt"
INDEX_BUILD_LOCK = False

# ── PDF Extraction ───────────────────────────────────────────
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

# ── Build Hybrid RAG Index ───────────────────────────────────
rag_index = HybridRAGIndex()

def build_index():
    global INDEX_BUILD_LOCK
    if INDEX_BUILD_LOCK:
        return
    INDEX_BUILD_LOCK = True
    constitution_pdf_path = "static/constitution.pdf"
    if os.path.exists(constitution_pdf_path):
        if not os.path.exists(CONSTITUTION_TEXT_PATH):
            save_constitution_text()
        with open(CONSTITUTION_TEXT_PATH, "r", encoding="utf-8") as f:
            text = f.read()
        rag_index.build(text, chunk_size=2000, overlap=400, domain="general")
    else:
        print("[WARN] Constitution PDF not found at static/constitution.pdf, skipping constitution loading.")

try:
    build_index()
    load_legal_corpus(os.path.join(os.path.dirname(__file__), "..", "corpus"), rag_index.build)
except Exception as e:
    print(f"[ERROR] Index build failed: {e}")


# ── Gemini-powered analysis ──────────────────────────────────
def build_prompt(query: str, context_chunks: list, chat_history_text: str, provider: str = "generic", domain: str = "unknown") -> str:
    # Strict RAG grounding: always require context_chunks, enforce template
    if not context_chunks:
        print(f"[DEBUG] build_prompt called with no retrieved chunks | chunks_retrieved=0 | top_chunk_text='' | domain_used={domain}")
        return "No relevant legal information found"

    print(f"[DEBUG] build_prompt | chunks_retrieved={len(context_chunks)} | top_chunk_text={context_chunks[0].get('text', '').replace(chr(10), ' ')!r} | domain_used={domain}")

    context = "\n\n".join(c.get('text', '').strip() for c in context_chunks)
    return (
        "You are a legal assistant.\n"
        "Answer ONLY using the provided legal context.\n"
        "Do NOT give general advice.\n"
        "If the answer is not present, say: No relevant legal information found.\n\n"
        "LEGAL CONTEXT:\n"
        f"{context}\n\n"
        "QUESTION:\n"
        f"{query}"
    )


def parse_llm_json(raw: str) -> dict | None:
    cleaned = (raw or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.replace("\ufeff", "")

    decoder = json.JSONDecoder()

    def try_load(text: str) -> dict | None:
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    parsed = try_load(cleaned)
    if parsed is not None:
        return parsed

    # If the model wraps JSON with extra text, decode from the first object start.
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


def gemini_analysis(query: str, context_chunks: list, chat_history_text: str, domain: str) -> dict | None:
    """Call Gemini and ask for a structured JSON response."""
    if not gemini_available or model is None:
        return None

    prompt = build_prompt(query, context_chunks, chat_history_text, provider="gemini", domain=domain)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )
        raw = response.text.strip()
        parsed = parse_llm_json(raw)
        if parsed is None:
            print(f"[WARN] Gemini JSON parse error. Raw: {raw[:300]}")
        return parsed
    except Exception as e:
        print(f"[WARN] Gemini API error: {e}")
        return None


def ollama_analysis(query: str, context_chunks: list, chat_history_text: str, domain: str) -> dict | None:
    """Call Ollama and ask for a structured JSON response."""
    url = OLLAMA_HOST.rstrip("/") + "/api/generate"

    def run_ollama(prompt: str, num_predict: int, timeout: int) -> dict | None:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
        }
        if num_predict > 0:
            payload["options"] = {"num_predict": num_predict}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        raw = (data.get("response") or "").strip()
        parsed = parse_llm_json(raw)
        if parsed is None:
            print(f"[WARN] Ollama JSON parse error. Raw: {raw[:300]}")
        return parsed

    prompt = build_prompt(query, context_chunks, chat_history_text, provider="ollama", domain=domain)
    try:
        return run_ollama(prompt, OLLAMA_NUM_PREDICT, OLLAMA_TIMEOUT)
    except (TimeoutError, socket.timeout):
        # Retry with a smaller prompt and shorter target output before falling back.
        compact_prompt = build_prompt(query, context_chunks[:2], chat_history_text[-500:], provider="ollama", domain=domain)
        compact_predict = min(OLLAMA_NUM_PREDICT, 450) if OLLAMA_NUM_PREDICT > 0 else 450
        try:
            print("[INFO] Ollama timed out; retrying with a compact prompt.")
            return run_ollama(compact_prompt, compact_predict, max(OLLAMA_TIMEOUT, 60))
        except (TimeoutError, socket.timeout) as retry_error:
            print(f"[WARN] Ollama retry timed out: {retry_error}")
            return None
        except urllib.error.URLError as retry_error:
            print(f"[WARN] Ollama retry connection error: {retry_error}")
            return None
    except urllib.error.URLError as e:
        print(f"[WARN] Ollama connection error: {e}")
        return None
    except Exception as e:
        print(f"[WARN] Ollama error: {e}")
        return None


def generate_answer(query: str, chunks: list, chat_history_text: str, domain: str = "unknown") -> dict | str | None:
    """Route LLM generation based on config."""
    # Strict RAG grounding: never call LLM if no chunks
    if not chunks:
        return "No relevant legal information found"

    # Debug logging for RAG pipeline
    print("[RAG DEBUG] Detected domain:", domain)
    print("[RAG DEBUG] Number of chunks retrieved:", len(chunks))
    if chunks:
        print("[RAG DEBUG] Top chunk (first 300 chars):", chunks[0].get('text', '')[:300].replace('\n', ' '))

    # Build prompt and print it before LLM call
    prompt = build_prompt(query, chunks, chat_history_text, provider=LLM_PROVIDER, domain=domain)
    print("[RAG DEBUG] Full prompt sent to LLM:\n" + prompt)

    if LLM_PROVIDER == "ollama":
        # ollama_analysis will rebuild the prompt, but for debug we print it here
        return ollama_analysis(query, chunks, chat_history_text, domain)
    if LLM_PROVIDER == "gemini":
        return gemini_analysis(query, chunks, chat_history_text, domain)
    print(f"[WARN] Unknown llm_provider: {LLM_PROVIDER}")
    return None


def infer_domain(query: str, legal_topics: list[str]) -> str:
    q = query.lower()
    if "consumer" in q or "warranty" in q or "refund" in q or "defect" in q:
        return "consumer"
    if any(t in legal_topics for t in ["right to equality", "right to freedom", "right to education", "police brutality / unlawful arrest"]):
        return "constitutional"
    if any(k in q for k in ["landlord", "tenant", "property", "eviction"]):
        return "property"
    if any(k in q for k in ["divorce", "marriage", "custody", "dowry"]):
        return "family"
    if any(k in q for k in ["wages", "salary", "employee", "labour", "worker"]):
        return "labour"
    return "other"


def build_structured_fallback(query: str, legal_topics: list[str], rights: list[str], next_steps: list[str],
                              chunks: list[dict], meta: dict, disclaimer: str) -> dict:
    article_nums = []
    for c in chunks:
        article_nums.extend(c.get("article_numbers", []))
    article_nums = list(dict.fromkeys(article_nums))[:6]
    sources = list(dict.fromkeys(
        c.get("metadata", {}).get("source", "Retrieved legal corpus") for c in chunks
    ))
    corpus_used = ", ".join(sources) if sources else "Retrieved legal corpus"

    laws = []
    if article_nums and meta.get("domain") == "constitutional":
        laws.append({
            "name": "Constitution of India",
            "type": "primary",
            "why_it_applies": "Retrieved from constitutional context based on your query.",
            "citations": [f"Article {n}" for n in article_nums],
        })
    elif sources:
        laws.append({
            "name": sources[0],
            "type": "primary",
            "why_it_applies": "Retrieved as the most relevant source for this domain-specific query.",
            "citations": sources[:3],
        })

    short_explanation = (
        f"The most relevant retrieved context came from {corpus_used}. "
        "Review the source section and verify the exact legal position with a qualified lawyer."
    )
    if meta.get("in_scope"):
        short_explanation = (
            "Based on the Constitution of India, these are the most relevant rights and steps "
            "for your situation in plain language."
        )

    return {
        "meta": meta,
        "summary": {
            "one_line": f"Based on your query, here is a structured legal brief.",
            "signal": "Consult a lawyer" if not meta.get("in_scope") else "Act promptly",
        },
        "plain_words": {"short_explanation": short_explanation},
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
        "sources": {
            "corpus_used": corpus_used,
            "chunks_retrieved": len(chunks),
        },
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


def build_compliance_response(query: str, business_type: str, employee_count: int, checklist: list[dict]) -> dict:
    """Build a frontend-compatible response for compliance monitor mode."""
    answer = format_checklist_output(checklist, business_type, employee_count)
    sources = list(dict.fromkeys(source for item in checklist for source in item.get("sources", [])))
    complete_count = sum(1 for item in checklist if item.get("status") == "applicable")
    total_count = len(checklist)

    steps = [
        {
            "step_no": idx + 1,
            "timeframe": "Review",
            "action": f"{item.get('status_symbol', '-')} {item['act']}",
            "why": item.get("requirement_summary", ""),
            "urgency_tag": item.get("status", "needs_review"),
        }
        for idx, item in enumerate(checklist)
    ]

    summary = (
        f"Compliance checklist prepared for {business_type.replace('_', ' ')} "
        f"with {employee_count} employees."
    )

    return {
        "query": query,
        "ai_powered": False,
        "urgency": {
            "level": "STANDARD",
            "color": "#10b981",
            "message": "Compliance review checklist",
        },
        "case_type": "Compliance Monitor",
        "summary": summary,
        "analysis": answer,
        "key_points": [
            f"{total_count} applicable acts identified.",
            f"{complete_count} acts have matching indexed source context.",
            "Items marked with x need manual verification or additional corpus coverage.",
        ],
        "is_follow_up": False,
        "legal_topics": ["business compliance", business_type.replace("_", " ")],
        "articles_cited": [],
        "your_rights": [],
        "next_steps": [f"{item.get('status_symbol', '-')} {item['act']}: {item['requirement_summary']}" for item in checklist],
        "retrieved_sections": [],
        "structured": {
            "meta": {
                "domain": "compliance",
                "case_type": "Compliance Monitor",
                "confidence": 85,
                "in_scope": True,
                "ai_powered": False,
                "llm_provider": LLM_PROVIDER,
            },
            "summary": {
                "one_line": summary,
                "signal": "Verify checklist items",
            },
            "plain_words": {
                "short_explanation": "The compliance monitor maps the business type and employee count to likely applicable acts, then retrieves matching indexed sections where available.",
            },
            "parties": {
                "complainant": "Business owner",
                "opposite_party": "Regulators / authorities",
                "subject": query,
                "forum": "Relevant labour, municipal, food safety, and consumer authorities",
            },
            "applicable_laws": [
                {
                    "name": item["act"],
                    "type": "compliance",
                    "why_it_applies": item.get("requirement_summary", ""),
                    "citations": item.get("sources", []),
                }
                for item in checklist
            ],
            "rights_vs_limits": {
                "rights": [],
                "limits": [
                    "This checklist identifies likely requirements; final applicability can depend on state rules, registrations, and exact business facts.",
                ],
            },
            "steps": steps,
            "evidence_checklist": [
                "Employee count records",
                "Wage register and salary slips",
                "Business registration/license documents",
                "Food safety registration if food is served",
            ],
            "do_and_avoid": {
                "do": ["Verify each applicable act with current state rules", "Keep wage and attendance records updated"],
                "avoid": ["Treating this checklist as a final legal audit"],
            },
            "sources": {
                "corpus_used": ", ".join(sources) if sources else "No matching indexed source found",
                "chunks_retrieved": complete_count,
            },
            "compliance_checklist": checklist,
            "followups": ["Show labour compliance only", "Explain Shops Act requirements"],
            "disclaimer": "This is an informational compliance checklist, not legal advice.",
        },
        "explainability": {
            "detected_domain": "compliance",
            "confidence": "high",
            "matched_keywords": [business_type, str(employee_count)],
            "number_of_chunks_used": complete_count,
            "source_documents": sources,
            "short_explanation": "Business type and employee count triggered compliance monitor mode.",
            "retrieval_details": [
                {
                    "act": item["act"],
                    "domain": item.get("domain"),
                    "status": item.get("status"),
                    "sources": item.get("sources", []),
                }
                for item in checklist
            ],
        },
        "disclaimer": "This is an informational compliance checklist, not legal advice.",
    }


# ── Fallback analysis (no Gemini) ────────────────────────────
def fallback_analysis(query: str, chunks: list) -> dict:
    """Produce a structured response purely from RAG-retrieved chunks."""
    corpus_used = "Retrieved legal corpus"
    if chunks:
        sources = [
            c.get("metadata", {}).get("source")
            for c in chunks
            if c.get("metadata", {}).get("source")
        ]
        if sources:
            corpus_used = ", ".join(list(dict.fromkeys(sources))[:3])

    article_nums = []
    for c in chunks:
        article_nums.extend(c.get("article_numbers", []))
    article_nums = list(dict.fromkeys(article_nums))[:6]

    applicable_articles = []
    for c in chunks:
        for num in c.get("article_numbers", [])[:2]:
            # Try to extract article title from the chunk
            title_match = re.search(
                rf'Article\s+{re.escape(num)}\s*[-–—.]?\s*([^\n]{{0,80}})', c["text"]
            )
            title = title_match.group(1).strip() if title_match else c["title"]
            applicable_articles.append({
                "number": f"Article {num}",
                "title": title[:80],
                "relevance": "Retrieved as relevant to your query from the Constitution of India."
            })

    if not applicable_articles and chunks:
        applicable_articles = [{"number": "N/A", "title": chunks[0]["title"], "relevance": "Most relevant section found."}]

    # Extract key sentences from chunks
    key_points = []
    for chunk in chunks[:3]:
        sentences = re.split(r'(?<=[.!?])\s+', chunk["text"])
        for sent in sentences[:2]:
            sent = sent.strip()
            if len(sent) > 40:
                key_points.append(sent[:200])

    return {
        "summary": f"Based on your query about \"{query[:100]}\", relevant sections from {corpus_used} have been retrieved. AI-powered analysis is temporarily unavailable, but grounded source text is shown below.",
        "analysis": f"The following retrieved legal sections from {corpus_used} are relevant to your situation. Please review the source text and consult a qualified legal professional for advice on your facts.",
        "key_points": key_points[:5] if key_points else ["Please review the retrieved constitutional articles below."],
        "applicable_articles": applicable_articles[:5],
        "case_type": "Legal Corpus Query",
        "is_follow_up": False,
        "fallback": True,
    }


# ── Main endpoint ────────────────────────────────────────────
@app.route('/legal-help', methods=['POST'])
def legal_help():
    data = request.json
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    query: str = data["query"].strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    if is_comparison_query(query):
        return jsonify(build_comparison_response(query))

    business_info = parse_business_input(query)
    if business_info.get("business_type") and business_info.get("employee_count") is not None:
        checklist = generate_compliance_checklist(
            business_info["business_type"],
            business_info["employee_count"],
            rag_index.retrieve,
        )
        return jsonify(build_compliance_response(
            query,
            business_info["business_type"],
            business_info["employee_count"],
            checklist,
        ))

    chat_history_list = data.get("chat_history", [])
    chat_history_text = ""
    if chat_history_list:
        for msg in chat_history_list[-6:]:  # last 3 exchanges
            role = "User" if msg.get("role") == "user" else "Assistant"
            chat_history_text += f"{role}: {msg.get('text', '')[:500]}\n\n"

    # 1. Domain-aware retrieval
    classification = situation_classifier(query)
    domain_filter = classification["domain"]
    if domain_filter is not None:
        print(f"Detected domain: {domain_filter} (confidence: {classification['confidence']}) — matched: {classification['matched_keywords']}")
    else:
        print("No specific domain detected — searching all documents")

    try:
        chunks = rag_index.retrieve(query, top_k=5, domain_filter=domain_filter)
    except Exception as e:
        print(f"[ERROR] Retrieval failed: {e}")
        chunks = []

    # 2. Extract supporting metadata
    legal_keywords = extract_legal_keywords(query, chunks)
    rights, next_steps = get_rights_and_steps(query)
    urgency = assess_urgency(query)

    top_score = chunks[0]["score"] if chunks else 0
    top_matched = 0
    if chunks and chunks[0].get("score_breakdown"):
        top_matched = len(chunks[0]["score_breakdown"].get("matched_terms", []))
    domain = domain_filter or infer_domain(query, legal_keywords)
    in_scope = domain == "constitutional" and top_score >= 8 and top_matched >= 2
    confidence = 25
    if in_scope:
        confidence = 60
        if top_score >= 12:
            confidence = 85
        elif top_score >= 10:
            confidence = 75

    # 3. AI generation (provider or fallback)
    ai_result = None
    # Strict RAG grounding: never call LLM if no chunks, always use prompt template
    if chunks:
        ai_result = generate_answer(query, chunks, chat_history_text, domain)
    else:
        ai_result = "No relevant legal information found"

    if isinstance(ai_result, str):
        if ai_result == "No relevant legal information found":
            ai_powered = False
        else:
            ai_powered = False
        ai_result = {
            "analysis": ai_result,
            "summary": ai_result,
            "key_points": [],
            "is_follow_up": False,
        }
    elif ai_result is None:
        ai_result = fallback_analysis(query, chunks)
        ai_powered = False
    else:
        ai_powered = True

    # 4. Build article references from both AI output and RAG
    article_refs = ai_result.get("applicable_articles", [])

    # 5. Build retrieved sections for display
    retrieved_sections = [
        {
            "title": c["title"],
            "excerpt": c["text"][:800],
            "score": c["score"],
            "article_numbers": c["article_numbers"],
            "score_breakdown": c.get("score_breakdown"),
            "metadata": c.get("metadata", {}),
        }
        for c in chunks
    ]

    meta = {
        "domain": domain,
        "case_type": ai_result.get("case_type", "Legal Query"),
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
    case_type = meta["case_type"]
    if isinstance(ai_result, dict) and "meta" in ai_result:
        structured = deep_merge(structured, ai_result)
        case_type = ai_result.get("meta", {}).get("case_type") or case_type
    structured["meta"] = {**meta, "case_type": case_type}

    has_structured = isinstance(ai_result, dict) and "meta" in ai_result
    summary_text = structured.get("summary", {}).get("one_line", "") if has_structured else ai_result.get("summary", "")
    analysis_text = ai_result.get("analysis", "")
    if has_structured and not analysis_text:
        analysis_text = structured.get("plain_words", {}).get("short_explanation", "")
    rights_points = structured.get("rights_vs_limits", {}).get("rights", [])
    limits_points = structured.get("rights_vs_limits", {}).get("limits", [])
    key_points = ai_result.get("key_points", [])
    if not key_points:
        key_points = rights_points[:3] + limits_points[:2]

    if not article_refs and structured.get("applicable_laws"):
        derived = []
        for law in structured.get("applicable_laws", []):
            for citation in law.get("citations", [])[:2]:
                derived.append({
                    "number": citation,
                    "title": law.get("name", ""),
                    "relevance": law.get("why_it_applies", ""),
                })
        article_refs = derived

    # Explainability metadata

    retrieval_details = []
    for c in chunks:
        score_breakdown = c.get("score_breakdown", {})
        retrieval_details.append({
            "text_preview": c.get("text", "")[:150],
            "domain": c.get("metadata", {}).get("domain", "unknown"),
            "score": {
                "bm25": score_breakdown.get("bm25"),
                "cosine": score_breakdown.get("cosine"),
                "hybrid": score_breakdown.get("hybrid"),
            }
        })

    explainability = {
        "detected_domain": classification.get("domain"),
        "confidence": classification.get("confidence"),
        "matched_keywords": classification.get("matched_keywords", []),
        "number_of_chunks_used": len(chunks),
        "source_documents": list(dict.fromkeys(
            c.get("metadata", {}).get("source", "Unknown source") for c in chunks
        )),
        "short_explanation": f"Domain '{classification.get('domain')}' was selected because the following keywords matched: {', '.join(classification.get('matched_keywords', [])) or 'none found'}.",
        "retrieval_details": retrieval_details,
    }

    response = {
        "query": query,
        "ai_powered": ai_powered,
        "urgency": urgency,
        "case_type": meta["case_type"],
        "summary": summary_text or ai_result.get("summary", ""),
        "analysis": analysis_text or ai_result.get("analysis", ""),
        "key_points": key_points or ai_result.get("key_points", []),
        "is_follow_up": ai_result.get("is_follow_up", False),
        "legal_topics": legal_keywords,
        "articles_cited": article_refs,
        "your_rights": rights,
        "next_steps": next_steps,
        "retrieved_sections": retrieved_sections,
        "structured": structured,
        "explainability": explainability,
        "disclaimer": "This is AI-generated legal information for educational purposes only. It does not constitute legal advice. Please consult a qualified lawyer for your specific situation.",
    }
    return jsonify(response)


def test_rights_module():
    """
    Run basic integration tests for rights module retrieval modes.
    """
    corpus_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "corpus"))
    load_legal_corpus(corpus_path, rag_index.build)

    tests = [
        {
            "mode": "situation",
            "query": "My employer fired me without notice and hasn't paid my last month salary",
        },
        {
            "mode": "compliance",
            "query": "I run a restaurant with 12 employees in Maharashtra",
        },
        {
            "mode": "direct",
            "query": "What are my fundamental rights under the Indian constitution?",
        },
    ]

    for test in tests:
        result = handle_rights_query(test["query"], rag_index.retrieve, mode=test["mode"])
        preview = result["answer"] if result["answer"] else ""
        print("Query:", test["query"])
        print("Mode used:", result.get("mode_used"))
        print("Domain detected:", result.get("domain_detected"))
        safe_preview = preview[:300].replace("\n", " ").encode('ascii', 'replace').decode('ascii')
        print("Output preview:", safe_preview)
        print("-" * 80)


@app.route('/health', methods=['GET'])
def health():
    domain_counts = {}
    for chunk in rag_index.chunks:
        domain = chunk.get("metadata", {}).get("domain", "unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    return jsonify({
        "status": "ok",
        "gemini_available": gemini_available,
        "ai_available": (LLM_PROVIDER == "ollama") or gemini_available,
        "llm_provider": LLM_PROVIDER,
        "index_chunks": len(rag_index.chunks),
        "domain_counts": domain_counts,
    })


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5555, debug=True)
