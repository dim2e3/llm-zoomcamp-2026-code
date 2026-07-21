"""Create the Postgres tables if they don't exist yet.

Usage:
    uv run python scripts/init_db.py            # create tables (safe to rerun)
    uv run python scripts/init_db.py --reset     # wipe and recreate everything
"""
import sys

from jdg_assistant.persistence.db import init_db, init_feedback

if __name__ == "__main__":
    reset = "--reset" in sys.argv[1:]
    init_db(drop=reset)
    init_feedback(drop=reset)
    print("Database ready (reset)" if reset else "Database ready")
