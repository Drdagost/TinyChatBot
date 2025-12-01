import types
from types import SimpleNamespace

import pytest

from tinychatbot import qa_service as qs


def test_qa_logic_with_mocks(monkeypatch):
    # Mock read_documents to return one document
    docs = [{'path': '/tmp/doc.txt', 'text': 'This is a document used for testing.'}]
    monkeypatch.setattr(qs, 'read_documents', lambda content_dir: docs)

    # Fake VectorStore with upsert and query
    class FakeVStore:
        def __init__(self):
            self.upserts = []

        def upsert(self, id, embedding, metadata):
            self.upserts.append((id, embedding, metadata))

        def query(self, embedding, top_k=5):
            # return metadata-like structure expected by qa_service
            return [{'metadata': {'snippet': docs[0]['text'][:300], 'source': docs[0]['path']}}]

    fake_v = FakeVStore()

    # Fake LLM client
    class FakeLLM:
        def embed(self, texts, **kwargs):
            # return dummy vector for each text
            return [[0.1, 0.2, 0.3] for _ in texts]

        def chat(self, messages, **kwargs):
            # mimic OpenAI-like response object with nested attributes
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Mocked answer'))])

    fake_l = FakeLLM()

    # Patch get_services to return our fakes
    monkeypatch.setattr(qs, 'get_services', lambda: (fake_v, fake_l))

    # Build request and call the endpoint function directly
    req = qs.QARequest(question='What is in the document?', top_k=1)
    resp = qs.qa(req)

    assert isinstance(resp, dict)
    assert resp['answer'] == 'Mocked answer'
    # sources now contain metadata dicts; assert the path appears in one of them
    assert any(s.get('source') == '/tmp/doc.txt' for s in resp['sources'])
