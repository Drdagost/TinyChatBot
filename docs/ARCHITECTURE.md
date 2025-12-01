# Tiny Chat Bot Architecture

## Overview
- **Goal:** provide a local-first assistant that chats over curated documents using a Gradio UI while sharing retrieval and answering logic with a FastAPI QA service.
- **Stack:** Python 3.11, Gradio UI, FastAPI backend, OpenAI-compatible LLM/embedding APIs, in-memory vector store (pluggable providers planned).
- **Content:** plaintext, Markdown, DOCX, and PDF files under `CONTENT_DIR` are extracted into plain text and cached in memory for prompting + retrieval.

## Key Modules
| Module | Purpose |
| --- | --- |
| `tinychatbot.app` | Gradio UI + `ContentAgent` orchestration (system prompt, chat history, tool calls). |
| `tinychatbot.qa_service` | FastAPI `/qa` endpoint plus pure-Python QA engine shared with the UI. Handles chunking, embeddings, vector search, answer synthesis, and citation formatting. |
| `tinychatbot.documents` | Single entry point for loading content folders via `DocumentExtractor`. Guarantees consistent behavior between the UI and QA service. |
| `tinychatbot.io_utils` | Robust document extraction (DOCX, PDF with optional OCR, txt/md). Provides helpers for registering new handlers. |
| `tinychatbot.vector_store` | Minimal in-memory cosine-sim vector store with `upsert`, `query`, and `clear`. Future providers (FAISS/Pinecone/Chroma) will plug in here. |
| `tinychatbot.llm_client` | Thin wrapper around OpenAI-like APIs for both chat completions and embeddings. Reads provider/model settings from `Config`. |
| `tinychatbot.config` | Centralizes env-backed settings (providers, models, chunk sizes, directories). |
| `scripts/smoke_load.py` | Manual utility for verifying that `load_documents()` finds and parses files as expected. |

## Data Flow
1. **Document ingestion**
   - `documents.load_documents()` walks `CONTENT_DIR`, uses `DocumentExtractor` to read supported files, filters out empty text, and returns `[{"path", "text"}]` pairs.
2. **Gradio chat path** (`tinychatbot.app`)
   - `ContentAgent` loads docs at startup and builds a long-form system prompt with document previews.
   - User messages are sent to OpenAI via `LLMClient` (direct SDK usage) with tooling to record unknown questions.
   - After generating a natural-language answer, the UI calls `qa_service.qa()` in-process to fetch structured citations and appends them to the response.
3. **QA service path** (`tinychatbot.qa_service`)
   - `qa()` loads docs (via the shared helper), ensures the vector index is built, embeds the user question, retrieves top-k chunks, composes an answering prompt, and returns both `answer` and `sources` metadata (path, page, paragraph, snippet).

## Vector Index Lifecycle
- `_build_index_if_needed()` fingerprints the document set using `(path, text_length)` tuples.
- On the first question (or whenever content changes), the service:
  1. Clears the vector store.
  2. Runs `chunk_with_metadata()` using `Config.CHUNK_SIZE_TOKENS` / `CHUNK_OVERLAP_TOKENS`.
  3. Embeds all chunks once and upserts them into the store with metadata (source, snippet, page, paragraph, chunk index).
- Subsequent questions reuse the cached vectors, avoiding repeated chunking/embedding.
- `reset_index_cache()` clears the store and fingerprint, forcing a rebuild on the next request—handy for tests or manual reloads.

## Runtime Modes
1. **All-in-one (default during dev):** Run `python -m tinychatbot.app`. Gradio hosts the chat UI and executes QA in-process.
2. **Service split (future-ready):** `tinychatbot.qa_service` already exposes a FastAPI app (`uvicorn tinychatbot.qa_service:app`). The Gradio app can be updated to call `/qa` over HTTP when you deploy the service separately.

## Configuration & Environment
- `.env.example` documents all environment variables (content paths, providers, chunk parameters, API keys).
- `Config` reads `VECTOR_PROVIDER` (with `VECTOR_DB` fallback), `LLM_PROVIDER`, model names, chunk sizes, and content directories at import time via `python-dotenv`.
- Adjust `CHUNK_SIZE` / `CHUNK_OVERLAP` to trade recall for speed without touching code.

## Testing & Diagnostics
- `pytest` suite covers chunk metadata, DOCX extraction edge cases, IO utilities, and QA logic with faked vector/LLM services.
- `scripts/smoke_load.py` prints a quick summary of extracted docs to validate new content before launching the UI.
- Logging (via `loguru`) surfaces document extraction failures and index warnings.

## Future Considerations
- **Vector providers:** swap the in-memory store for FAISS/Pinecone/Chroma by extending `VectorStore` and wiring provider-specific classes.
- **Content change detection:** integrate file watching or timestamps to trigger `reset_index_cache()` automatically.
- **Deployment profile:** document whether Gradio should remain coupled to the QA engine or talk to it over HTTP (ties into CI/CD and scaling decisions).
- **Telemetry:** optionally record unanswered questions via the existing tool interface (e.g., send to a queue or analytics service).
