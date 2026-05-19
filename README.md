# NyayaSetu

NyayaSetu is a legal assistant focused on Indian Constitutional Law. It uses a local
hybrid RAG engine (BM25 + TF-IDF + title boosting) and can generate responses via
Ollama (local) or Gemini.

## Features
- Hybrid retrieval with explainability scores
- Local LLM via Ollama (phi3/llama3) or Gemini fallback
- Rights and next-steps templates for common scenarios
- Modular AI legal reasoning tools:
  - Fairness checker
  - Rights card generator
  - Scenario simulator
  - Layman/legal translator
  - Constitutional amendment tracker
  - Article comparison tool
- NyayaSetu Bot floating widget:
  - Legal Assistant mode routes legal questions through `/api/chat`
  - Site Guide mode answers from the static NyayaSetu feature knowledge base
  - Confidence badges, source citations, quick actions, and page-aware prompts
- Document intelligence:
  - Upload PDF/DOCX/image and merge extracted text into corpus
  - Contract risk analyzer (regex + constitutional RAG grounding)
  - Court notice decoder (deadline extraction + section grounding)

## Tech stack
- Backend: Flask (Python)
- Frontend: React
- LLM: Ollama (local) or Gemini (optional)

## Quickstart (local)
Backend (Terminal 1):
```
cd backend
pip install -r requirements.txt
python app.py
```

OCR note: install the Tesseract binary on your system (for example `brew install tesseract` on macOS) so scanned PDF/image extraction works. Handwriting is supported as best-effort via image preprocessing + OCR fallback.

Frontend (Terminal 2):
```
cd frontend
npm install
npm start
```

Backend runs on http://127.0.0.1:5555 and frontend on http://localhost:3000.
Open `/ai-legal-tools` in the frontend for the new modular reasoning UI.

## LLM configuration
Copy `config.example.yaml` to `config.yaml` in the repo root, then edit it if needed:
```
llm_provider: "ollama"
ollama_model: "phi3"
ollama_host: "http://localhost:11434"
ollama_timeout: 180
ollama_num_predict: 900
gemini_model: "gemini-1.5-flash"
```

Optional Gemini setup: set GEMINI_API_KEY in a .env file at the repo root.

## What not to commit
- Do not commit `config.yaml`; keep local machine settings there.
- Do not commit `.venv/`, `venv/`, `__pycache__/`, or frontend build output.
- Do not commit local scratch files like `context.txt` or `commands.txt`.
- Ollama models themselves are not stored in this repo, so `git add .` will not add the actual model weights unless you manually copy them into the project folder.

## API
POST /legal-help
```
curl -X POST http://127.0.0.1:5555/legal-help \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Police arrested me without telling the reason\"}"
```

### Standard advanced-tool response
All `/api/*` reasoning endpoints return:
```
{
  "status": "success | insufficient_data | error",
  "feature": "feature_name",
  "data": {},
  "explainability": {
    "retrieved_chunks": [],
    "retrieval_scores": [],
    "domain_filter_applied": "domain",
    "confidence": 0.0,
    "sources": [],
    "reasoning_steps": [],
    "unverified_claims": []
  },
  "warnings": [],
  "confidence": 0.0
}
```

POST /api/fairness-check
```
curl -X POST http://127.0.0.1:5555/api/fairness-check \
  -H "Content-Type: application/json" \
  -d "{\"situation\":\"My employer didn't pay me overtime for 3 months\"}"
```

POST /api/rights-card
```
curl -X POST http://127.0.0.1:5555/api/rights-card \
  -H "Content-Type: application/json" \
  -d "{\"rights_type\":\"arrest_rights\"}"
```

POST /api/simulate-scenario
```
curl -X POST http://127.0.0.1:5555/api/simulate-scenario \
  -H "Content-Type: application/json" \
  -d "{\"scenario\":\"I was fired without notice after 4 years at my company\"}"
```

POST /api/translate
```
curl -X POST http://127.0.0.1:5555/api/translate \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"They locked me up without telling me why\",\"direction\":\"to_legal\"}"
```

GET /api/amendments and GET /api/amendments/{article_number}
```
curl http://127.0.0.1:5555/api/amendments/21
```

POST /api/compare-articles
```
curl -X POST http://127.0.0.1:5555/api/compare-articles \
  -H "Content-Type: application/json" \
  -d "{\"article_a\":\"14\",\"article_b\":\"21\"}"
```

POST /api/chat
```
curl -X POST http://127.0.0.1:5555/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"Can my landlord evict me without notice?\",\"conversation_history\":[]}"
```

Stub endpoints, intentionally returning HTTP 501 until their retrieve -> generate flow is implemented:
`/api/document-analyzer`, `/api/petition-draft`, `/api/landmark-cases?topic=`, `/api/bail-eligibility`, `/api/legal-timeline`.

POST /document-intel/upload (multipart file upload)
```
curl -X POST http://127.0.0.1:5555/document-intel/upload \
  -F "file=@/absolute/path/to/contract.pdf"
```

POST /document-intel/contract-analyze
```
curl -X POST http://127.0.0.1:5555/document-intel/contract-analyze \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"...contract text...\"}"
```

POST /document-intel/court-notice-decode
```
curl -X POST http://127.0.0.1:5555/document-intel/court-notice-decode \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"...notice text...\"}"
```

## Notes
- Constitution text is loaded from backend/constitution.txt; if missing, the app
  tries to extract from backend/static/constitution.pdf.
- New advanced features live under `backend/features`, route blueprints under
  `backend/routes`, shared wrappers under `backend/utils`, and structured data
  under `backend/data`.
- The vanilla bot widget assets live under `frontend/public/static/bot` and are
  mirrored under `backend/static/bot` for Flask/static deployments.
