"""Dump the FastAPI app's OpenAPI schema to docs/api/openapi.json.

Run from the backend directory with the project venv active:

    python export_openapi.py

Importing ``main`` triggers the schema bootstrap (``create_all`` plus
``ensure_schema_updates``), so a working DATABASE_URL is required —
the same one you use for local development.
"""
import json
from pathlib import Path

from main import app

OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "api" / "openapi.json"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(app.openapi(), indent=2))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
