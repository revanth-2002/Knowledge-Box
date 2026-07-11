"""Server-side URL fetching and main-content extraction.

Uses readability-lxml to strip navigation/ads/boilerplate down to the
article body, falling back to a plain BeautifulSoup text dump if
readability can't parse the page.
"""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from readability import Document

from app.config import get_settings
from app.core.errors import FetchError

settings = get_settings()

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KnowledgeInboxBot/1.0; +https://example.com/bot)"
}


async def fetch_url_content(url: str) -> tuple[str, str]:
    """Fetch a URL and return (title, extracted_text).

    Raises FetchError on network failure, non-2xx status, or unparsable content.
    """
    if not url.startswith(("http://", "https://")):
        raise FetchError("URL must start with http:// or https://", detail=url)

    try:
        async with httpx.AsyncClient(
            timeout=settings.fetch_timeout_seconds, follow_redirects=True, headers=_HEADERS
        ) as client:
            response = await client.get(url)
    except httpx.TimeoutException as exc:
        raise FetchError(f"Timed out fetching URL after {settings.fetch_timeout_seconds}s", detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise FetchError("Could not reach the given URL", detail=str(exc)) from exc

    if response.status_code >= 400:
        raise FetchError(
            f"URL returned HTTP {response.status_code}", detail=str(response.status_code)
        )

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise FetchError(f"Unsupported content type for extraction: {content_type or 'unknown'}")

    html = response.text[: settings.max_fetch_bytes]

    try:
        doc = Document(html)
        title = doc.short_title() or url
        summary_html = doc.summary()
        text = BeautifulSoup(summary_html, "lxml").get_text(separator="\n", strip=True)
    except Exception:
        text = ""
        title = url

    if not text or len(text) < 50:
        # Fallback: raw text dump if readability produced too little
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        title = (soup.title.string.strip() if soup.title and soup.title.string else url)

    if not text or len(text.strip()) < 20:
        raise FetchError("Could not extract readable content from this URL")

    return title.strip()[:500], text
