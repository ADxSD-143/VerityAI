"""Local development server.

    python scripts/run_dev.py        # http://127.0.0.1:8000

Requires the package to be installed (``pip install -e ".[dev]"``) so ``app`` is
importable.
"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("VERITY_HOST", "127.0.0.1"),
        port=int(os.environ.get("VERITY_PORT", "8000")),
        reload=True,
    )
