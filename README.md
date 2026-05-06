# NyayaSetu

NyayaSetu is a legal assistant focused on Indian Constitutional Law. It uses a local
hybrid RAG engine (BM25 + TF-IDF + title boosting) and can generate responses via
Ollama (local) or Gemini.

## Features
- Hybrid retrieval with explainability scores
- Local LLM via Ollama (phi3/llama3) or Gemini fallback
- Rights and next-steps templates for common scenarios

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

Frontend (Terminal 2):
```
cd frontend
npm install
npm start
```

Backend runs on http://127.0.0.1:5555 and frontend on http://localhost:3000.

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

## Notes
- Constitution text is loaded from backend/constitution.txt; if missing, the app
  tries to extract from backend/static/constitution.pdf.
