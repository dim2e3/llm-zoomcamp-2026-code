import re

INSTRUCTIONS = '''
You are an assistant helping foreign nationals set up and run a sole
proprietorship (JDG) in Poland. Answer questions using only the provided
context, which comes from a community-maintained JDG guide.

The context is a list of excerpts, each starting with a heading line
("# page title / section title") and ending with its source URL. Before
concluding that the context doesn't answer the question, check every
excerpt's heading and content -- if a heading closely matches or restates
the question, that excerpt almost certainly contains the answer, even if
other excerpts in the context are unrelated.

Excerpts may contain Markdown links, e.g. [some text](https://...). Keep any
such links that are relevant to your answer, formatted exactly the same way,
instead of describing them in plain text. If an excerpt itself has no
relevant link but you are drawing on it, you may cite its source URL the
same way (e.g. "see [the JDG registration guide](https://...)").

Answer in the same language as the question. Only if none of the excerpts
address the question, respond with "I don't know." (or "Не знаю." for
Russian questions) rather than guessing.
'''.strip()

PROMPT_TEMPLATE = '''
QUESTION: {question}

CONTEXT:
{context}
'''.strip()

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")

# Languages the corpus actually has indexed content in. A query in any other
# language (e.g. Polish/Ukrainian/Belarusian) has no same-language chunks to
# filter to, so search() should skip the lang filter for those instead of
# filtering to an empty set.
CONTENT_LANGS = {"ru", "en"}


def extract_links(search_results):
    """Pull every Markdown link out of the retrieved chunks (already
    resolved to absolute URLs during ingestion), plus each chunk's own
    source page, deduplicated by URL and in retrieval-rank order.

    Used to reliably surface hyperlinks in the UI regardless of whether the
    LLM chooses to echo them in its answer -- relying on the model to
    faithfully reproduce every link from context isn't reliable enough on
    its own.
    """
    links = []
    seen_urls = set()

    def add(text, url):
        if url not in seen_urls:
            seen_urls.add(url)
            links.append({"text": text, "url": url})

    for doc in search_results:
        for text, url in MARKDOWN_LINK_RE.findall(doc["content"]):
            add(text, url)
        add(f"{doc['title']} / {doc['section']}", doc["url"])

    return links


def reciprocal_rank_fusion(result_lists, k=60):
    """Merge several ranked lists of docs (each a list of dicts with a
    'doc_id' field) into one ranking using Reciprocal Rank Fusion."""
    scores = {}
    docs_by_id = {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            doc_id = doc["doc_id"]
            docs_by_id[doc_id] = doc
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)

    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    return [docs_by_id[doc_id] for doc_id in ranked_ids]


class RAGBase:

    def __init__(
        self,
        index,
        llm_client,
        instructions=INSTRUCTIONS,
        prompt_template=PROMPT_TEMPLATE,
        model='gpt-5.4-mini',
    ):
        self.index = index
        self.llm_client = llm_client
        self.instructions = instructions
        self.prompt_template = prompt_template
        self.model = model

    def search(self, query, num_results=5, lang=None):
        boost_dict = {'title': 1.0, 'section': 3.0, 'content': 1.0}
        filter_dict = {'lang': lang} if lang in CONTENT_LANGS else {}

        return self.index.search(
            query,
            num_results=num_results,
            boost_dict=boost_dict,
            filter_dict=filter_dict,
        )

    def build_context(self, search_results):
        lines = []

        for doc in search_results:
            lines.append(f"# {doc['title']} / {doc['section']}")
            lines.append(doc['content'])
            lines.append(f"Source: {doc['url']}")
            lines.append('')

        return '\n'.join(lines).strip()

    def build_prompt(self, query, search_results):
        context = self.build_context(search_results)
        return self.prompt_template.format(question=query, context=context)

    def llm(self, prompt):
        input_messages = [
            {'role': 'developer', 'content': self.instructions},
            {'role': 'user', 'content': prompt},
        ]

        response = self.llm_client.responses.create(
            model=self.model,
            input=input_messages,
        )

        return response.output_text

    def rag(self, query, lang=None):
        search_results = self.search(query, lang=lang)
        prompt = self.build_prompt(query, search_results)
        answer = self.llm(prompt)
        return answer
