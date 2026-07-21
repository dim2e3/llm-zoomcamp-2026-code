"""Build a retrieval ground-truth set: one LLM-generated question per chunk,
useful for evaluating search over the JDG knowledge base."""
import random
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
from pydantic import BaseModel

from jdg_assistant.ingestion.source import load_jdg_docs
from jdg_assistant.evaluation.llm_utils import llm_structured_retry, map_progress

GEN_INSTRUCTIONS_RU = """
Ты помогаешь составить тестовый набор вопросов для оценки поиска в базе
знаний о ведении ИП (JDG) в Польше. По данному фрагменту текста придумай ОДИН
вопрос на русском языке, на который этот фрагмент является ответом.
Вопрос должен быть таким, как его задал бы реальный пользователь -- не
цитируй текст дословно.
""".strip()

GEN_INSTRUCTIONS_EN = """
You help build a test set of questions to evaluate search over a knowledge
base about running a sole proprietorship (JDG) in Poland. Given a text
chunk, write ONE English question that this chunk answers. Phrase it the way
a real user would ask it -- do not quote the text verbatim.
""".strip()

GEN_PROMPT = """
TITLE: {title}
SECTION: {section}
TEXT:
{content}
""".strip()


class GeneratedQuestion(BaseModel):
    question: str


def generate_question(doc, client):
    instructions = GEN_INSTRUCTIONS_EN if doc["lang"] == "en" else GEN_INSTRUCTIONS_RU
    prompt = GEN_PROMPT.format(
        title=doc["title"], section=doc["section"], content=doc["content"][:1500]
    )
    result, _usage = llm_structured_retry(client, instructions, prompt, GeneratedQuestion)
    return {
        "question": result.question,
        "doc_id": doc["doc_id"],
        "lang": doc["lang"],
        "source": "llm-generated",
    }


def build_ground_truth(sample_size=150, seed=42, max_workers=8):
    docs = load_jdg_docs()

    # Skip the flat glossary chunk -- it's a whole-page bag of terms, not a
    # single-answer target, so it isn't a fair retrieval-eval item.
    candidates = [d for d in docs if d["page"] != "glossary"]

    random.Random(seed).shuffle(candidates)
    sample = candidates[:sample_size]

    client = OpenAI()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        ground_truth = map_progress(pool, sample, lambda d: generate_question(d, client))

    return ground_truth


TRANSLATE_INSTRUCTIONS = {
    "pl": """
You translate questions about running a sole proprietorship (JDG) in Poland
into natural, colloquial Polish, the way a real user would type it -- not a
literal word-for-word translation. Keep JDG-specific terms as they already
appear in Polish usage (ZUS, JDG, PESEL, CEIDG, Urząd Skarbowy, etc.).
""".strip(),
    "uk": """
Ти перекладаєш питання про ведення ІП (JDG) у Польщі природною розмовною
українською мовою, так як реальний користувач міг би її написати -- не
дослівний переклад. Залиш специфічні терміни як є (ZUS, JDG, PESEL, CEIDG
тощо).
""".strip(),
    "be": """
Ты перакладаеш пытанні пра вядзенне ІП (JDG) у Польшчы натуральнай размоўнай
беларускай мовай, так як рэальны карыстальнік мог бы яе напісаць -- не
даслоўны пераклад. Пакінь спецыфічныя тэрміны як ёсць (ZUS, JDG, PESEL, CEIDG
і інш.).
""".strip(),
}

TRANSLATE_PROMPT = "QUESTION: {question}"


class TranslatedQuestion(BaseModel):
    question: str


def translate_question(item, target_lang, client):
    instructions = TRANSLATE_INSTRUCTIONS[target_lang]
    prompt = TRANSLATE_PROMPT.format(question=item["question"])
    result, _usage = llm_structured_retry(client, instructions, prompt, TranslatedQuestion)
    return {
        "question": result.question,
        "doc_id": item["doc_id"],  # the target chunk doesn't change -- only the question's language does
        "lang": target_lang,
        "source": f"faq-translated-{item['lang']}",
    }


def build_cross_lingual_ground_truth(base_items, target_langs=("pl", "uk", "be"), max_workers=8):
    """Translate an existing (Russian) ground-truth set into other query
    languages that the corpus itself has no content in, keeping the same
    doc_id target. This tests cross-lingual retrieval specifically: can a
    Polish/Ukrainian/Belarusian question still find the right Russian chunk?
    """
    client = OpenAI()
    translated = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for target_lang in target_langs:
            translated.extend(map_progress(
                pool, base_items,
                lambda item, tl=target_lang: translate_question(item, tl, client),
            ))

    return translated


def build_faq_ground_truth(docs=None):
    """Ground truth built directly from the real FAQ page (docs/faq.md /
    docs/faq.en.md) instead of LLM-generated questions.

    Each FAQ entry is already phrased as a real user question (it's a level-3
    heading, e.g. "Можно ли податься на BlueCard как JDG"), and
    ingestion.source.chunk_body() already splits the FAQ page into exactly
    one chunk per question -- so no synthesis is needed, just extraction.
    This is free (no LLM calls) and, unlike the LLM-generated set, reflects
    questions real users actually asked.
    """
    docs = docs if docs is not None else load_jdg_docs()
    faq_docs = [d for d in docs if d["page"] == "faq"]

    return [
        {
            "question": doc["section"],
            "doc_id": doc["doc_id"],
            "lang": doc["lang"],
            "source": "faq",
        }
        for doc in faq_docs
    ]
