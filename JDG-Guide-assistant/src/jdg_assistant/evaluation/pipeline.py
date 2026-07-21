"""End-to-end helpers that build ground truth and run the retrieval
evaluation. Shared between the CLI scripts (scripts/build_faq_ground_truth.py,
scripts/eval_retrieval.py) and the dashboard's "Run evaluation" button, so
there's one implementation instead of two drifting copies.
"""
import json

from jdg_assistant.ingestion.source import load_jdg_docs, CACHE_PATH
from jdg_assistant.ingestion.indexing import build_keyword_index, build_vector_index
from jdg_assistant.rag.reranker import CrossEncoderReranker
from jdg_assistant.rag.hybrid import HybridRAG
from jdg_assistant.evaluation.ground_truth import build_faq_ground_truth, build_cross_lingual_ground_truth
from jdg_assistant.evaluation.retrieval_metrics import evaluate_retrieval_by_lang

DATA_DIR = CACHE_PATH.parent
GROUND_TRUTH_FAQ_PATH = DATA_DIR / "ground_truth_faq.json"
RETRIEVAL_RESULTS_PATH = DATA_DIR / "retrieval_eval_results.json"


def build_and_save_faq_ground_truth():
    """Extract ground truth from the real FAQ page and write it to
    data/ground_truth_faq.json. No LLM calls, no OpenAI key needed."""
    ground_truth = build_faq_ground_truth()

    GROUND_TRUTH_FAQ_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GROUND_TRUTH_FAQ_PATH, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2)

    return ground_truth


def build_and_save_crosslingual_ground_truth():
    """Extend data/ground_truth_faq.json with Polish/Ukrainian/Belarusian
    translations of the real (Russian) FAQ questions -- same doc_id targets,
    just a different query language, to measure cross-lingual retrieval.
    Needs OPENAI_API_KEY (each translation is one LLM call).
    """
    base_ground_truth = build_faq_ground_truth()
    ru_items = [item for item in base_ground_truth if item["lang"] == "ru"]

    translated = build_cross_lingual_ground_truth(ru_items)
    full_ground_truth = base_ground_truth + translated

    GROUND_TRUTH_FAQ_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GROUND_TRUTH_FAQ_PATH, "w", encoding="utf-8") as f:
        json.dump(full_ground_truth, f, ensure_ascii=False, indent=2)

    return full_ground_truth


def _load_faq_ground_truth():
    if GROUND_TRUTH_FAQ_PATH.exists():
        with open(GROUND_TRUTH_FAQ_PATH, encoding="utf-8") as f:
            return json.load(f)
    return build_and_save_faq_ground_truth()


def _make_search_fn(rag, strategy):
    def search_fn(question, lang):
        return rag.search(question, num_results=5, lang=lang, strategy=strategy)
    return search_fn


def run_and_save_retrieval_evaluation(ground_truth=None):
    """Build fresh keyword + vector indexes and evaluate keyword / vector /
    hybrid / hybrid+rerank retrieval against `ground_truth` (defaults to
    data/ground_truth_faq.json, building it first if missing), writing
    per-language results to data/retrieval_eval_results.json.

    This is the slow part: it downloads/builds the MiniLM embedder and the
    cross-encoder reranker and runs every ground-truth question through all
    four strategies -- expect it to take a couple of minutes on CPU.
    """
    if ground_truth is None:
        ground_truth = _load_faq_ground_truth()

    docs = load_jdg_docs()
    keyword_index = build_keyword_index(docs)
    vector_index, embedder = build_vector_index(docs)

    strategies = {
        "keyword": HybridRAG(keyword_index, vector_index, embedder, llm_client=None),
        "vector": HybridRAG(keyword_index, vector_index, embedder, llm_client=None),
        "hybrid": HybridRAG(keyword_index, vector_index, embedder, llm_client=None),
        "hybrid+rerank": HybridRAG(
            keyword_index, vector_index, embedder, llm_client=None,
            reranker=CrossEncoderReranker(),
        ),
    }

    results = {}
    for name, rag in strategies.items():
        strategy_arg = "hybrid" if name == "hybrid+rerank" else name
        results[name] = evaluate_retrieval_by_lang(ground_truth, _make_search_fn(rag, strategy_arg))

    RETRIEVAL_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RETRIEVAL_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results
