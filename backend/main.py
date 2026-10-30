"""FastAPI backend for the Fake News Analyzer website.

Loads the existing scikit-learn pipeline from Frontend/ml/best_model.pkl
and exposes it over HTTP for the React frontend.

Labels: 0 = Potentially Fake, 1 = Potentially Real.
This is a screening classifier, not a fact-checking system.
"""

from pathlib import Path
from urllib.parse import urljoin, urlparse
import ipaddress
import socket

import joblib
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "best_model.pkl"

DISCLAIMER = (
    "This is a machine-learning screening result based on writing patterns "
    "learned from the training dataset. It is not fact verification and does "
    "not establish whether the story is true or false."
)

MAX_ARTICLE_CHARS = 20000
MIN_ARTICLE_CHARS = 100
MIN_INPUT_CHARS = 30

LABEL_VERDICTS = {0: "Potentially Fake", 1: "Potentially Real"}

app = FastAPI(title="Fake News Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_model = None


def get_model():
    global _model
    if _model is None:
        if not MODEL_PATH.is_file():
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Model file not found at {MODEL_PATH}. "
                    "Place best_model.pkl inside Frontend/ml/."
                ),
            )
        _model = joblib.load(MODEL_PATH)
    return _model


class AnalyzeRequest(BaseModel):
    text: str | None = None
    url: str | None = None


class AnalyzeResponse(BaseModel):
    label: int
    verdict: str
    disclaimer: str
    input_mode: str
    source_title: str | None = None
    source_hostname: str | None = None
    extracted_chars: int | None = None


def validate_public_url(url: str) -> None:
    """Allow HTTP(S) URLs whose resolved IP addresses are public."""

    parsed = urlparse(url.strip())

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid URL beginning with http:// or https://.",
        )

    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=422,
            detail="URLs containing embedded login credentials are not allowed.",
        )

    hostname = parsed.hostname

    if hostname.lower() == "localhost" or hostname.lower().endswith(".local"):
        raise HTTPException(
            status_code=422,
            detail="Local and private network URLs are not supported.",
        )

    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(
            status_code=422,
            detail="The website hostname could not be resolved.",
        )

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise HTTPException(
                status_code=422,
                detail="Private or non-public network addresses are not allowed.",
            )


def fetch_html(url: str) -> tuple[str, str]:
    """Fetch an article page following redirects safely. Returns (final_url, html)."""

    current_url = url.strip()
    response = None

    for _ in range(6):
        validate_public_url(current_url)

        try:
            response = requests.get(
                current_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    )
                },
                timeout=(5, 15),
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not access the website: {type(exc).__name__}. "
                "The site may be offline or may block automated access.",
            ) from exc

        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            response.close()

            if not location:
                raise HTTPException(
                    status_code=502,
                    detail="The website returned an invalid redirect.",
                )

            current_url = urljoin(current_url, location)
            continue

        break
    else:
        raise HTTPException(
            status_code=502, detail="Too many website redirects."
        )

    try:
        with response:
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"The website returned HTTP {response.status_code}.",
                )

            content_type = response.headers.get("Content-Type", "").lower()

            if not ("text/html" in content_type or "text/plain" in content_type):
                raise HTTPException(
                    status_code=502,
                    detail="This URL does not appear to contain an HTML or plain-text article.",
                )

            chunks = []
            total_bytes = 0
            max_bytes = 2_000_000

            for chunk in response.iter_content(chunk_size=16384):
                if not chunk:
                    continue
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=502,
                        detail="The webpage is too large to process safely.",
                    )
                chunks.append(chunk)

            raw_content = b"".join(chunks)
            html = raw_content.decode(response.encoding or "utf-8", errors="replace")
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not read the webpage: {type(exc).__name__}.",
        ) from exc

    return current_url, html


def extract_article(url: str) -> tuple[str, str, str]:
    """Return (title, article_text, hostname) for a public article URL."""

    final_url, html = fetch_html(url)

    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title:
        title = soup.title.get_text(" ", strip=True)

    for element in soup(
        ["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg"]
    ):
        element.decompose()

    container = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.body
        or soup
    )

    paragraphs = [
        element.get_text(" ", strip=True)
        for element in container.find_all(["p", "h1", "h2", "h3"])
    ]

    article_text = "\n\n".join(p for p in paragraphs if p)

    if len(article_text.strip()) < MIN_ARTICLE_CHARS:
        article_text = container.get_text(" ", strip=True)

    article_text = article_text.strip()[:MAX_ARTICLE_CHARS]

    if len(article_text) < MIN_ARTICLE_CHARS:
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not extract enough article text. The site may require "
                "JavaScript or block automated readers. Try pasting the "
                "article text in News Text mode instead."
            ),
        )

    hostname = urlparse(final_url).hostname or ""

    return title, article_text, hostname


def run_screening(article: str) -> tuple[int, str]:
    try:
        model = get_model()
        prediction = int(model.predict([article])[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Model analysis failed ({type(exc).__name__}).",
        ) from exc

    if prediction not in LABEL_VERDICTS:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected model label: {prediction}",
        )

    return prediction, LABEL_VERDICTS[prediction]


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": MODEL_PATH.is_file(),
        "labels": LABEL_VERDICTS,
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    has_text = bool(request.text and request.text.strip())
    has_url = bool(request.url and request.url.strip())

    if has_text == has_url:
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one of: article text or an article URL.",
        )

    if has_text:
        article = request.text.strip()

        if len(article) < MIN_INPUT_CHARS:
            raise HTTPException(
                status_code=422,
                detail=f"Please provide at least {MIN_INPUT_CHARS} characters of meaningful text.",
            )

        label, verdict = run_screening(article[:MAX_ARTICLE_CHARS])

        return AnalyzeResponse(
            label=label,
            verdict=verdict,
            disclaimer=DISCLAIMER,
            input_mode="text",
            extracted_chars=len(article),
        )

    title, article_text, hostname = extract_article(request.url)
    label, verdict = run_screening(article_text)

    return AnalyzeResponse(
        label=label,
        verdict=verdict,
        disclaimer=DISCLAIMER,
        input_mode="url",
        source_title=title or None,
        source_hostname=hostname or None,
        extracted_chars=len(article_text),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
