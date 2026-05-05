# LegalAI

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Build Status](https://img.shields.io/badge/build-pending-yellow)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()

LegalAI is a toolkit and platform for legal-document intelligence. It helps teams extract clauses, summarize contracts, answer legal questions, classify documents, and cite legal sources using modern NLP and LLM technologies. LegalAI aims to provide a secure, auditable, and extensible foundation for building legal automation and research tools.

Table of Contents
- About
- Key Features
- Tech Stack
- Architecture Overview
- Quickstart
  - Prerequisites
  - Local development
  - Docker
- Configuration / Environment Variables
- Usage Examples
  - CLI
  - REST API (curl)
  - Python client
- Data & Models
- Security & Privacy
- Tests
- Contributing
- Roadmap
- License
- Contact

About
-----
LegalAI combines large language models, embeddings, and legal-specific pipelines to power features such as:
- Contract clause extraction and normalization
- Contract and memorandum summarization
- Natural language Q&A with citation of supporting text
- Document classification (e.g., NDA, Master Agreement, SOW)
- Search over precedent and statutes via vector search
- Audit logs and explainability for results

Key Features
------------
- Reusable pipelines for ingestion -> preprocessing -> embedding -> retrieval -> response
- Vector database integrations (local FAISS and cloud options)
- Pluggable LLM and embedding providers (OpenAI, local models, etc.)
- Secure handling of sensitive documents (configurable retention and redaction)
- API endpoints and simple Python client for easy integration
- Test suite and CI-ready workflows

Tech Stack
----------
- Language: Python 3.10+
- Web/API: FastAPI (or Flask — adjust as implemented)
- Model/Embeddings: configurable (OpenAI, open-source models)
- Vector DB: FAISS (local) plus connectors for Pinecone, Weaviate, Supabase
- Storage: local filesystem for dev; S3-compatible for production
- Testing: pytest
- Containerization: Docker

Architecture Overview
---------------------
1. Ingest: Upload documents (PDF, DOCX, TXT) → OCR (if needed) → text extraction.
2. Preprocess: Chunking, normalization, metadata extraction.
3. Indexing: Compute embeddings and store them in a vector database with metadata.
4. Retrieval: Retrieve relevant chunks with similarity search and reranking.
5. Generation: Use LLMs to answer, summarize, and explain; include citations to source chunks.
6. Audit & Safety: Log requests, redact PII, and optionally store provenance.

Quickstart
----------
Prerequisites
- Python 3.10+
- pip or Poetry
- Git
- (Optional) Docker

Local development
1. Clone the repo
   git clone https://github.com/GaurangMundhra/LegalAI.git
   cd LegalAI

2. Create a virtual environment and install dependencies
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

3. Copy the example env file and set required secrets
   cp .env.example .env
   # Edit .env with your keys (see Configuration section)

4. Start the application
   uvicorn app.main:app --reload --port 8000

Open http://localhost:8000 in your browser. If API docs are enabled, visit http://localhost:8000/docs

Docker
1. Build the image:
   docker build -t legalai:latest .

2. Run the container (example):
   docker run --env-file .env -p 8000:8000 legalai:latest

Configuration / Environment Variables
-------------------------------------
Place secrets in .env (never commit secrets). Typical variables:
- OPENAI_API_KEY=your_openai_api_key
- VECTOR_DB=faiss|pinecone|weaviate
- PINECONE_API_KEY=...
- PINECONE_ENVIRONMENT=...
- STORAGE_BACKEND=local|s3
- S3_BUCKET=...
- S3_ENDPOINT=...
- RETENTION_DAYS=30
- LOG_LEVEL=info

Usage Examples
--------------

CLI
- Ingest a file:
  python -m legalai.cli ingest --file ./contracts/example.pdf --namespace "acme/nda"

- Search:
  python -m legalai.cli query --q "What is the termination clause?" --namespace "acme/nda"

REST API (curl)
- Basic Q&A
  curl -X POST "http://localhost:8000/api/v1/query" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query":"Summarize the main obligations of the supplier.","namespace":"acme/nda"}'

Python client (example)
```python
from legalai.client import LegalAIClient
client = LegalAIClient(api_url="http://localhost:8000", api_key="YOUR_KEY")
resp = client.query("What are the termination rights for the vendor?", namespace="acme/nda", max_tokens=512)
print(resp)
```

Data & Models
-------------
- Support for uploading and processing PDFs, DOCX, TXT.
- Chunking strategy: configurable chunk size + overlap.
- Embeddings: use provider choice; store vectors with metadata: source_file, page, chunk_id, extracted_text.
- Model selection: LLM and embedding provider config lives in the settings file or .env.

Security & Privacy
------------------
- Do not store secrets in the repository.
- Configure retention policies for documents and vectors.
- Redaction: PII redaction is supported in preprocessing pipelines — enable as needed.
- Audit logs record queries and responses for compliance; redact stored outputs if required.
- If using third-party providers (e.g., OpenAI), check their data usage policies; consider opt-out or self-hosted models for sensitive data.

Tests
-----
- Run unit tests:
  pytest tests/

- Linting:
  flake8 .
  black --check .

- CI: Add workflows to run tests, linting, and security scans on push/PR.

Contributing
------------
We welcome contributions! Suggested workflow:
1. Fork the repository.
2. Create a feature branch: git checkout -b feat/some-feature
3. Write tests for new functionality.
4. Open a PR with a clear description and linked issue.
5. Ensure CI passes; respond to review feedback.

Please follow code style guidelines (Black, flake8) and include tests for new logic.

Roadmap
-------
Planned improvements:
- Additional model and vector DB integrations (Weaviate, Supabase)
- RBAC and user management for multi-tenant use
- End-to-end encrypted storage option
- UI for document management and annotation
- Benchmark suite for legal tasks (summarization, extraction, Q&A)

License
-------
This repository is provided under the MIT License. See LICENSE for details. (Change if another license is required for your organization.)

Contact
-------
Maintainer: Gaurang Mundhra (GitHub: @GaurangMundhra)
For questions or enterprise integrations, open an issue or email: [replace-with-contact-email]

Acknowledgements
----------------
- Built with the open-source community and common NLP libraries.
- Inspired by legal automation workflows; adapt responsibly.

Notes
-----
- This README is intentionally general: update the "Tech Stack", "Usage", and "Configuration" sections to reflect exact choices and providers used in your codebase.
- If you want, I can:
  - tailor the README to the repository's actual files (requirements.txt, app structure) by scanning the repo, or
  - generate a shorter README focused only on Quickstart and API references.
