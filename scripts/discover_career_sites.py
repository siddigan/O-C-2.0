"""Best-effort discovery script for career URLs.
Uses DuckDuckGo HTML search results to fill missing company career URLs.
"""

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.db.session import SessionLocal
from app.models.models import Company

PREFERRED_HINTS = ["careers", "jobs", "workdayjobs", "greenhouse", "lever"]


def looks_like_career(url: str) -> bool:
    lower = url.lower()
    return any(h in lower for h in PREFERRED_HINTS)


def clean_redirect(url: str) -> str:
    if "uddg=" in url:
        return httpx.URL(url).params.get("uddg", url)
    return url


def discover(company: str) -> str | None:
    query = f"{company} official careers jobs"
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        res = client.get("https://duckduckgo.com/html/", params={"q": query})
        res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    for a in soup.select("a.result__a"):
        href = clean_redirect(a.get("href", ""))
        if not href:
            continue
        parsed = urlparse(href)
        if parsed.scheme in {"http", "https"} and looks_like_career(href):
            return href
    # Fallback: first result if none contains strong hints.
    first = soup.select_one("a.result__a")
    if first and first.get("href"):
        href = clean_redirect(first["href"])
        if re.match(r"^https?://", href):
            return href
    return None


def main() -> None:
    db = SessionLocal()
    companies = db.query(Company).filter(Company.career_url.is_(None)).all()
    for c in companies:
        url = discover(c.name)
        if url:
            c.career_url = url
            print(f"{c.name}: {url}")
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
