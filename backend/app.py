from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import re
import os
import json
import socket
import urllib.request
import urllib.error
from dotenv import load_dotenv
from config import load_config
from rag_engine import (
    HybridRAGIndex,
    extract_legal_keywords,
    get_rights_and_steps,
    assess_urgency,
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
    if not os.path.exists(CONSTITUTION_TEXT_PATH):
        save_constitution_text()
    with open(CONSTITUTION_TEXT_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    rag_index.build(text, chunk_size=2000, overlap=400)

try:
    build_index()
except Exception as e:
    print(f"[ERROR] Index build failed: {e}")


# ── Gemini-powered analysis ──────────────────────────────────
def build_prompt(query: str, context_chunks: list, chat_history_text: str, provider: str = "generic") -> str:
    context = "\n\n".join(
        f"[{c['title']}]\n{c['text'][:1200]}" for c in context_chunks
    )
    if provider == "ollama":
        template = """You are an expert Legal AI Assistant specializing in Indian Constitutional Law.
Your task is to analyze the user's legal scenario and produce a STRICT JSON response.

CONSTITUTIONAL CONTEXT (from RAG retrieval):
{context}

CONVERSATION HISTORY:
{chat_history}

USER'S SCENARIO:
{query}

INSTRUCTIONS:
- Analyze the scenario in plain, simple language that a common person can understand.
- Ground your response in the constitutional context provided. Do NOT hallucinate laws.
- Be concise. Keep every string short and every list to at most 3 items.
- Return JSON only. No markdown, no code fences, no explanation before or after JSON.
- Choose one single value for `meta.domain`.
- If a field is unknown, use an empty string or empty array.
- Ensure the final character of your answer is `}}`.

RESPOND WITH ONLY THIS JSON SHAPE:
{{
  "meta": {{
    "domain": "constitutional",
    "case_type": "Short case type tag",
    "confidence": 0,
    "in_scope": true,
    "ai_powered": true,
    "llm_provider": "ollama"
  }},
  "analysis": "2-3 short paragraphs",
  "key_points": ["Point 1", "Point 2", "Point 3"],
  "summary": {{
    "one_line": "One-line summary",
    "signal": "Act quickly"
  }},
  "plain_words": {{
    "short_explanation": "2-4 short sentences in plain words"
  }},
  "parties": {{
    "complainant": "Who is affected",
    "opposite_party": "Who is responsible",
    "subject": "What the issue is about",
    "forum": "Likely forum or authority"
  }},
  "applicable_laws": [
    {{
      "name": "Constitution of India",
      "type": "primary",
      "why_it_applies": "Short reason",
      "citations": ["Article 21"]
    }}
  ],
  "rights_vs_limits": {{
    "rights": ["Right 1", "Right 2"],
    "limits": ["Limit 1", "Limit 2"]
  }},
  "steps": [
    {{
      "step_no": 1,
      "timeframe": "Day 0",
      "action": "Action",
      "why": "Why this helps",
      "urgency_tag": "Do immediately"
    }}
  ],
  "evidence_checklist": ["Document 1", "Document 2"],
  "do_and_avoid": {{
    "do": ["Do this"],
    "avoid": ["Avoid this"]
  }},
  "followups": ["Draft a notice"],
  "disclaimer": "Short legal disclaimer"
}}"""
    else:
        template = """You are an expert Legal AI Assistant specializing in Indian Constitutional Law.
Your task is to analyze the user's legal scenario and produce a STRICT JSON response.

CONSTITUTIONAL CONTEXT (from RAG retrieval):
{context}

CONVERSATION HISTORY:
{chat_history}

USER'S SCENARIO:
{query}

INSTRUCTIONS:
- Analyze the scenario in plain, simple language that a common person can understand.
- Ground your response in the constitutional context provided. Do NOT hallucinate laws.
- If the user's scenario is a follow-up, be conversational and contextual.
- Keep the output concise to avoid truncation:
    - Analysis: max 3 short paragraphs, 2-3 sentences each.
    - Lists: max 3-4 items; use empty arrays if unknown.
    - Strings: keep under 160 characters where possible.
    - Choose a single value for `meta.domain` (do not list options).
- Return valid JSON only and ensure the JSON ends with a closing `}}`.

RESPOND ONLY WITH VALID JSON in this exact structure (no markdown, no code fences):
{{
    "meta": {{
        "domain": "constitutional | consumer | labour | property | family | other",
        "case_type": "Short case type tag",
        "confidence": 0,
        "in_scope": true,
        "ai_powered": true,
        "llm_provider": "ollama | gemini"
    }},
    "analysis": "Detailed 5-8 paragraph narrative analysis",
    "key_points": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
    "summary": {{
        "one_line": "One-line summary",
        "signal": "Act quickly | Low urgency | Consult a lawyer"
    }},
    "plain_words": {{
        "short_explanation": "2-4 sentences in plain words"
    }},
    "parties": {{
        "complainant": "Who is affected",
        "opposite_party": "Who is responsible",
        "subject": "What the issue is about",
        "forum": "Likely forum / authority"
    }},
    "applicable_laws": [
        {{"name": "Law name", "type": "primary | supporting", "why_it_applies": "Short reason", "citations": ["Article 21", "Section 12"]}}
    ],
    "rights_vs_limits": {{
        "rights": ["Right 1", "Right 2"],
        "limits": ["Limit 1", "Limit 2"]
    }},
    "steps": [
        {{"step_no": 1, "timeframe": "Day 0", "action": "Action", "why": "Why this helps", "urgency_tag": "Do immediately"}}
    ],
    "forum_comparison": {{
        "forums": ["Consumer Commission", "Civil Court", "Lok Adalat"],
        "rows": [
            {{"factor": "Filing fee", "values": ["₹200-₹2,000", "₹5,000-₹50,000+", "Free"]}}
        ]
    }},
    "relief_spectrum": [
        {{"label": "Refund", "range": "Full price", "likelihood": 80, "level": "high"}}
    ],
    "case_strength": [
        {{"label": "Evidence", "score": 70, "note": "Receipts and complaint trail"}}
    ],
    "cost_benefit": {{
        "invest": [
            {{"item": "Filing fee", "amount": "₹200", "note": "CONFONET"}}
        ],
        "recover": [
            {{"item": "Refund", "amount": "Full price", "note": "If granted"}}
        ]
    }},
    "clause_risks": [
        {{"clause": "Non-compete", "risk_level": "high", "issue": "Overbroad duration", "fix": "Limit to 12 months"}}
    ],
    "evidence_checklist": ["Document 1", "Document 2"],
    "do_and_avoid": {{
        "do": ["Do this"],
        "avoid": ["Avoid this"]
    }},
    "misconceptions": [
        {{"claim": "Myth", "truth": "True/False", "explanation": "Short clarification"}}
    ],
    "similar_cases": [
        {{"court": "Court", "year": 2022, "case_name": "Case", "outcome": "Outcome", "similarity": "85%"}}
    ],
    "sources": {{
        "corpus_used": "Constitution of India",
        "chunks_retrieved": 0
    }},
    "followups": ["Draft a notice", "How to file online"],
    "disclaimer": "Short legal disclaimer"
}}"""
    return template.format(
        context=context,
        chat_history=chat_history_text or "No previous conversation.",
        query=query,
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


def gemini_analysis(query: str, context_chunks: list, chat_history_text: str) -> dict | None:
    """Call Gemini and ask for a structured JSON response."""
    if not gemini_available or model is None:
        return None

    prompt = build_prompt(query, context_chunks, chat_history_text, provider="gemini")

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


def ollama_analysis(query: str, context_chunks: list, chat_history_text: str) -> dict | None:
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

    prompt = build_prompt(query, context_chunks, chat_history_text, provider="ollama")
    try:
        return run_ollama(prompt, OLLAMA_NUM_PREDICT, OLLAMA_TIMEOUT)
    except (TimeoutError, socket.timeout):
        # Retry with a smaller prompt and shorter target output before falling back.
        compact_prompt = build_prompt(query, context_chunks[:2], chat_history_text[-500:], provider="ollama")
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


def generate_answer(query: str, chunks: list, chat_history_text: str) -> dict | None:
    """Route LLM generation based on config."""
    if LLM_PROVIDER == "ollama":
        return ollama_analysis(query, chunks, chat_history_text)
    if LLM_PROVIDER == "gemini":
        return gemini_analysis(query, chunks, chat_history_text)
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

    laws = []
    if article_nums:
        laws.append({
            "name": "Constitution of India",
            "type": "primary",
            "why_it_applies": "Retrieved from constitutional context based on your query.",
            "citations": [f"Article {n}" for n in article_nums],
        })

    short_explanation = (
        "This issue appears outside the current constitutional corpus. "
        "I can provide general guidance, but specific citations may be unavailable."
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
            "corpus_used": "Constitution of India",
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


# ── Fallback analysis (no Gemini) ────────────────────────────
def fallback_analysis(query: str, chunks: list) -> dict:
    """Produce a structured response purely from RAG-retrieved chunks."""
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
        "summary": f"Based on your query about \"{query[:100]}\", relevant sections of the Constitution of India have been retrieved. AI-powered analysis is temporarily unavailable, but key constitutional provisions are shown below.",
        "analysis": "The following constitutional provisions are relevant to your situation. Please review the 'Articles' tab for the exact text from the Constitution of India. We recommend consulting a qualified legal professional for personalized advice based on these provisions.",
        "key_points": key_points[:5] if key_points else ["Please review the retrieved constitutional articles below."],
        "applicable_articles": applicable_articles[:5],
        "case_type": "Constitutional Query",
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

    chat_history_list = data.get("chat_history", [])
    chat_history_text = ""
    if chat_history_list:
        for msg in chat_history_list[-6:]:  # last 3 exchanges
            role = "User" if msg.get("role") == "user" else "Assistant"
            chat_history_text += f"{role}: {msg.get('text', '')[:500]}\n\n"

    # 1. RAG retrieval
    try:
        chunks = rag_index.retrieve(query, top_k=5)
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
    domain = infer_domain(query, legal_keywords)
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
    if in_scope:
        ai_result = generate_answer(query, chunks, chat_history_text)
    if ai_result is None:
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

    return jsonify({
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
        "disclaimer": "This is AI-generated legal information for educational purposes only. It does not constitute legal advice. Please consult a qualified lawyer for your specific situation.",
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "gemini_available": gemini_available,
        "ai_available": (LLM_PROVIDER == "ollama") or gemini_available,
        "llm_provider": LLM_PROVIDER,
        "index_chunks": len(rag_index.chunks),
    })


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5555, debug=True)
