from jdg_assistant.rag.base import RAGBase, reciprocal_rank_fusion, CONTENT_LANGS


class HybridRAG(RAGBase):
    """RAGBase variant that fuses keyword search (minsearch.Index) and
    embedding search (minsearch.VectorSearch) with Reciprocal Rank Fusion,
    then optionally reranks the fused candidates with a cross-encoder."""

    def __init__(
        self,
        keyword_index,
        vector_index,
        embedder,
        llm_client,
        reranker=None,
        rrf_k=60,
        **kwargs,
    ):
        super().__init__(index=keyword_index, llm_client=llm_client, **kwargs)
        self.keyword_index = keyword_index
        self.vector_index = vector_index
        self.embedder = embedder
        self.reranker = reranker
        self.rrf_k = rrf_k

    def search(self, query, num_results=5, lang=None, strategy='hybrid'):
        # The corpus itself only has RU/EN content. A query in a language
        # that isn't indexed (e.g. Polish/Ukrainian/Belarusian) has no
        # same-language chunks to filter to, so search unfiltered across the
        # whole RU+EN corpus instead -- this is cross-lingual retrieval, not
        # same-language retrieval.
        filter_dict = {'lang': lang} if lang in CONTENT_LANGS else {}

        keyword_results = self._keyword_search(query, filter_dict)
        vector_results = self._vector_search(query, filter_dict)

        if strategy == 'keyword':
            candidates = keyword_results
        elif strategy == 'vector':
            candidates = vector_results
        else:
            candidates = reciprocal_rank_fusion(
                [keyword_results, vector_results], k=self.rrf_k
            )

        candidates = candidates[:max(num_results * 4, num_results)]

        if self.reranker is not None:
            candidates = self.reranker.rerank(query, candidates, top_k=num_results)
        else:
            candidates = candidates[:num_results]

        return candidates

    def _keyword_search(self, query, filter_dict, num_results=10):
        boost_dict = {'title': 1.0, 'section': 3.0, 'content': 1.0}
        return self.keyword_index.search(
            query,
            num_results=num_results,
            boost_dict=boost_dict,
            filter_dict=filter_dict,
        )

    def _vector_search(self, query, filter_dict, num_results=10):
        query_vector = self.embedder.encode(query, normalize_embeddings=True)
        return self.vector_index.search(
            query_vector,
            num_results=num_results,
            filter_dict=filter_dict,
        )
