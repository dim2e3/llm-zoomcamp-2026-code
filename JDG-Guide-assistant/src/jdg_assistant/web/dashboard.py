import json
from dataclasses import asdict

import pandas as pd
import streamlit as st

from jdg_assistant.evaluation.pipeline import (
    build_and_save_faq_ground_truth, build_and_save_crosslingual_ground_truth,
    run_and_save_retrieval_evaluation, RETRIEVAL_RESULTS_PATH,
)
from jdg_assistant.ingestion.source import load_jdg_docs, get_cache_info
from jdg_assistant.persistence.conversations import (
    get_conversations, get_stats, get_cost_by_strategy, get_cost_by_lang,
)
from jdg_assistant.persistence.feedback import get_relevance_stats, get_user_feedback_stats
from jdg_assistant.web.styling import inject_theme, render_letterhead

LANG_LABELS = {"ru": "🇷🇺 RU", "en": "🇬🇧 EN", "pl": "🇵🇱 PL", "uk": "🇺🇦 UK", "be": "🇧🇾 BE"}

st.set_page_config(page_title="JDG Guide Assistant — Dashboard", page_icon="🖋️", layout="wide")
inject_theme()


def _reingest():
    with st.spinner(
        "Reingesting the guide content from GitHub (fetches ~76 pages, "
        "resolves links, chunks by heading)..."
    ):
        load_jdg_docs(force_refresh=True)
    st.rerun()


def _run_evaluation():
    with st.spinner(
        "Building FAQ ground truth and running retrieval evaluation "
        "(embeds ~948 chunks and runs the reranker -- this can take a "
        "couple of minutes)..."
    ):
        build_and_save_faq_ground_truth()
        run_and_save_retrieval_evaluation()
    st.rerun()


def _run_crosslingual_evaluation():
    with st.spinner(
        "Translating the FAQ ground truth to Polish/Ukrainian/Belarusian "
        "(needs OPENAI_API_KEY) and re-running retrieval evaluation -- this "
        "can take a few minutes..."
    ):
        build_and_save_crosslingual_ground_truth()
        run_and_save_retrieval_evaluation()
    st.rerun()

render_letterhead(
    "JDG Guide Assistant",
    "Case ledger: cost, latency, feedback, and retrieval quality across languages.",
    eyebrow="JDG · monitoring & evaluation",
)

monitoring_tab, evaluation_tab = st.tabs(["📊 Monitoring", "🎯 Evaluation"])

with monitoring_tab:
    st.header("Monitoring")

    stats = get_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total conversations", stats.total or 0)
    col2.metric("Avg response time", f"{(stats.avg_response_time or 0):.2f}s")
    col3.metric("Total cost", f"${(stats.total_cost or 0):.4f}")
    col4.metric("Avg prompt tokens", f"{(stats.avg_prompt_tokens or 0):.0f}")

    records = get_conversations(limit=200)
    df = pd.DataFrame([asdict(r) for r in records])

    st.subheader("Cost over time")
    if not df.empty:
        st.line_chart(df, x="timestamp", y="cost")

    st.subheader("Cost & tokens by retrieval strategy")
    strategy_stats = get_cost_by_strategy()
    if strategy_stats:
        strategy_df = pd.DataFrame(strategy_stats).set_index("strategy")
        c1, c2 = st.columns(2)
        c1.bar_chart(strategy_df["total_cost"])
        c2.bar_chart(strategy_df["avg_prompt_tokens"])
        st.dataframe(strategy_df)
    else:
        st.write("No data yet.")

    st.subheader("Cost by language")
    lang_stats = get_cost_by_lang()
    if lang_stats:
        lang_df = pd.DataFrame(lang_stats).set_index("lang")
        st.bar_chart(lang_df["total_cost"])
        st.dataframe(lang_df)

    st.subheader("Response time over time")
    if not df.empty:
        st.line_chart(df, x="timestamp", y="response_time")

    st.subheader("Recent conversations")
    for record in records[:20]:
        st.write(f"**[{record.lang}/{record.strategy}] {record.question[:80]}**")
        st.write(f"{record.answer[:200]}...")
        st.write(f"Time: {record.response_time:.2f}s | Cost: ${record.cost:.4f}")
        st.divider()

    st.subheader("Judge relevance")
    relevance = get_relevance_stats()
    if relevance:
        st.bar_chart(relevance)

    st.subheader("User feedback")
    thumbs_up, thumbs_down = get_user_feedback_stats()
    col1, col2 = st.columns(2)
    col1.metric("Thumbs up", int(thumbs_up or 0))
    col2.metric("Thumbs down", int(thumbs_down or 0))

with evaluation_tab:
    st.header("Evaluation")
    st.caption(
        "Retrieval quality (hit-rate, MRR, precision@1) per strategy, computed "
        "against real questions from the FAQ page (docs/faq.md / docs/faq.en.md)."
    )

    st.subheader("Guide content")
    cache_info = get_cache_info()
    if cache_info:
        st.caption(
            f"Cached from `{cache_info['repo']}@{cache_info['branch']}`, "
            f"commit `{(cache_info['commit'] or '')[:8]}`, "
            f"fetched {cache_info['fetched_at']}."
        )
    else:
        st.caption("No cached guide content yet.")
    if st.button("📥 Reingest guide content"):
        _reingest()
    st.caption(
        "Rebuilds `data/jdg_docs.json` from the source repo. The chat app "
        "caches its indexes for the life of its process, so restart it "
        "after reingesting to actually see fresh content."
    )
    st.divider()

    if not RETRIEVAL_RESULTS_PATH.exists():
        st.info(
            "No evaluation results yet. Click the button below, or run "
            "from the `JDG-Guide-assistant` directory:\n\n"
            "```\nmake ground-truth-faq\nmake eval-retrieval\n```"
        )
        if st.button("▶️ Run evaluation now"):
            _run_evaluation()
    else:
        b1, b2 = st.columns(2)
        if b1.button("🔁 Re-run evaluation"):
            _run_evaluation()
        if b2.button("🌍 Add Polish/Ukrainian/Belarusian & re-run"):
            _run_crosslingual_evaluation()
        st.caption(
            "The cross-lingual option translates the real FAQ questions into "
            "PL/UK/BE (needs `OPENAI_API_KEY`) and measures whether they can "
            "still find the right Russian chunk -- see README.md's Evaluation "
            "section for why that's a meaningfully harder retrieval problem."
        )

        with open(RETRIEVAL_RESULTS_PATH, encoding="utf-8") as f:
            results = json.load(f)

        present_langs = sorted({
            lang for by_lang in results.values() for lang in by_lang if lang != "all"
        })
        lang_keys = present_langs + ["all"]
        lang_tabs = st.tabs([LANG_LABELS.get(k, k.upper()) if k != "all" else "🌐 All" for k in lang_keys])

        for tab, lang_key in zip(lang_tabs, lang_keys):
            with tab:
                rows = []
                for strategy, by_lang in results.items():
                    metrics = by_lang.get(lang_key)
                    if metrics:
                        rows.append({
                            "strategy": strategy,
                            "hit_rate": metrics["hit_rate"],
                            "mrr": metrics["mrr"],
                            "precision@1": metrics["precision_at_1"],
                            "n questions": metrics["n"],
                        })

                if not rows:
                    st.write("No data for this language.")
                    continue

                metrics_df = pd.DataFrame(rows).set_index("strategy")
                st.dataframe(
                    metrics_df.style.format({
                        "hit_rate": "{:.3f}", "mrr": "{:.3f}",
                        "precision@1": "{:.3f}", "n questions": "{:.0f}",
                    })
                )

                c1, c2, c3 = st.columns(3)
                c1.bar_chart(metrics_df["hit_rate"])
                c2.bar_chart(metrics_df["mrr"])
                c3.bar_chart(metrics_df["precision@1"])
