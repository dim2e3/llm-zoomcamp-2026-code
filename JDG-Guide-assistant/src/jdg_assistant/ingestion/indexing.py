"""Build the keyword and embedding indexes used for retrieval."""
from sentence_transformers import SentenceTransformer
from minsearch import Index, VectorSearch

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def build_keyword_index(documents):
    index = Index(
        text_fields=["title", "section", "content"],
        keyword_fields=["lang", "page"],
    )
    index.fit(documents)
    return index


def build_vector_index(documents, embedder=None):
    embedder = embedder or SentenceTransformer(EMBEDDING_MODEL)

    texts = [f"{doc['section']}\n{doc['content']}" for doc in documents]
    vectors = embedder.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    index = VectorSearch(keyword_fields=["lang", "page"])
    index.fit(vectors, documents)
    return index, embedder
