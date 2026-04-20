"""
Scraper service — the first real "worker" in the pipeline.

Three pure-ish functions:
  fetch_page   → download HTML from a URL (async, uses httpx)
  extract_text → strip tags and return human-readable text (sync, CPU-bound)
  detect_source → classify URL by ATS (sync, string matching)

Why httpx instead of requests?
  httpx is natively async, so it plays nicely with FastAPI's event loop.
  Using `requests` in an async route would block the entire server.

Why BeautifulSoup with lxml?
  lxml is the fastest HTML parser available in Python.  We strip <script>
  and <style> tags before extracting text — they add noise to the output
  and would confuse an LLM in Phase 2.
"""

import re

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger

log = get_logger(__name__)

FETCH_TIMEOUT = 15.0  # seconds

# Patterns for ATS detection — order matters, first match wins
_SOURCE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("greenhouse", re.compile(r"greenhouse\.io|boards\.greenhouse", re.IGNORECASE)),
    ("lever", re.compile(r"jobs\.lever\.co", re.IGNORECASE)),
]


async def fetch_page(url: str) -> str:
    """
    Download the HTML content of a URL.

    Raises httpx.TimeoutException on timeout and httpx.HTTPStatusError
    on non-2xx responses.  The caller (route) is responsible for
    translating these into user-facing error responses.
    """
    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "applybot/0.1 (job-scraper)"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        log.info("page_fetched", url=url, status=response.status_code, length=len(response.text))
        return response.text


def extract_text(html: str) -> str:
    """
    Strip HTML to plain readable text.

    Removes script/style elements first (they add noise), then pulls
    the text content with newline separators and whitespace cleanup.
    Returns an empty string if nothing is extractable.
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Collapse runs of blank lines into a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_source(url: str) -> str:
    """
    Classify a URL by applicant tracking system.

    Simple substring/regex matching — fast and deterministic.
    Returns "greenhouse", "lever", or "unknown".
    """
    for source_name, pattern in _SOURCE_PATTERNS:
        if pattern.search(url):
            return source_name
    return "unknown"
