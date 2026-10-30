"""Fetch candidate articles and cache their text for manual review.

Read-only network research tool. For every candidate URL harvested by
harvest_candidates.py it records:

  * the HTTP status actually returned,
  * the <title> and og:title served by the page,
  * the publication date from JSON-LD datePublished or article:published_time,
  * the readable article text (capped) used to write dashboard entries.

The cache is written OUTSIDE the repository (OS temp directory by default) so
that no copied article text is committed to the project. Only
fetch_log.tsv -- url, status, title, date, text length -- stays here as the
verification record.

Usage:
    python Frontend/research/fetch_articles.py [--limit N] [--source "Alt News"]
"""

import argparse
import json
import re
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import html as htmllib
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
CANDIDATES = HERE / "candidates.tsv"
FETCH_LOG = HERE / "fetch_log.tsv"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DELAY = 0.6
TIMEOUT = 30
MAX_TEXT = 5600
HEAD = 3000
TAIL = 2400


def default_cache_dir():
    return Path(tempfile.gettempdir()) / "fnd_research"


def read_candidates(source_filter):
    rows = []
    with CANDIDATES.open("r", encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < len(header):
                parts += [""] * (len(header) - len(parts))
            row = dict(zip(header, parts))
            if source_filter and source_filter.lower() not in row["source"].lower():
                continue
            rows.append(row)
    return rows


def fetch(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "en", "Accept": "text/html,application/xhtml+xml"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.geturl(), response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return getattr(exc, "code", 0), url, f"__error__ {type(exc).__name__}: {exc}"


def extract_published(body):
    for pattern in (
        r'"datePublished"\s*:\s*"([^"]{6,40})"',
        r'property="article:published_time"\s+content="([^"]{6,40})"',
        r'content="([^"]{6,40})"\s+property="article:published_time"',
        r'"publishDate"\s*:\s*"([^"]{6,40})"',
        r'"date"\s*:\s*"(\d{4}-\d{2}-\d{2}[^"]{0,30})"',
    ):
        match = re.search(pattern, body)
        if match:
            return match.group(1)
    return ""


def cap(text):
    if len(text) <= MAX_TEXT:
        return text
    # Fact-checks state the claim near the top and the verdict at the end, so
    # keep both ends instead of only the opening paragraphs.
    return text[:HEAD] + "\n...[MIDDLE TRUNCATED]...\n" + text[-TAIL:]


def extract_text(body):
    soup = BeautifulSoup(body, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg", "figure"]):
        element.decompose()

    # Pick the largest candidate rather than the first one: several of these
    # sites put a "related posts" card in the first <article> while the real
    # story sits in <main>.
    candidates = soup.find_all("article")
    candidates.append(soup.find("main"))
    candidates.append(soup.find(attrs={"role": "main"}))
    candidates = [c for c in candidates if c is not None]
    if candidates:
        container = max(candidates, key=lambda c: len(c.get_text(" ", strip=True)))
    else:
        container = soup.body or soup

    parts = [el.get_text(" ", strip=True) for el in container.find_all(["h1", "h2", "h3", "p", "li"])]
    text = "\n".join(p for p in parts if p and len(p) > 2)
    return cap(re.sub(r"\n{3,}", "\n\n", text))


def strip_tags(fragment):
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def fetch_wp_rest(url):
    """Some WordPress sites serve a JS shell to plain fetchers; their REST API
    still returns the rendered post content, date and title."""

    slug = url.rstrip("/").rsplit("/", 1)[-1]
    parsed = urlparse(url)
    api = (
        f"{parsed.scheme}://{parsed.netloc}/wp-json/wp/v2/posts"
        f"?slug={slug}&_fields=date,link,title,content"
    )
    status, _, body = fetch(api)
    if status != 200 or body.startswith("__error__"):
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list) or not payload:
        return None
    post = payload[0]
    return {
        "title": strip_tags(post.get("title", {}).get("rendered", "")),
        "published": (post.get("date") or "")[:10],
        "text": strip_tags(post.get("content", {}).get("rendered", "")),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="maximum candidates to fetch (0 = all)")
    parser.add_argument("--source", default="", help="only fetch rows whose source contains this string")
    parser.add_argument("--cache-dir", type=Path, default=default_cache_dir())
    parser.add_argument("--log", type=Path, default=FETCH_LOG, help="TSV fetch log to append to")
    args = parser.parse_args()

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = args.cache_dir / "articles.jsonl"
    fetch_log = args.log

    done = set()
    if cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    done.add(json.loads(line)["url"])
                except (json.JSONDecodeError, KeyError):
                    continue

    rows = [row for row in read_candidates(args.source) if row["url"] not in done]
    if args.limit:
        rows = rows[: args.limit]

    print(f"candidates={len(rows)} cache={cache_path} already_cached={len(done)}")

    log_rows = []
    log_needs_header = not (fetch_log.exists() and fetch_log.stat().st_size > 0)
    with cache_path.open("a", encoding="utf-8", newline="\n") as cache, fetch_log.open(
        "a", encoding="utf-8", newline="\n"
    ) as log:
        if log_needs_header:
            log.write("url\thttp\ttitle\tpublished\ttext_chars\tsource\tvia\n")
        for index, row in enumerate(rows, start=1):
            status, final_url, body = fetch(row["url"])
            record = {
                "url": row["url"],
                "final_url": final_url,
                "source": row["source"],
                "feed_title": row["title"],
                "feed_pubdate": row["pubdate"],
                "http": status,
                "title": "",
                "og_title": "",
                "published": "",
                "text_chars": 0,
                "text": "",
                "via": "",
            }
            if status == 200 and not body.startswith("__error__"):
                soup_title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
                record["title"] = htmllib.unescape(soup_title.group(1)).strip() if soup_title else ""
                og = re.search(r'property="og:title"\s+content="([^"]*)"', body)
                record["og_title"] = htmllib.unescape(og.group(1)).strip() if og else ""
                record["published"] = extract_published(body)
                record["text"] = extract_text(body)
                record["via"] = "html"

                if len(record["text"]) < 400:
                    rest = fetch_wp_rest(row["url"])
                    if rest and len(rest["text"]) > len(record["text"]):
                        record["text"] = cap(rest["text"])
                        record["title"] = rest["title"] or record["title"]
                        record["published"] = rest["published"] or record["published"]
                        record["via"] = "wp-rest"

                record["text_chars"] = len(record["text"])
            else:
                record["text"] = body[:200] if body.startswith("__error__") else ""

            cache.write(json.dumps(record, ensure_ascii=False) + "\n")
            cache.flush()
            log_rows.append(record)
            log.write(
                "\t".join(
                    [
                        record["url"],
                        str(record["http"]),
                        record["title"].replace("\t", " ")[:160],
                        record["published"][:10],
                        str(record["text_chars"]),
                        record["source"],
                        record.get("via", ""),
                    ]
                )
                + "\n"
            )
            log.flush()
            flag = "OK " if status == 200 and record["text_chars"] > 400 else "?? "
            print(
                f"{flag}{index:4d}/{len(rows)} http={status} chars={record['text_chars']:5d} "
                f"pub={record['published'][:10] or '-':10s} {row['url'][:95]}",
                flush=True,
            )
            time.sleep(DELAY)

    ok = sum(1 for r in log_rows if r["http"] == 200 and r["text_chars"] > 400)
    print(f"\nfetched={len(log_rows)} usable={ok} cache={cache_path} log={fetch_log}")


if __name__ == "__main__":
    main()
