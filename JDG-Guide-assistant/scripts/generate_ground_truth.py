"""Build retrieval ground truth by asking an LLM to generate one question
per chunk. See also scripts/build_faq_ground_truth.py for a free,
deterministic alternative built from the real FAQ page."""
import json

from jdg_assistant.evaluation.ground_truth import build_ground_truth
from jdg_assistant.ingestion.source import CACHE_PATH

OUTPUT_PATH = CACHE_PATH.parent / "ground_truth_llm.json"

if __name__ == "__main__":
    ground_truth = build_ground_truth()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(ground_truth)} ground-truth questions to {OUTPUT_PATH}")
