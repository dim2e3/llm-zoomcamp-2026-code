import streamlit as st

from jdg_assistant.assistant import create_assistant
from jdg_assistant.persistence.feedback import save_feedback
from jdg_assistant.persistence.conversations import save_conversation
from jdg_assistant.evaluation.judge import evaluate_relevance
from jdg_assistant.web.styling import inject_theme, render_letterhead, render_verdict_stamp

SESSION_BUDGET_LIMIT = 0.50  # USD, demo-friendly guard rail

# The guide itself is only written in Russian/English. Polish/Ukrainian/
# Belarusian questions still work (see rag/hybrid.py's CONTENT_LANGS guard),
# but retrieval has to bridge the language gap to RU/EN content, so answer
# quality is expected to vary -- that's what the Evaluation dashboard tab
# measures per language. English listed first: it's the default.
LANGUAGES = {
    "en": "English",
    "ru": "Russian",
    "pl": "Polish",
    "uk": "Ukrainian",
    "be": "Belarusian",
}

st.set_page_config(page_title="JDG Guide Assistant", page_icon="🖋️", layout="centered")
inject_theme()


@st.cache_resource
def get_assistant():
    return create_assistant()


assistant = get_assistant()

render_letterhead(
    "JDG Guide Assistant",
    "Ask about registering and running a sole proprietorship (JDG) in Poland. "
    "Answers are grounded in the community jdg guide "
    "(<a href=\"https://github.com/sobolevbel/jdg\" style=\"color:#F0DFAE\">sobolevbel/jdg</a>, CC0).",
)

col_a, col_b = st.columns(2)
lang = col_a.selectbox(
    "Language", list(LANGUAGES), format_func=lambda x: f"{LANGUAGES[x]} ({x.upper()})"
)
strategy = col_b.selectbox("Retrieval strategy", ["hybrid", "keyword", "vector"])

if lang not in ("ru", "en"):
    st.caption(
        f"⚠️ The guide is only written in Russian/English -- {LANGUAGES[lang]} questions "
        "search that same content cross-lingually, so quality may be lower "
        "(see the Evaluation dashboard tab)."
    )

session_cost = st.session_state.get("session_cost", 0.0)
st.markdown('<p class="jdg-ledger-label">Case budget</p>', unsafe_allow_html=True)
st.progress(min(session_cost / SESSION_BUDGET_LIMIT, 1.0),
            text=f"${session_cost:.4f} / ${SESSION_BUDGET_LIMIT:.2f}")

input_col, ask_col = st.columns([5, 1], vertical_alignment="bottom")
user_input = input_col.text_input("Enter your question:")
ask_clicked = ask_col.button("Ask", type="primary", use_container_width=True)

if ask_clicked and user_input:
    if session_cost >= SESSION_BUDGET_LIMIT:
        st.error("Session budget limit reached -- refresh the page to reset.")
    else:
        with st.spinner("Processing..."):
            answer = assistant.rag(user_input, lang=lang, strategy=strategy)

            record = assistant.last_call
            st.session_state.session_cost = session_cost + record.cost

            conversation_id = save_conversation(record)
            st.session_state.conversation_id = conversation_id

            relevance, explanation = evaluate_relevance(user_input, answer)
            save_feedback(conversation_id, "judge", relevance=relevance, explanation=explanation)

        with st.container(key="jdg-answer-card"):
            st.markdown(answer)  # renders any [text](url) links in the answer

            if assistant.last_links:
                st.markdown("**Related links:**")
                for link in assistant.last_links:
                    st.markdown(f"- [{link['text']}]({link['url']})")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Response time", f"{record.response_time:.2f}s")
            m2.metric("Prompt tokens", record.prompt_tokens)
            m3.metric("Output tokens", record.completion_tokens)
            m4.metric("Cost", f"${record.cost:.4f}")

            render_verdict_stamp(relevance, explanation)

up_col, down_col, _spacer = st.columns([1, 1, 6])
with up_col:
    if st.button("+1"):
        if "conversation_id" in st.session_state:
            save_feedback(st.session_state.conversation_id, "user", score=1)
            st.write("Thanks!")
with down_col:
    if st.button("-1"):
        if "conversation_id" in st.session_state:
            save_feedback(st.session_state.conversation_id, "user", score=-1)
            st.write("Thanks for the feedback!")
