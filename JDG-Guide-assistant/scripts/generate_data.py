import random
import time

from jdg_assistant.metrics.cost import LLMCallRecord
from jdg_assistant.persistence.conversations import save_conversation
from jdg_assistant.persistence.feedback import save_feedback

SAMPLE_QUESTIONS = [
    ("Как зарегистрировать JDG?", "ru"),
    ("Какие взносы ZUS платит новый предприниматель?", "ru"),
    ("Что такое Ulga na Start?", "ru"),
    ("Как подать декларацию PIT?", "ru"),
    ("How do I register for VAT?", "en"),
    ("What is a Profil Zaufany?", "en"),
    ("How do I close a JDG?", "en"),
]

SAMPLE_ANSWERS = [
    "You register a JDG through the CEIDG portal using your PESEL and Profil Zaufany.",
    "New entrepreneurs typically qualify for reduced ZUS contributions for the first period.",
    "Ulga na Start exempts you from social insurance contributions for six months.",
    "PIT declarations are filed annually through e-Urzad Skarbowy or your accounting tool.",
]

STRATEGIES = ["hybrid", "keyword", "vector"]
RELEVANCE = ["RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT"]


def fake_record(question, lang, answer):
    return LLMCallRecord(
        model="gpt-5.4-mini",
        prompt=question,
        instructions="",
        answer=answer,
        question=question,
        lang=lang,
        strategy=random.choice(STRATEGIES),
        prompt_tokens=random.randint(300, 1200),
        completion_tokens=random.randint(50, 300),
        total_tokens=random.randint(400, 1500),
        response_time=random.uniform(0.5, 5.0),
        cost=random.uniform(0.0001, 0.01),
    )


def random_score():
    return random.choice([1, 1, 1, 1, -1])


def generate_one():
    question, lang = random.choice(SAMPLE_QUESTIONS)
    answer = random.choice(SAMPLE_ANSWERS)
    record = fake_record(question, lang, answer)

    conversation_id = save_conversation(record)

    if random.random() < 0.7:
        relevance = random.choice(RELEVANCE)
        save_feedback(
            conversation_id, "judge",
            relevance=relevance,
            explanation=f"Answer is {relevance.lower()}.",
        )

    if random.random() < 0.5:
        save_feedback(conversation_id, "user", score=random_score())


def generate_live():
    print("Starting live data generation (Ctrl+C to stop)...", flush=True)
    while True:
        generate_one()
        time.sleep(1)


if __name__ == "__main__":
    try:
        generate_live()
    except KeyboardInterrupt:
        print("Stopped.")
