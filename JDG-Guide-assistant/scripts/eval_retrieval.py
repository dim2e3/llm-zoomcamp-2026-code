"""Compare keyword-only, vector-only, and hybrid(+rerank) retrieval on the
ground-truth set with hit-rate/MRR/precision@1, broken out by RU/EN --
the standout-feature evaluation called for in the capstone plan.

Uses data/ground_truth_faq.json by default (built from the real FAQ page --
see scripts/build_faq_ground_truth.py, run automatically here if missing);
pass a different --ground-truth path to evaluate against the LLM-generated
set (data/ground_truth_llm.json) instead.
"""
import argparse
import json
from pathlib import Path

from jdg_assistant.evaluation.pipeline import run_and_save_retrieval_evaluation, RETRIEVAL_RESULTS_PATH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", type=str, default=None)
    args = parser.parse_args()

    ground_truth = None
    if args.ground_truth:
        with open(Path(args.ground_truth), encoding="utf-8") as f:
            ground_truth = json.load(f)

    results = run_and_save_retrieval_evaluation(ground_truth)

    for name, by_lang in results.items():
        for lang, metrics in by_lang.items():
            print(
                f"{name:15s} [{lang:3s}] hit_rate={metrics['hit_rate']:.3f}  "
                f"mrr={metrics['mrr']:.3f}  precision@1={metrics['precision_at_1']:.3f}  "
                f"(n={metrics['n']})"
            )

    print(f"\nWrote results to {RETRIEVAL_RESULTS_PATH}")


if __name__ == "__main__":
    main()
