from typing import Any, Dict, List, Tuple

# tiktoken is optional at runtime; annotate as Any|None so mypy is happy when
# it's not installed in some environments.
tiktoken: Any | None = None
try:
    import tiktoken as _tiktoken

    tiktoken = _tiktoken
except Exception:
    tiktoken = None
from fastapi import FastAPI
from pydantic import BaseModel

from .config import Config
from .documents import load_documents
from .llm_client import LLMClient
from .vector_store import VectorStore

app = FastAPI(title="Content QA")


class QARequest(BaseModel):
    question: str
    top_k: int = 5


def read_documents(content_dir: str):
    return load_documents(content_dir)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    # Token-aware chunking using tiktoken when available; falls back to character-based.
    if tiktoken:
        model_name = getattr(Config, "LLM_MODEL", "gpt-4o-mini")
        enc = (
            tiktoken.encoding_for_model(model_name)
            if hasattr(tiktoken, "encoding_for_model")
            else tiktoken.get_encoding("cl100k_base")
        )
        toks = enc.encode(text)
        chunks = []
        i = 0
        while i < len(toks):
            part = toks[i : i + chunk_size]
            chunks.append(enc.decode(part))
            i += chunk_size - overlap
        return chunks

    # fallback: character-based
    i = 0
    chunks = []
    while i < len(text):
        chunk = text[i : i + chunk_size]
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def chunk_with_metadata(
    text: str, path: str, chunk_size_tokens: int = 700, overlap_tokens: int = 150
):
    """Split text into chunks and attach metadata: source, approximate page and paragraph indices.

    Page detection: look for form-feed characters '\f' or 'Page ' markers; fallback sets page=1.
    Paragraph index is approximate using split('\n\n').
    """
    # naive page split
    if "\f" in text:
        pages = text.split("\f")
    else:
        # attempt to detect explicit 'Page X' markers
        pages = [text]

    chunks = []
    for p_idx, page_text in enumerate(pages, start=1):
        paras = [p for p in page_text.split("\n\n") if p.strip()]
        for para_idx, para in enumerate(paras, start=1):
            sub_chunks = chunk_text(
                para, chunk_size=chunk_size_tokens, overlap=overlap_tokens
            )
            for sc_idx, sc in enumerate(sub_chunks):
                meta = {
                    "source": path,
                    "page": p_idx,
                    "para": para_idx,
                    "chunk_index": sc_idx,
                }
                chunks.append((sc, meta))
    return chunks


_VSTORE = None
_LLM = None
_INDEX_FINGERPRINT: Tuple[Tuple[str, int], ...] | None = None
_INDEX_READY = False


def _fingerprint_documents(docs: List[Dict[str, Any]]) -> Tuple[Tuple[str, int], ...]:
    """Compute a cheap fingerprint of the current content set."""
    pairs = [(d.get("path", ""), len(d.get("text") or "")) for d in docs]
    pairs.sort(key=lambda item: item[0])
    return tuple(pairs)


def _build_index_if_needed(
    docs: List[Dict[str, Any]], vstore: VectorStore, llm: LLMClient, force: bool = False
) -> None:
    """Ensure the in-memory vector index matches the provided docs."""
    global _INDEX_FINGERPRINT, _INDEX_READY

    new_fp = _fingerprint_documents(docs)
    if _INDEX_READY and not force and new_fp == _INDEX_FINGERPRINT:
        return

    if hasattr(vstore, "clear"):
        vstore.clear()

    chunk_texts: List[str] = []
    chunk_meta: List[Dict[str, Any]] = []
    for doc in docs:
        text = doc.get("text", "") or ""
        path = doc.get("path", "unknown")
        for chunk, meta in chunk_with_metadata(
            text,
            path,
            chunk_size_tokens=Config.CHUNK_SIZE_TOKENS,
            overlap_tokens=Config.CHUNK_OVERLAP_TOKENS,
        ):
            chunk_texts.append(chunk)
            meta_with_snippet = {
                "source": meta["source"],
                "snippet": chunk[:300],
                "page": meta.get("page"),
                "para": meta.get("para"),
                "chunk_index": meta.get("chunk_index"),
            }
            chunk_meta.append(meta_with_snippet)

    if chunk_texts:
        embeddings = llm.embed(chunk_texts)
        for idx, emb in enumerate(embeddings):
            vstore.upsert(str(idx), emb, chunk_meta[idx])

    _INDEX_FINGERPRINT = new_fp
    _INDEX_READY = True


def get_services():
    """Lazily create and cache the VectorStore and LLMClient instances.

    This avoids importing optional heavy dependencies at module import time so
    the FastAPI app can be imported in environments where those packages
    aren't installed yet.
    """
    global _VSTORE, _LLM
    if _VSTORE is None:
        _VSTORE = VectorStore()
    if _LLM is None:
        _LLM = LLMClient()
    return _VSTORE, _LLM


@app.post("/qa")
def qa(req: QARequest):
    if not req.question:
        return {"answer": "", "sources": []}

    VSTORE, LLM = get_services()

    docs = read_documents(Config.CONTENT_DIR)
    _build_index_if_needed(docs, VSTORE, LLM)

    q_emb = LLM.embed([req.question])[0]
    results = VSTORE.query(q_emb, top_k=req.top_k)
    hits = results
    context = "\n\n".join([h.get("metadata", {}).get("snippet", "") for h in hits])
    prompt = f"You are a helpful subject-matter expert. Use ONLY the context to answer.\n\nContext:\n{context}\n\nQuestion: {req.question}\nAnswer:"
    resp = LLM.chat(
        [
            {"role": "system", "content": "You are a helpful subject-matter expert."},
            {"role": "user", "content": prompt},
        ]
    )
    try:
        answer = resp.choices[0].message.content.strip()
    except Exception:
        answer = str(resp)
    # Build ordered, deduplicated list of source metadata dicts so the UI can render
    # precise citations (source path, page, paragraph, chunk_index, snippet).
    seen = set()
    sources = []
    for h in hits:
        meta = h.get("metadata", {})
        key = (
            meta.get("source"),
            meta.get("page"),
            meta.get("para"),
            meta.get("chunk_index"),
        )
        if key in seen:
            continue
        seen.add(key)
        # include at minimum the source; keep snippet/page/para if available
        entry = {
            k: v
            for k, v in meta.items()
            if k in ("source", "snippet", "page", "para", "chunk_index")
        }
        sources.append(entry)

    return {"answer": answer, "sources": sources}


def reset_index_cache():
    """Force the in-memory index to rebuild on the next QA call."""
    global _INDEX_FINGERPRINT, _INDEX_READY
    vstore, _ = get_services()
    if hasattr(vstore, "clear"):
        vstore.clear()
    _INDEX_FINGERPRINT = None
    _INDEX_READY = False
