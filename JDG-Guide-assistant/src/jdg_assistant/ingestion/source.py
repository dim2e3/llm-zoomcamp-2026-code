"""Fetch and chunk the sobolevbel/jdg guide (JDG in Poland) markdown source."""
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

# Loaded here (not just at the app entry point) so REPO/BRANCH below always
# see .env values, regardless of which script imports this module first.
load_dotenv()

REPO = os.getenv("JDG_REPO", "sobolevbel/jdg")
BRANCH = os.getenv("JDG_BRANCH", "master")

RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
API_TREE_URL = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=true"
API_COMMIT_URL = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"

HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

SITE_BASE = "https://sobolevbel.github.io/jdg"

# Reference-style link definitions, e.g. "[1]: registration_jdg.md" or
# "[7]: https://example.com", normally collected at the bottom of the page.
LINK_DEF_RE = re.compile(r"^\[([^\]]+)\]:\s*(\S+)\s*$", re.MULTILINE)
# Usages of those definitions elsewhere in the page: [link text][1]
REF_LINK_RE = re.compile(r"\[([^\]]+)\]\[([^\]]+)\]")
# Inline links: [link text](target) -- excludes images (![alt](src))
INLINE_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)")
RELATIVE_PAGE_RE = re.compile(r"^([\w./-]+)\.md(#.*)?$")


def _project_root():
    """Walk up from this file until the directory containing pyproject.toml."""
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate project root (no pyproject.toml found)")


CACHE_PATH = _project_root() / "data" / "jdg_docs.json"


def get_latest_commit():
    """SHA of the current tip of REPO/BRANCH on GitHub."""
    resp = requests.get(API_COMMIT_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()["sha"]


def get_cache_info():
    """Metadata (commit, repo, branch, fetched_at) for the local doc cache,
    or None if nothing has been ingested yet."""
    if not CACHE_PATH.exists():
        return None

    with open(CACHE_PATH, encoding="utf-8") as f:
        cache = json.load(f)

    return {
        "commit": cache.get("commit"),
        "repo": cache.get("repo"),
        "branch": cache.get("branch"),
        "fetched_at": cache.get("fetched_at"),
    }


def check_freshness():
    """Compare the cached ingestion commit against the latest commit on
    REPO/BRANCH, to decide whether a reingest is needed."""
    cache_info = get_cache_info()
    latest_commit = get_latest_commit()

    cached_commit = cache_info["commit"] if cache_info else None

    return {
        "cached_commit": cached_commit,
        "latest_commit": latest_commit,
        "stale": cached_commit != latest_commit,
    }


def list_doc_paths():
    resp = requests.get(API_TREE_URL, timeout=30)
    resp.raise_for_status()
    tree = resp.json()["tree"]

    return sorted(
        item["path"]
        for item in tree
        if item["path"].startswith("docs/")
        and item["path"].endswith(".md")
    )


def fetch_raw(path, retries=3):
    url = f"{RAW_BASE}/{path}"
    for attempt in range(retries):
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.text
        time.sleep(2 ** attempt)
    resp.raise_for_status()


def parse_frontmatter(text):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    raw_meta, body = match.groups()
    try:
        meta = yaml.safe_load(raw_meta) or {}
    except yaml.YAMLError:
        meta = {}

    return meta, body


def page_slug(path):
    name = path.split("/")[-1]
    name = name[:-len(".md")]
    if name.endswith(".en"):
        return name[:-len(".en")], "en"
    return name, "ru"


def page_url(slug, lang):
    prefix = "en/" if lang == "en" else ""
    return f"{SITE_BASE}/{prefix}{slug}/"


def _resolve_link_target(target, lang):
    if re.match(r"^(https?://|mailto:|#)", target):
        return target

    match = RELATIVE_PAGE_RE.match(target)
    if not match:
        return target  # not a page link (e.g. a relative image path) -- leave as-is

    slug = match.group(1).rstrip("/").split("/")[-1]
    fragment = match.group(2) or ""
    return page_url(slug, lang) + fragment


def resolve_links(body, lang):
    """Markdown reference-style links ([text][1], with the "[1]: target"
    definition sitting elsewhere on the page) and relative page links
    ([text](page.md)) don't survive a chunk being pulled out of its page.
    Inline everything into absolute URLs so each chunk is self-contained and
    the assistant can quote a working link straight from the chunk it
    retrieved.
    """
    definitions = dict(LINK_DEF_RE.findall(body))
    body = LINK_DEF_RE.sub("", body)

    def replace_ref(match):
        text, label = match.group(1), match.group(2)
        target = definitions.get(label)
        if target is None:
            return match.group(0)
        return f"[{text}]({_resolve_link_target(target, lang)})"

    body = REF_LINK_RE.sub(replace_ref, body)

    def replace_inline(match):
        text, target = match.group(1), match.group(2)
        return f"[{text}]({_resolve_link_target(target, lang)})"

    return INLINE_LINK_RE.sub(replace_inline, body)


def chunk_body(body):
    """Split a markdown page into heading-scoped chunks.

    Each chunk covers one heading (H1/H2/H3) plus the text under it, up to
    (not including) the next heading of any level.
    """
    lines = body.splitlines()

    chunks = []
    current_title = None
    current_lines = []

    def flush():
        text = "\n".join(current_lines).strip()
        if current_title and text:
            chunks.append((current_title, text))

    for line in lines:
        heading = HEADING_RE.match(line)
        if heading:
            flush()
            current_title = heading.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    flush()
    return chunks


def _fetch_documents():
    documents = []
    doc_id = 0

    for path in list_doc_paths():
        slug, lang = page_slug(path)
        raw = fetch_raw(path)
        meta, body = parse_frontmatter(raw)
        body = resolve_links(body, lang)

        page_title = meta.get("title", slug)
        chunks = chunk_body(body)

        for section, content in chunks:
            documents.append({
                "doc_id": f"{slug}-{lang}-{doc_id}",
                "page": slug,
                "title": page_title,
                "section": section,
                "content": content,
                "lang": lang,
                "url": page_url(slug, lang),
            })
            doc_id += 1

    return documents


def load_jdg_docs(use_cache=True, force_refresh=False):
    """Fetch every markdown page in the sobolevbel/jdg guide and split it
    into heading-scoped chunks with page/section/language metadata.

    Results are cached locally (data/jdg_docs.json), alongside the commit
    SHA they were ingested at, since re-fetching and re-parsing ~40 pages on
    every process start is slow and hits GitHub's unauthenticated rate limit
    quickly. Pass force_refresh=True to bypass the cache and re-ingest even
    if it's still present (see also check_freshness()).
    """
    if use_cache and not force_refresh and CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)["documents"]

    documents = _fetch_documents()

    if use_cache:
        cache = {
            "repo": REPO,
            "branch": BRANCH,
            "commit": get_latest_commit(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "documents": documents,
        }
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    return documents
