"""Fetch and cache the JDG guide content (data/jdg_docs.json).

Usage:
    uv run python scripts/ingest.py            # use existing cache if present
    uv run python scripts/ingest.py --force     # re-fetch even if cached
"""
import sys

from jdg_assistant.ingestion.source import REPO, BRANCH, load_jdg_docs

if __name__ == "__main__":
    force = "--force" in sys.argv[1:]

    docs = load_jdg_docs(force_refresh=force)
    print(f"Ingested from {REPO}@{BRANCH}")
    print(f"Loaded {len(docs)} chunks from {len(set(d['page'] for d in docs))} pages")
    print(f"Languages: {sorted(set(d['lang'] for d in docs))}")
