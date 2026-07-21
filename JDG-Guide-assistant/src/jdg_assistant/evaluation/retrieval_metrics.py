def hit_rate(relevance_lists):
    return sum(any(rel) for rel in relevance_lists) / len(relevance_lists)


def mrr(relevance_lists):
    total = 0.0
    for rel in relevance_lists:
        for rank, is_relevant in enumerate(rel, start=1):
            if is_relevant:
                total += 1.0 / rank
                break
    return total / len(relevance_lists)


def precision_at_1(relevance_lists):
    return sum(rel[0] if rel else False for rel in relevance_lists) / len(relevance_lists)


def compute_metrics(relevance_lists):
    return {
        "hit_rate": hit_rate(relevance_lists),
        "mrr": mrr(relevance_lists),
        "precision_at_1": precision_at_1(relevance_lists),
        "n": len(relevance_lists),
    }


def evaluate_retrieval(ground_truth, search_fn):
    """ground_truth: list of {'question': str, 'doc_id': str, 'lang': str}
    search_fn: callable(question, lang) -> list of result docs (with doc_id)

    Returns hit-rate, MRR, and precision@1 over the given ground-truth set.
    """
    relevance_lists = []

    for item in ground_truth:
        results = search_fn(item["question"], item.get("lang"))
        relevance_lists.append([doc["doc_id"] == item["doc_id"] for doc in results])

    return compute_metrics(relevance_lists)


def evaluate_retrieval_by_lang(ground_truth, search_fn, langs=None):
    """Same as evaluate_retrieval, but broken out per language plus an "all"
    entry over the combined set -- lets the dashboard compare retrieval
    quality across languages side by side instead of only seeing an average.

    langs defaults to whatever languages are actually present in the ground
    truth, so this scales automatically from 2 languages (RU/EN) to however
    many are added (e.g. PL/UK/BE) without needing a code change here.
    """
    if langs is None:
        langs = sorted(set(item.get("lang") for item in ground_truth if item.get("lang")))

    results = {}

    for lang in langs:
        subset = [item for item in ground_truth if item.get("lang") == lang]
        if subset:
            results[lang] = evaluate_retrieval(subset, search_fn)

    results["all"] = evaluate_retrieval(ground_truth, search_fn)
    return results
