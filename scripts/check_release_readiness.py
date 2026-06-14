from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLIENT_API_FILES = [
    ROOT / "apps/web/src/features/charts/api.ts",
    ROOT / "apps/web/src/features/platform/api.ts",
]
NEXT_CONFIG = ROOT / "apps/web/next.config.ts"


def main() -> int:
    failures: list[str] = []

    for path in CLIENT_API_FILES:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        if "http://127.0.0.1:8000" in text or "http://localhost:8000" in text:
            failures.append(f"{rel} defaults to a loopback API URL")
        normalized = " ".join(text.split())
        if '?? "";' not in normalized:
            failures.append(f"{rel} does not default to same-origin API requests")

    next_config = NEXT_CONFIG.read_text(encoding="utf-8")
    required_snippets = [
        "async rewrites()",
        "process.env.BACKEND_API_URL",
        "source: \"/api/:path*\"",
        "destination: `${backendApiUrl}/api/:path*`",
    ]
    for snippet in required_snippets:
        if snippet not in next_config:
            failures.append(f"apps/web/next.config.ts missing {snippet}")

    if failures:
        print("Release readiness check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Release readiness check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
