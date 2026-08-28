from __future__ import annotations
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper.browser import Browser

async def main():
    async with Browser(headless=True) as br:
        html, url = await br.html(
            "data:text/html,<html><head><title>AUTORADAR Smoke</title></head><body><h1>OK</h1></body></html>",
            timeout=15000,
        )
        assert "<h1>OK</h1>" in html or "<h1>OK</h1>".lower() in html.lower(), "HTML smoke test failed"
        assert isinstance(url, str) and url.startswith("data:text/html"), f"URL contract failed: {url!r}"
        print("AUTORADAR browser smoke test: OK")

if __name__ == "__main__":
    asyncio.run(main())
