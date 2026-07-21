import time

from jdg_assistant.rag.hybrid import HybridRAG
from jdg_assistant.rag.base import extract_links
from jdg_assistant.metrics.cost import calculate_cost, LLMCallRecord


class RAGWithMetrics(HybridRAG):
    """HybridRAG variant that records cost/latency/token metrics for every
    call, split out by retrieval strategy and language so the dashboard can
    compare quality and cost side by side."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_call: LLMCallRecord = None
        self.last_links = []
        self.session_cost = 0.0

    def rag(self, query, lang=None, strategy="hybrid", budget_limit=None):
        search_results = self.search(query, lang=lang, strategy=strategy)
        self.last_links = extract_links(search_results)
        prompt = self.build_prompt(query, search_results)

        start_time = time.time()
        response = self._call_llm(prompt)
        response_time = time.time() - start_time

        self._log_response(query, prompt, response, response_time, lang, strategy)

        if budget_limit is not None and self.session_cost > budget_limit:
            raise RuntimeError(
                f"Session cost ${self.session_cost:.4f} exceeded budget "
                f"limit ${budget_limit:.4f}"
            )

        return self.last_call.answer

    def _call_llm(self, prompt):
        input_messages = [
            {"role": "developer", "content": self.instructions},
            {"role": "user", "content": prompt},
        ]
        return self.llm_client.responses.create(model=self.model, input=input_messages)

    def _log_response(self, question, prompt, response, response_time, lang, strategy):
        usage = response.usage
        cost = calculate_cost(self.model, usage)
        self.session_cost += cost

        self.last_call = LLMCallRecord(
            model=self.model,
            prompt=prompt,
            instructions=self.instructions,
            answer=response.output_text,
            question=question,
            lang=lang or "unknown",
            strategy=strategy,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            response_time=response_time,
            cost=cost,
        )
