"""Export the FastAPI OpenAPI spec to a JSON file.

Usage:
    uv run python scripts/export_openapi.py [output_path]

Defaults to writing `openapi.json` in the backend directory. The frontend's
HeyAPI codegen (`npm run generate:api`) consumes this file.
"""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

DEFAULT_OUTPUT = BACKEND_DIR / "openapi.json"


def main() -> None:
    """Write the OpenAPI spec to the output path."""
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    spec = app.openapi()
    output.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"Wrote OpenAPI spec to {output}")


if __name__ == "__main__":
    main()
