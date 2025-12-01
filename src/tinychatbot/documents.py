"""Shared helpers for loading project documents from the content directory."""
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .config import Config
from .io_utils import DocumentExtractor


def load_documents(content_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load supported documents under ``content_dir`` and return a path/text list.

    This centralizes the folder walking logic so both the UI and QA service stay in sync.
    It also filters out empty-text entries because downstream components only work with
    readable documents.
    """
    base = Path(content_dir or Config.CONTENT_DIR)
    if not base.exists():
        raise FileNotFoundError(f"Content directory '{base}' not found.")

    extractor = DocumentExtractor()
    docs = extractor.load_folder(str(base))

    filtered: List[Dict[str, Any]] = []
    skipped = 0
    for doc in docs:
        text = doc.get("text", "") or ""
        if text.strip():
            filtered.append({"path": doc.get("path"), "text": text})
        else:
            skipped += 1

    if skipped:
        logger.warning(f"Skipped {skipped} documents that produced no readable text in '{base}'.")
    if not filtered:
        logger.warning(f"No readable documents found under '{base}'.")

    return filtered
