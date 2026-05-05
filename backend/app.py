from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import re
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from rag_engine import (
    HybridRAGIndex,
    extract_legal_keywords,
    get_rights_and_steps,
    assess_urgency,
)

load_dotenv()

app = Flask(__name__)
CORS(app)

# ── Gemini setup ─────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_available = False
model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
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
def gemini_analysis(query: str, context_chunks: list, chat_history_text: str) -> dict | None:
    """Call Gemini and ask for a structured JSON response."""
    if not gemini_available or model is None:
        return None

    context = "\n\n".join(
        f"[{c['title']}]\n{c['text'][:1200]}" for c in context_chunks
    )

    prompt = f"""You are an expert Legal AI Assistant specializing in Indian Constitutional Law.
Your task is to analyze the user's legal scenario and produce a STRICT JSON response.

CONSTITUTIONAL CONTEXT (from RAG retrieval):
{context}

CONVERSATION HISTORY:
{chat_history_text or "No previous conversation."}

USER'S SCENARIO:
{query}

INSTRUCTIONS:
- Analyze the scenario deeply in plain, simple language that a common person can understand.
- Ground your response in the constitutional context provided. Do NOT hallucinate laws.
- If the user's scenario is a follow-up, be conversational and contextual.

RESPOND ONLY WITH VALID JSON in this exact structure (no markdown, no code fences):
{{
  "summary": "A 2-3 sentence plain-language summary of the legal situation",
  "analysis": "A detailed 5-8 paragraph analysis covering what happened legally, which rights are involved, what the law says, and what the person should do. Use simple language.",
  "key_points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "applicable_articles": [
    {{"number": "Article X", "title": "Title of Article", "relevance": "How this article applies to the case"}}
  ],
  "case_type": "Type of legal case (e.g. Motor Accident, Property Dispute, etc.)",
  "is_follow_up": true or false
}}"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )
        raw = response.text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        return parsed
    except json.JSONDecodeError as e:
        print(f"[WARN] Gemini JSON parse error: {e}\nRaw: {raw[:300]}")
        return None
    except Exception as e:
        print(f"[WARN] Gemini API error: {e}")
        return None


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

    # 3. AI generation (Gemini or fallback)
    ai_result = gemini_analysis(query, chunks, chat_history_text)
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
        }
        for c in chunks
    ]

    return jsonify({
        "query": query,
        "ai_powered": ai_powered,
        "urgency": urgency,
        "case_type": ai_result.get("case_type", "Legal Query"),
        "summary": ai_result.get("summary", ""),
        "analysis": ai_result.get("analysis", ""),
        "key_points": ai_result.get("key_points", []),
        "is_follow_up": ai_result.get("is_follow_up", False),
        "legal_topics": legal_keywords,
        "articles_cited": article_refs,
        "your_rights": rights,
        "next_steps": next_steps,
        "retrieved_sections": retrieved_sections,
        "disclaimer": "This is AI-generated legal information for educational purposes only. It does not constitute legal advice. Please consult a qualified lawyer for your specific situation.",
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "gemini_available": gemini_available,
        "index_chunks": len(rag_index.chunks),
    })


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5555, debug=True)