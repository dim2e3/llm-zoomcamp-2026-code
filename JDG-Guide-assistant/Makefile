ingest:
	uv run python scripts/ingest.py

reingest:
	uv run python scripts/ingest.py --force

check-freshness:
	uv run python scripts/check_freshness.py

init-db:
	uv run python scripts/init_db.py

run:
	uv run python scripts/run_assistant.py

chat:
	uv run streamlit run src/jdg_assistant/web/app.py

dashboard:
	uv run streamlit run src/jdg_assistant/web/dashboard.py --server.port 8502

generate-data:
	uv run python scripts/generate_data.py

ground-truth-faq:
	uv run python scripts/build_faq_ground_truth.py

ground-truth-crosslingual:
	uv run python scripts/build_crosslingual_ground_truth.py

ground-truth-llm:
	uv run python scripts/generate_ground_truth.py

eval-retrieval:
	uv run python scripts/eval_retrieval.py

up:
	docker compose up --build

down:
	docker compose down
