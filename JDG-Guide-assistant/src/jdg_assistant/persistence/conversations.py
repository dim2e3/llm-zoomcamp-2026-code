from dataclasses import dataclass
from datetime import datetime

from jdg_assistant.persistence.db import get_db_connection, DB_TIMEZONE
from jdg_assistant.metrics.cost import LLMCallRecord


def save_conversation(record):
    timestamp = datetime.now(DB_TIMEZONE)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (
                    question, answer, lang, strategy, model, instructions, prompt,
                    prompt_tokens, completion_tokens, total_tokens,
                    response_time, cost, timestamp
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    record.question,
                    record.answer,
                    record.lang,
                    record.strategy,
                    record.model,
                    record.instructions,
                    record.prompt,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.total_tokens,
                    record.response_time,
                    record.cost,
                    timestamp,
                ),
            )
            conversation_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return conversation_id


def row_to_record(row):
    return LLMCallRecord(
        model=row[5],
        prompt=row[7],
        instructions=row[6],
        answer=row[2],
        question=row[1],
        lang=row[3],
        strategy=row[4],
        prompt_tokens=row[8],
        completion_tokens=row[9],
        total_tokens=row[10],
        response_time=row[11],
        cost=row[12],
        timestamp=row[13],
    )


def get_conversations(limit=10):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, question, answer, lang, strategy, model,
                       instructions, prompt,
                       prompt_tokens, completion_tokens, total_tokens,
                       response_time, cost, timestamp
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [row_to_record(row) for row in rows]


@dataclass
class Stats:
    total: int
    avg_response_time: float
    total_cost: float
    avg_tokens: float
    avg_prompt_tokens: float


def get_stats():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*),
                    AVG(response_time),
                    SUM(cost),
                    AVG(total_tokens)::float8,
                    AVG(prompt_tokens)::float8
                FROM conversations
            """)
            row = cur.fetchone()
    finally:
        conn.close()

    return Stats(
        total=row[0],
        avg_response_time=row[1],
        total_cost=row[2],
        avg_tokens=row[3],
        avg_prompt_tokens=row[4],
    )


def get_cost_by_strategy():
    """Cost/token breakdown per retrieval strategy -- lets the dashboard show
    quality (hit-rate/MRR, evaluated separately) and cost side by side."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT strategy,
                       COUNT(*),
                       SUM(cost),
                       AVG(cost),
                       AVG(prompt_tokens)::float8
                FROM conversations
                GROUP BY strategy
                ORDER BY strategy
            """)
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "strategy": r[0], "count": r[1], "total_cost": r[2],
            "avg_cost": r[3], "avg_prompt_tokens": r[4],
        }
        for r in rows
    ]


def get_cost_by_lang():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT lang, COUNT(*), SUM(cost), AVG(cost)
                FROM conversations
                GROUP BY lang
                ORDER BY lang
            """)
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {"lang": r[0], "count": r[1], "total_cost": r[2], "avg_cost": r[3]}
        for r in rows
    ]
