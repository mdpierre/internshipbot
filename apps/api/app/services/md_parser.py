from __future__ import annotations

import re
from pathlib import Path


URL_RE = re.compile(r"https?://[^\s)>]+", re.I)


def extract_urls_from_markdown(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in URL_RE.findall(text):
        cleaned = match.rstrip(".,)")
        if cleaned in seen:
            continue
        seen.add(cleaned)
        urls.append(cleaned)
    return urls


def extract_urls_from_file(path: str | Path) -> list[str]:
    return extract_urls_from_markdown(Path(path).read_text())
