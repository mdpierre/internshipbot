"""
Markdown URL parser.

Extracts all unique HTTP(S) URLs from markdown content.
Handles both bare URLs and standard markdown link syntax [text](url).
"""

import re

# Markdown links: [text](url) — matched first to avoid double-counting
_MD_LINK = re.compile(r"\[.*?\]\((https?://[^)\s]+)\)")
# Bare URLs — negative lookbehind excludes URLs already captured inside '('
_BARE_URL = re.compile(r"(?<!\()(https?://[^\s\)\]]+)")


def extract_urls(content: str) -> list[str]:
    """
    Return a deduplicated list of URLs found in `content`, preserving order.

    Markdown links are matched before bare URLs so the same URL is not
    counted twice when both patterns match the same string.
    """
    seen: set[str] = set()
    urls: list[str] = []

    for url in _MD_LINK.findall(content):
        if url not in seen:
            seen.add(url)
            urls.append(url)

    for url in _BARE_URL.findall(content):
        url = url.rstrip(".,;:!?")  # strip trailing punctuation
        if url not in seen:
            seen.add(url)
            urls.append(url)

    return urls
