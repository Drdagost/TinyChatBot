import os

from tinychatbot.qa_service import read_documents

content_dir = os.path.join(os.getcwd(), "content")
try:
    docs = read_documents(content_dir)
    print(f"Loaded {len(docs)} documents")
    for d in docs:
        print(
            "-",
            os.path.basename(d["path"]),
            "len=",
            len(d["text"]),
            "preview=",
            repr(d["text"][:200]),
        )
except Exception as e:
    print("Error during read_documents:", e)
