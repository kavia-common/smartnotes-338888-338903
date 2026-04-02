"""
Generate the OpenAPI schema to notes_backend/interfaces/openapi.json.

Run (inside notes_backend):
  python -m src.api.generate_openapi
"""

import json
import os

from src.api.main import app


def main() -> None:
    """PUBLIC_INTERFACE Generate and write the OpenAPI schema file."""
    openapi_schema = app.openapi()

    output_dir = "interfaces"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "openapi.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
