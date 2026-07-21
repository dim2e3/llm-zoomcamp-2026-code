"""Compare the commit the local cache was ingested at against the latest
commit on the source repo/branch, and propose a reingest if they differ."""
from jdg_assistant.ingestion.source import REPO, BRANCH, check_freshness

if __name__ == "__main__":
    result = check_freshness()

    print(f"Repo:           {REPO}@{BRANCH}")
    print(f"Cached commit:  {result['cached_commit'] or '(no cache yet)'}")
    print(f"Latest commit:  {result['latest_commit']}")

    if result["cached_commit"] is None:
        print("\nNo cached data yet -- run `make ingest` to build it.")
    elif result["stale"]:
        print("\nCached data is STALE (upstream guide has new commits).")
        print("Run `make reingest` to refresh.")
    else:
        print("\nUp to date -- no reingest needed.")
