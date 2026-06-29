"""Fetch US News 2026 ranks from public college profile pages."""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
USNEWS_COLLEGE_RE = re.compile(
    r"https://www\.usnews\.com/best-colleges/([a-z0-9-]+-\d+)(?:/overall-rankings)?"
)
RANK_TYPES = {
    "national-universities": "national_university",
    "regional-universities-midwest": "regional_universities_midwest",
    "undergraduate-business-programs": "undergrad_business",
}
STOP_WORDS = frozenset({"university", "of", "the", "college", "school", "business", "and"})


def _get(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        return None
    return None


def _search_name(school_name: str) -> str:
    name = school_name.split(" - ")[0].strip()
    name = re.sub(r"\s*\([^)]*\)", "", name).strip()
    return name


def _name_tokens(name: str) -> List[str]:
    cleaned = re.sub(r"[^a-z0-9\s-]", " ", name.lower())
    tokens = [t for t in cleaned.replace("-", " ").split() if t and t not in STOP_WORDS]
    return tokens


def _score_slug(slug: str, tokens: List[str]) -> int:
    slug_text = slug.lower().replace("-", " ")
    score = 0
    for token in tokens:
        if token in slug_text:
            score += 2
    if "uw-" in slug and "wisconsin" in " ".join(tokens):
        score += 1
    return score


def _pick_best_url(urls: List[str], school_name: str) -> Optional[str]:
    tokens = _name_tokens(_search_name(school_name))
    if not tokens:
        return None
    best_url = None
    best_score = 0
    for url in urls:
        match = USNEWS_COLLEGE_RE.search(url)
        if not match:
            continue
        score = _score_slug(match.group(1), tokens)
        if score > best_score:
            best_score = score
            best_url = url
    if best_score < 2:
        return None
    if best_url and not best_url.endswith("/overall-rankings"):
        return f"{best_url.rstrip('/')}/overall-rankings"
    return best_url


def _ddg_usnews_urls(query: str) -> List[str]:
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=25,
        )
    except requests.RequestException:
        return []
    if resp.status_code == 202:
        time.sleep(2.0)
        try:
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers={"User-Agent": USER_AGENT},
                timeout=25,
            )
        except requests.RequestException:
            return []
    if resp.status_code != 200:
        return []

    urls: List[str] = []
    soup = BeautifulSoup(resp.text, "html.parser")
    for anchor in soup.select("a.result__a"):
        href = anchor.get("href") or ""
        if "uddg=" in href:
            href = unquote(href.split("uddg=")[-1])
        if "usnews.com/best-colleges/" in href:
            urls.append(href.split("&")[0])

    for match in USNEWS_COLLEGE_RE.finditer(resp.text):
        urls.append(match.group(0))
    return list(dict.fromkeys(urls))


def _find_rankings_url(school_name: str) -> Optional[str]:
    query_name = _search_name(school_name)
    queries = [
        f"{query_name} site:usnews.com/best-colleges",
        f"usnews best colleges {query_name}",
    ]
    for query in queries:
        urls = _ddg_usnews_urls(query)
        picked = _pick_best_url(urls, school_name)
        if picked:
            return picked
        time.sleep(1.0)
    return None


def parse_rankings_html(html: str) -> Dict[str, Any]:
    rankings: Dict[str, Any] = {}
    for us_type, field in RANK_TYPES.items():
        match = re.search(rf'"type":"{us_type}".*?"sortRank":(\d+)', html)
        if match:
            rankings[field] = int(match.group(1))
    if not rankings:
        nat = re.search(r"ranked #(\d+) out of \d+ National Universities", html, re.I)
        if nat:
            rankings["national_university"] = int(nat.group(1))
        reg = re.search(r"ranked #(\d+) out of \d+ Regional Universities Midwest", html, re.I)
        if reg:
            rankings["regional_universities_midwest"] = int(reg.group(1))
    return rankings


def fetch_us_news_rankings(school_name: str, *, pause_sec: float = 1.0) -> Dict[str, Any]:
    """Return ranking fields + source URL, or empty dict if not found."""
    time.sleep(pause_sec)
    url = _find_rankings_url(school_name)
    if not url:
        return {}
    html = _get(url)
    if not html:
        return {}
    ranks = parse_rankings_html(html)
    if not ranks:
        return {}
    ranks["source_url"] = url
    return ranks
