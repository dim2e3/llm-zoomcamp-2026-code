# JDG Guide Assistant

A chatbot that answers questions about setting up and running a sole
proprietorship (JDG) in Poland as a foreigner. Ask it in Russian or English,
e.g. *"Как зарегистрировать JDG?"* or *"How do I register for VAT?"* — it
answers using a community-written guide, not guesswork.

## Run it in one click

You don't need to know Python, or anything about programming, to try this.
You need two things installed on your computer:

1. **Docker Desktop** — [download it here](https://www.docker.com/products/docker-desktop/)
   and install it like any other app. Open it once so it's running in the
   background (you'll see a whale icon in your taskbar/menu bar).
2. **An OpenAI API key** — this is what pays for the AI's answers. Get one at
   [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   (you'll need to add a few dollars of credit — this project is cheap to run,
   a few cents per question).

Then:

1. Download this project (green "Code" button on GitHub → "Download ZIP", then
   unzip it — or `git clone` if you know how) and open the `JDG-Guide-assistant` folder.
2. Find the file named `.env.example`, make a copy of it, and rename the copy
   to `.env` (just `.env`, nothing before the dot).
3. Open `.env` in any text editor (Notepad, TextEdit, etc.) and replace
   `your-key-here` with the OpenAI key from step 2. Save the file.
4. Open a terminal in that `JDG-Guide-assistant` folder:
   - **Windows**: right-click inside the folder → "Open in Terminal"
   - **Mac**: right-click the folder → Services → "New Terminal at Folder"
     (or open Terminal and type `cd ` then drag the folder in)
5. Type this one command and press Enter:

   ```
   docker compose up --build
   ```

That's it. The first run takes a few minutes (it's downloading and setting
everything up); after that, wait until the terminal stops scrolling and
settles down. Then open your web browser and go to:

- **http://localhost:8501** — the chat app, ask it questions here
- **http://localhost:8502** — a simple built-in dashboard showing how much every answer cost
- **http://localhost:3000** — a fuller Grafana dashboard (same data, nicer charts); open it,
  no login needed to view it (to edit, log in with `admin` / `admin`, or whatever
  you set `GF_ADMIN_PASSWORD` to in `.env`)

To stop everything: go back to the terminal and press `Ctrl+C`, or close it.
To start it again later, just repeat step 5 — no need to redo steps 1-4.

> **Nothing to install manually beyond Docker.** The one command above starts
> a small database, sets it up, and starts both web pages automatically.

---

## Dataset

Content is sourced from [`sobolevbel/jdg`](https://github.com/sobolevbel/jdg), a
community-maintained, **CC0-licensed** MkDocs guide (RU-primary, fully translated
to EN — 38 pages / 76 files). It covers PESEL/Profil Zaufany onboarding, JDG/VAT
registration, ZUS social-insurance regimes, tax declarations (PIT/VAT/ZUS/JPK),
residence-permit legalization, and accounting-tool walkthroughs (inFakt, wFirma).
`jdg_assistant.ingestion.source` fetches every page, splits it into
heading-scoped chunks, and caches the result to `data/jdg_docs.json` along
with the commit SHA it was ingested at.

The source repo/branch are configured via `.env` (`JDG_REPO`, `JDG_BRANCH` --
see `.env.example`), not hardcoded, so this can point at a fork or a pinned
branch without code changes.

### Keeping the cache fresh

`data/jdg_docs.json` records the commit it was built from. To check whether
the upstream guide has moved on:

```bash
make check-freshness   # uv run python scripts/check_freshness.py
```

This fetches the latest commit on `JDG_REPO`@`JDG_BRANCH` and compares it to
the cached one, proposing a reingest if they differ:

```bash
make reingest           # uv run python scripts/ingest.py --force
```

## Project layout

Package code lives in `src/jdg_assistant/`, organized by domain; one-off CLI
entry points live in `scripts/`; the two Streamlit apps live under `web/` and
are run directly by path.

```
src/jdg_assistant/
  ingestion/    source.py (fetch/parse/chunk), indexing.py (keyword + vector index)
  rag/          base.py (RAGBase, RRF), hybrid.py (HybridRAG), reranker.py (cross-encoder)
  metrics/      cost.py (rates, LLMCallRecord), tracking.py (RAGWithMetrics)
  persistence/  db.py (connection, schema), conversations.py, feedback.py
  evaluation/   llm_utils.py, retrieval_metrics.py (hit-rate/MRR), judge.py, ground_truth.py
  web/          app.py (chat), dashboard.py (monitoring)
  assistant.py  composition root: create_assistant() wires the above together
scripts/
  ingest.py, init_db.py, run_assistant.py, generate_data.py,
  generate_ground_truth.py, eval_retrieval.py, check_freshness.py
grafana/
  provisioning/datasources/  auto-registers Postgres as a Grafana data source
  provisioning/dashboards/   tells Grafana where to load dashboard JSON from
  dashboards/                the actual dashboard definition (jdg_assistant.json)
```

## Architecture

- **Ingestion** (`ingestion/source.py`, `ingestion/indexing.py`): fetches and
  chunks the markdown guide, builds a `minsearch.Index` (keyword/TF-IDF) and a
  `minsearch.VectorSearch` (`sentence-transformers/all-MiniLM-L6-v2`
  embeddings) over the same chunks.
- **Retrieval** (`rag/hybrid.py`): `HybridRAG` fuses keyword + vector search
  results with Reciprocal Rank Fusion, then optionally reranks with a local
  CPU cross-encoder (`rag/reranker.py`, `cross-encoder/ms-marco-MiniLM-L-6-v2`).
  Supports `keyword` / `vector` / `hybrid` strategies and RU/EN language
  filtering, both selectable in the UI.
- **Generation**: `RAGWithMetrics` (`metrics/tracking.py`) wraps `HybridRAG`,
  calling the OpenAI Responses API and recording cost/latency/tokens per call
  (`metrics/cost.py`), broken out by retrieval strategy and language.
- **Evaluation**: `evaluation/ground_truth.py` builds a ground-truth question
  set (one LLM-generated question per chunk); `scripts/eval_retrieval.py`
  compares keyword/vector/hybrid/hybrid+rerank with hit-rate and MRR
  (`evaluation/retrieval_metrics.py`); `evaluation/judge.py` scores generated
  answers with an LLM-as-judge.
- **Interface**: `web/app.py` (Streamlit chat, with a per-session cost budget
  guard) and `web/dashboard.py` (monitoring: cost over time, cost/tokens
  broken down by retrieval strategy and by language, judge relevance, user
  feedback), both reading from Postgres (`persistence/`).
- **Monitoring dashboard**: Grafana (`grafana/`), reading the same Postgres
  tables directly via SQL, provisioned automatically (data source + the
  `jdg_assistant` dashboard) so it needs no manual setup -- the panels mirror
  `web/dashboard.py` (cost over time, cost/tokens by strategy and language,
  judge relevance, user feedback) plus response-time trends.
- **Containerization**: `Dockerfile` + `docker-compose.yaml` run Postgres +
  a one-shot DB-init step + chat app + dashboard + Grafana together.

## Running it from source (for development)

```bash
cp .env.example .env   # fill in OPENAI_API_KEY

uv sync                          # editable-installs jdg_assistant from src/
uv run python scripts/ingest.py  # fetch + cache the guide (data/jdg_docs.json)

docker compose up postgres -d
uv run python scripts/init_db.py # create tables

make chat                        # Streamlit chat app, port 8501
make dashboard                   # monitoring dashboard, port 8502
```

Or everything in Docker (this is what "one click" above does):
`docker compose up --build`.

## Evaluation

```bash
uv run python scripts/generate_ground_truth.py   # -> ground_truth.json
uv run python scripts/eval_retrieval.py          # -> retrieval_eval_results.json
```

Fill in results here after running:

| Strategy       | Hit-rate | MRR |
|----------------|----------|-----|
| keyword        |          |     |
| vector         |          |     |
| hybrid         |          |     |
| hybrid+rerank  |          |     |

## Attribution

Guide content © [sobolevbel/jdg](https://github.com/sobolevbel/jdg) contributors,
[CC0-1.0](https://github.com/sobolevbel/jdg/blob/master/LICENSE) (public domain).
