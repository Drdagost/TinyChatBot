from tinychatbot import qa_service as qs


def test_chunk_with_metadata_basic():
    # create a simple multi-page text using form-feed and paragraph breaks
    text = "PageOne-Intro\n\nPageOne-Body\fPageTwo-Intro\n\nPageTwo-Body"
    path = "/tmp/multipage.txt"

    chunks = qs.chunk_with_metadata(text, path, chunk_size_tokens=50, overlap_tokens=10)

    # Expect at least one chunk for page1 and page2
    pages = {m["page"] for _, m in chunks}
    paras = {m["para"] for _, m in chunks}

    assert 1 in pages
    assert 2 in pages
    assert 1 in paras


def test_qa_includes_metadata(monkeypatch):
    # Mock read_documents to return one multi-page document
    text = "PageOne-Intro\n\nPageOne-Body\fPageTwo-Intro\n\nPageTwo-Body"
    docs = [{"path": "/tmp/doc.txt", "text": text}]
    monkeypatch.setattr(qs, "read_documents", lambda content_dir: docs)

    # Fake VectorStore that will store metadata and return it on query
    class FakeVStore:
        def __init__(self):
            self._vectors = []

        def upsert(self, id, embedding, metadata):
            self._vectors.append(
                {"id": id, "embedding": embedding, "metadata": metadata}
            )

        def clear(self):
            self._vectors = []

        def query(self, embedding, top_k=5):
            # return stored vectors as hits (sorted naive)
            return self._vectors[:top_k]

    fake_v = FakeVStore()

    # Fake LLM client
    class FakeLLM:
        def embed(self, texts, **kwargs):
            return [[0.0] * 3 for _ in texts]

        def chat(self, messages, **kwargs):
            from types import SimpleNamespace

            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content="Mocked answer"))
                ]
            )

    fake_l = FakeLLM()

    monkeypatch.setattr(qs, "get_services", lambda: (fake_v, fake_l))

    req = qs.QARequest(question="What is on page two?", top_k=2)
    resp = qs.qa(req)

    assert isinstance(resp, dict)
    assert resp["answer"] == "Mocked answer"
    # sources should be a list of metadata dicts
    assert isinstance(resp["sources"], list)
    assert len(resp["sources"]) > 0
    first = resp["sources"][0]
    assert "source" in first
    assert "page" in first or "snippet" in first
