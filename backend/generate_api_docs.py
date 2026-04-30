"""Generate static HTML API documentation for the backend modules.

This script uses Python's built-in ``pydoc`` tool so the repository can ship
with browsable HTML documentation without relying on external packages.
"""

import os
import pydoc
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
OUTPUT_DIR = REPO_ROOT / "docs" / "api"
MODULES = [
    "database",
    "models",
    "ollama_helper",
    "create_test_course",
    "main",
]


def build_index() -> None:
    """Write a simple landing page that links to each generated module page."""
    links = "\n".join(
        f'      <li><a href="{module}.html">{module}.html</a></li>'
        for module in MODULES
    )
    index_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>StudySync API Documentation</title>
    <style>
      body {{
        font-family: Arial, sans-serif;
        margin: 2rem auto;
        max-width: 860px;
        line-height: 1.5;
        color: #1f2937;
      }}
      h1 {{
        margin-bottom: 0.25rem;
      }}
      code {{
        background: #f3f4f6;
        padding: 0.1rem 0.3rem;
        border-radius: 4px;
      }}
    </style>
  </head>
  <body>
    <h1>StudySync API Documentation</h1>
    <p>
      Generated with Python's built-in <code>pydoc</code> tool from the backend
      source modules listed below.
    </p>
    <ul>
{links}
    </ul>
  </body>
</html>
"""
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")


def main() -> None:
    """Generate HTML documentation files into ``docs/api``."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    sys.path.insert(0, str(BACKEND_DIR))

    original_cwd = Path.cwd()
    os.chdir(OUTPUT_DIR)
    try:
        for module in MODULES:
            pydoc.writedoc(module)
        build_index()
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()
