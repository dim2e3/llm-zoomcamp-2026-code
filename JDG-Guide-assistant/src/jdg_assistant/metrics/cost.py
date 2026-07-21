from dataclasses import dataclass, field
from datetime import datetime

# $ per 1M tokens (input, output). Extend this table as new models are used
# so cost stays correct regardless of which model served a given query.
MODEL_RATES = {
    "gpt-5.4-mini": (0.15, 0.60),
    "gpt-5.4": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}

# Local embedding/reranker models run on CPU with no per-call API cost.
EMBEDDING_COST_PER_QUERY = 0.0


def calculate_cost(model, usage):
    input_rate, output_rate = MODEL_RATES.get(model, (0.0, 0.0))
    cost = (
        usage.input_tokens * input_rate + usage.output_tokens * output_rate
    ) / 1_000_000
    return cost + EMBEDDING_COST_PER_QUERY


@dataclass
class LLMCallRecord:
    model: str
    prompt: str
    instructions: str
    answer: str
    question: str
    lang: str
    strategy: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    response_time: float
    cost: float
    timestamp: datetime = field(default_factory=datetime.now)
