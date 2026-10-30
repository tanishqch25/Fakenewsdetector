"""Harvest candidate fact-check article URLs for the claims dashboard.

Read-only network research tool. It fetches public RSS feeds and public
listing pages of fact-checking organisations and writes a candidate table
(source, url, title, publish date, short snippet) to this directory.

It does not download datasets, does not touch the model, the backend or the
website, and it never writes claim records by itself: snippets are truncated
triage hints only. Final dashboard entries are written by hand from the full
article text cached by fetch_articles.py.

Usage:
    python Frontend/research/harvest_candidates.py
"""

import re
import time
import html as htmllib
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path(__file__).resolve().parent / "candidates.tsv"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DELAY = 1.0
TIMEOUT = 30

RSS_SOURCES = [
    # (source label, feed url template with {page}, pages to fetch)
    ("Alt News", "https://www.altnews.in/feed/?paged={page}", 14),
    ("Factly", "https://factly.in/category/fact-check/feed/?paged={page}", 14),
    ("Newschecker", "https://www.newschecker.in/feed/?paged={page}", 12),
    ("Vishvas News", "https://www.vishvasnews.com/english/feed/?paged={page}", 12),
    ("FactCheck.org", "https://www.factcheck.org/feed/?paged={page}", 4),
]

HTML_SOURCES = [
    # (source label, [page urls], regex producing absolute or relative hrefs, base)
    (
        "BOOM",
        [f"https://www.boomlive.in/fact-check{'' if i == 1 else '/' + str(i)}" for i in range(1, 7)],
        r'href="(/fact-check/[a-z0-9-]{15,120})"',
        "https://www.boomlive.in",
    ),
    (
        "The Quint WebQoof",
        [f"https://www.thequint.com/news/webqoof?page={i}" for i in range(0, 6)],
        r'href="(https://www\.thequint\.com/news/webqoof/[a-z0-9-]{15,120})"',
        "",
    ),
    (
        "India Today Fact Check",
        [f"https://www.indiatoday.in/fact-check?page={i}" for i in range(0, 6)],
        r'"(/fact-check/story/[a-z0-9-]{15,140})"',
        "https://www.indiatoday.in",
    ),
    (
        "Alt News (listing)",
        [f"https://www.altnews.in/page/{i}/" for i in range(2, 8)],
        r'href="(https://www\.altnews\.in/[a-z0-9-]{15,120}/)"',
        "",
    ),
]

TAG_RE = re.compile(r"<[^>]+>")
SKIP_SLUGS = {"business", "news", "videos", "photos", "opinion", "sports", "entertainment"}


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - research tool, log and continue
        return getattr(exc, "code", 0), f"__error__ {type(exc).__name__}: {exc}"


def clean(text):
    text = htmllib.unescape(TAG_RE.sub(" ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def harvest_rss(label, template, pages, seen, rows):
    for page in range(1, pages + 1):
        status, body = fetch(template.format(page=page))
        if status != 200 or body.startswith("__error__"):
            print(f"  [{label}] page {page}: http={status} -> stop")
            break
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            print(f"  [{label}] page {page}: XML parse error {exc} -> stop")
            break
        items = root.findall("./channel/item")
        if not items:
            print(f"  [{label}] page {page}: 0 items -> stop")
            break
        new = 0
        for item in items:
            link = clean(item.findtext("link"))
            if not link or link in seen:
                continue
            seen.add(link)
            rows.append(
                {
                    "source": label,
                    "url": link,
                    "title": clean(item.findtext("title")),
                    "pubdate": clean(item.findtext("pubDate")),
                    "snippet": clean(item.findtext("description"))[:180],
                    "via": "rss",
                }
            )
            new += 1
        print(f"  [{label}] page {page}: {len(items)} items, {new} new")
        if new == 0:
            break
        time.sleep(DELAY)


def harvest_html(label, urls, pattern, base, seen, rows):
    compiled = re.compile(pattern)
    for url in urls:
        status, body = fetch(url)
        if status != 200 or body.startswith("__error__"):
            print(f"  [{label}] {url}: http={status}")
            time.sleep(DELAY)
            continue
        matches = compiled.findall(body)
        new = 0
        for href in matches:
            slug = href.rstrip("/").rsplit("/", 1)[-1]
            if slug in SKIP_SLUGS:
                continue
            full = href if href.startswith("http") else base + href
            if full in seen:
                continue
            seen.add(full)
            rows.append(
                {"source": label, "url": full, "title": "", "pubdate": "", "snippet": "", "via": "listing"}
            )
            new += 1
        print(f"  [{label}] {url}: {len(matches)} links, {new} new")
        time.sleep(DELAY)


def main():
    seen, rows = set(), []
    print("== RSS feeds ==")
    for label, template, pages in RSS_SOURCES:
        harvest_rss(label, template, pages, seen, rows)
    print("== HTML listings ==")
    for label, urls, pattern, base in HTML_SOURCES:
        harvest_html(label, urls, pattern, base, seen, rows)

    with OUT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("source\turl\ttitle\tpubdate\tsnippet\tvia\n")
        for row in rows:
            handle.write(
                "\t".join(
                    row[key].replace("\t", " ").replace("\n", " ")
                    for key in ("source", "url", "title", "pubdate", "snippet", "via")
                )
                + "\n"
            )

    print(f"\nwrote {len(rows)} unique candidates -> {OUT}")
    tally = {}
    for row in rows:
        tally[row["source"]] = tally.get(row["source"], 0) + 1
    for label, count in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"  {count:4d}  {label}")


if __name__ == "__main__":
    main()
