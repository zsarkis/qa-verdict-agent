"""Knowledge-base retrieval.

The KB is four small markdown docs (runbook, testing conventions, definition of
done, glossary) — shared team knowledge where semantic retrieval earns its keep.
Ticket-specific facts (acceptance criteria) deliberately do NOT live here: those
ride on the card and are fetched by key, not similarity.

The index is rebuilt in-memory at startup: the corpus is tiny, and it keeps the
demo free of a vector-store service. Swapping in Chroma/pgvector means changing
only this module.
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from qa_agent.settings import EMBEDDINGS_MODEL, KB_DIR


def build_retriever(kb_dir: Path = KB_DIR, k: int = 4):
    docs = [
        Document(page_content=path.read_text(), metadata={"source": path.name})
        for path in sorted(kb_dir.glob("*.md"))
    ]
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = splitter.split_documents(docs)
    store = InMemoryVectorStore(OpenAIEmbeddings(model=EMBEDDINGS_MODEL))
    store.add_documents(chunks)
    return store.as_retriever(search_kwargs={"k": k})
