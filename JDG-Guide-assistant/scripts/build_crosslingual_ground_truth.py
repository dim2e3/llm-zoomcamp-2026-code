"""Extend the real-FAQ ground truth with Polish/Ukrainian/Belarusian
translations of the Russian questions (same target chunk, different query
language) -- measures cross-lingual retrieval, since the corpus itself has
no PL/UK/BE content. Needs OPENAI_API_KEY (one LLM call per translation)."""
from collections import Counter

from jdg_assistant.evaluation.pipeline import (
    build_and_save_crosslingual_ground_truth, GROUND_TRUTH_FAQ_PATH,
)

if __name__ == "__main__":
    ground_truth = build_and_save_crosslingual_ground_truth()

    by_lang = Counter(item["lang"] for item in ground_truth)
    print(f"Wrote {len(ground_truth)} ground-truth questions to {GROUND_TRUTH_FAQ_PATH}")
    print(f"By language: {dict(by_lang)}")
