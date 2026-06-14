from __future__ import annotations

import os

import uvicorn

from app.main import app


def main() -> None:
    host = os.getenv("STOCK_APP_API_HOST", "127.0.0.1")
    port = int(os.getenv("STOCK_APP_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
