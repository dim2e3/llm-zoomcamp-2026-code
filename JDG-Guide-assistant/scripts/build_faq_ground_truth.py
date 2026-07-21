"""Build retrieval ground truth directly from the real FAQ page content
(docs/faq.md, docs/faq.en.md) -- real user questions, no LLM calls needed."""
from collections import Counter

from jdg_assistant.evaluation.pipeline import build_and_save_faq_ground_truth, GROUND_TRUTH_FAQ_PATH

if __name__ == "__main__":
    ground_truth = build_and_save_faq_ground_truth()

    by_lang = Counter(item["lang"] for item in ground_truth)
    print(f"Wrote {len(ground_truth)} FAQ ground-truth questions to {GROUND_TRUTH_FAQ_PATH}")
    print(f"By language: {dict(by_lang)}")
