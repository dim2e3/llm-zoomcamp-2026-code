FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
# No live file editing happens inside the container, and Streamlit's watcher
# otherwise walks every installed package (including transformers' large
# lazy-loaded model zoo) trying to find local source paths, which is both
# pointless here and spams the log with harmless torchvision ImportErrors.
ENV STREAMLIT_SERVER_FILE_WATCHER_TYPE=none

COPY pyproject.toml .python-version README.md ./
COPY src ./src
RUN uv sync

COPY . .

CMD ["streamlit", "run", "src/jdg_assistant/web/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
