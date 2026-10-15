"""Fetch an article from a URL: body text and, where possible, its publication date.

URL input is the primary path for this system — a user pastes a link, not a paragraph — so
fusion has to turn that link into the text Module 1 needs and the date Module 2 needs.

Extraction is deliberately simple and dependency-light: Sri Lankan news sites are ordinary
server-rendered HTML, so paragraph text plus standard metadata tags gets us there without a
heavy readability library. Everything degrades rather than raising: a failed fetch returns a
reason, and fusion carries on with whatever the user supplied.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

URL_RE = re.compile(r"^\s*(https?://|www\.)\S+\s*$", re.I)
SINHALA_RE = re.compile(r"[඀-෿]")

# Meta tags that commonly carry a publication date, best first.
DATE_META = [
    ("property", "article:published_time"),
    ("property", "og:published_time"),
    ("itemprop", "datePublished"),
    ("name", "publish-date"),
    ("name", "pubdate"),
    ("name", "date"),
    ("name", "DC.date.issued"),
]

# Wrappers that usually hold the article body, tried in order before falling back to <p>.
BODY_SELECTORS = [
    "article", "div.news-content", "div.article-content", "div.entry-content",
    "div.post-content", "div.story-content", "div#article-body", "div.content-text",
]

STRIP_TAGS = ["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]


def looks_like_url(text: str) -> bool:
    """True if the whole string is just a URL — i.e. the user pasted a link into the text box."""
    return bool(text and URL_RE.match(text.strip()))


def normalise_url(url: str) -> str:
    url = url.strip()
    if url.lower().startswith("www."):
        url = "https://" + url
    return url


def _parse_date(raw: str) -> Optional[datetime]:
    raw = raw.strip()
    if not raw:
        return None
    cleaned = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y",
                "%B %d, %Y", "%d %B %Y", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # last resort: a bare ISO-ish date sitting inside a longer string
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        try:
            return datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def extract_published_date(soup: BeautifulSoup) -> tuple[Optional[datetime], Optional[str]]:
    for attr, value in DATE_META:
        tag = soup.find("meta", attrs={attr: value})
        if tag and tag.get("content"):
            dt = _parse_date(tag["content"])
            if dt:
                return dt, f"meta[{attr}={value}]"
    t = soup.find("time")
    if t:
        raw = t.get("datetime") or t.get_text()
        dt = _parse_date(raw or "")
        if dt:
            return dt, "<time>"
    return None, None


def extract_text(soup: BeautifulSoup) -> tuple[str, str]:
    for tag in soup(STRIP_TAGS):
        tag.decompose()

    for sel in BODY_SELECTORS:
        if "." in sel or "#" in sel:
            node = soup.select_one(sel)
        else:
            node = soup.find(sel)
        if node:
            paras = [p.get_text(" ", strip=True) for p in node.find_all("p")]
            text = " ".join(p for p in paras if len(p) > 20)
            if len(text) > 200:
                return text, sel

    paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    return " ".join(p for p in paras if len(p) > 20), "all <p> tags"


def extract_title(soup: BeautifulSoup) -> Optional[str]:
    for attr, value in (("property", "og:title"), ("name", "twitter:title")):
        tag = soup.find("meta", attrs={attr: value})
        if tag and tag.get("content"):
            return tag["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else None


async def fetch_article(url: str, timeout: float = 20.0) -> dict:
    """Fetch and parse an article.

    Always returns a dict with an `ok` flag; never raises. On failure `reason` explains why in
    terms a user can act on, because this runs in a live demo where a stack trace helps nobody.
    """
    url = normalise_url(url)
    out: dict = {"ok": False, "url": url, "text": None, "title": None,
                 "published_date": None, "reason": None,
                 "n_characters": 0, "sinhala_characters": 0,
                 "extraction": {}}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout,
                                     headers={"User-Agent": UA}) as client:
            r = await client.get(url)
            r.raise_for_status()
            html = r.text
    except httpx.HTTPStatusError as e:
        out["reason"] = f"the site returned HTTP {e.response.status_code}"
        return out
    except httpx.TimeoutException:
        out["reason"] = f"the site did not respond within {timeout:.0f}s"
        return out
    except Exception as e:
        out["reason"] = f"could not reach the site ({type(e).__name__})"
        return out

    soup = BeautifulSoup(html, "html.parser")
    text, how = extract_text(soup)
    title = extract_title(soup)
    dt, date_source = extract_published_date(soup)

    if len(text) < 100:
        out["reason"] = ("the page was fetched but no article text could be extracted "
                         "(it may be JavaScript-rendered, or a listing page rather than an article)")
        out["title"] = title
        return out

    out.update(ok=True, text=text, title=title,
               published_date=dt.isoformat() if dt else None,
               n_characters=len(text),
               sinhala_characters=len(SINHALA_RE.findall(text)),
               extraction={"body_from": how,
                           "date_from": date_source or "not found",
                           "final_url": url})
    return out
