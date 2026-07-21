"""Composition root: wires ingestion + indexing + rag + metrics together."""
from dotenv import load_dotenv
from openai import OpenAI

from jdg_assistant.ingestion.source import load_jdg_docs
from jdg_assistant.ingestion.indexing import build_keyword_index, build_vector_index
from jdg_assistant.rag.reranker import CrossEncoderReranker
from jdg_assistant.metrics.tracking import RAGWithMetrics


def create_assistant(use_reranker=True):
    load_dotenv()

    docs = load_jdg_docs()
    keyword_index = build_keyword_index(docs)
    vector_index, embedder = build_vector_index(docs)
    reranker = CrossEncoderReranker() if use_reranker else None

    return RAGWithMetrics(
        keyword_index=keyword_index,
        vector_index=vector_index,
        embedder=embedder,
        llm_client=OpenAI(),
        reranker=reranker,
    )
