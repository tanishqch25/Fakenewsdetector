
from pathlib import Path
from urllib.parse import urlparse
import ipaddress
import socket

import joblib
import requests
import streamlit as st
from bs4 import BeautifulSoup


# ---------------- CONFIGURATION ----------------

MODEL_PATH = Path(__file__).parent / "ml" / "best_model.pkl"

st.set_page_config(
    page_title="AI Fake News Detector",
    page_icon="🔎",
    layout="wide",
)


# ---------------- STYLING ----------------

st.markdown(
    """
    <style>
    
.stApp {
    background-color: #f4f7fb;
    color: #24364b;
}

.main-title {
    font-size: 2.35rem;
    font-weight: 750;
    color: #17365d;
    margin-bottom: 0.2rem;
}

.subtitle {
    color: #52657a;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}

.panel {
    background: #ffffff;
    color: #24364b;
    padding: 1.4rem;
    border-radius: 14px;
    border: 1px solid #dce5f0;
    margin-bottom: 1rem;
}

.section-kicker {
    color: #3769a5;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.08em;
}

.result-title {
    color: #17365d;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 1rem;
}

/* Fix headings, labels and helper text */
.stApp h1,
.stApp h2,
.stApp h3,
.stApp label,
.stApp .stMarkdown p,
.stApp .stCaption,
.stApp [data-testid="stWidgetLabel"] {
    color: #24364b !important;
}

/* Make radio labels readable */
.stApp [data-testid="stRadio"] label,
.stApp [data-testid="stRadio"] p {
    color: #24364b !important;
}

/* Improve text area readability */
.stApp textarea {
    color: #24364b !important;
    background-color: #ffffff !important;
    caret-color: #24364b !important;
}

/* Improve URL input readability */
.stApp input {
    color: #24364b !important;
    background-color: #ffffff !important;
}

/* Placeholder text */
.stApp textarea::placeholder,
.stApp input::placeholder {
    color: #718096 !important;
    opacity: 1;
}

    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- LOAD MODEL ----------------

@st.cache_resource
def load_model():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Model file not found at {MODEL_PATH}. "
            "Place best_model.pkl inside Frontend/ML/."
        )

    return joblib.load(MODEL_PATH)


# ---------------- URL VALIDATION ----------------

def validate_public_url(url):
    """Allow HTTP(S) URLs whose resolved IP addresses are public."""

    parsed = urlparse(url.strip())

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(
            "Enter a valid URL beginning with http:// or https://."
        )

    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded login credentials are not allowed.")

    hostname = parsed.hostname

    if hostname.lower() == "localhost" or hostname.lower().endswith(".local"):
        raise ValueError("Local and private network URLs are not supported.")

    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise RuntimeError("The website hostname could not be resolved.")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise ValueError("Private or non-public network addresses are not allowed.")

    return parsed


# ---------------- EXTRACT ARTICLE ----------------

def extract_article(url):
    """
    Fetch a public article and extract readable text.
    Some websites may block requests or require JavaScript.
    """

    url = url.strip()

    if not url:
        raise ValueError("Enter an article URL before analyzing.")

    current_url = url
    response = None

    # Validate each destination, including redirect destinations.
    for _ in range(6):
        parsed = validate_public_url(current_url)

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
            raise RuntimeError(
                f"Could not access the website: {exc}"
            ) from exc

        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            response.close()

            if not location:
                raise RuntimeError("The website returned an invalid redirect.")

            from urllib.parse import urljoin
            current_url = urljoin(current_url, location)
            continue

        break
    else:
        raise RuntimeError("Too many website redirects.")

    try:
        with response:
            if response.status_code >= 400:
                raise RuntimeError(
                    f"The website returned HTTP {response.status_code}."
                )

            content_type = response.headers.get("Content-Type", "").lower()

            if not (
                "text/html" in content_type
                or "text/plain" in content_type
            ):
                raise RuntimeError(
                    "This URL does not appear to contain an HTML or plain-text article."
                )

            # Read a limited amount of content.
            chunks = []
            total_bytes = 0
            max_bytes = 2_000_000

            for chunk in response.iter_content(chunk_size=16384):
                if not chunk:
                    continue

                total_bytes += len(chunk)

                if total_bytes > max_bytes:
                    raise RuntimeError(
                        "The webpage is too large to process safely."
                    )

                chunks.append(chunk)

            raw_content = b"".join(chunks)
            html = raw_content.decode(
                response.encoding or "utf-8",
                errors="replace",
            )

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not read the webpage: {exc}"
        ) from exc

    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title:
        title = soup.title.get_text(" ", strip=True)

    for element in soup(
        ["script", "style", "nav", "footer", "header",
         "aside", "form", "noscript", "svg"]
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

    article_text = "\n\n".join(
        paragraph for paragraph in paragraphs if paragraph
    )

    if len(article_text.strip()) < 100:
        article_text = container.get_text(" ", strip=True)

    article_text = article_text.strip()[:20000]

    if len(article_text) < 100:
        raise RuntimeError(
            "Could not extract enough article text. "
            "Try pasting the article text in News Text mode."
        )

    final_hostname = urlparse(current_url).hostname or parsed.hostname

    return title, article_text, final_hostname


# ---------------- PAGE HEADER ----------------

st.markdown(
    '<div class="main-title">🔎 AI-Based Fake News Detector</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle">'
    "Screen news articles using a trained machine-learning model."
    "</div>",
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1], gap="large")


# ---------------- INPUT PANEL ----------------

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-kicker">01 · INPUT</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Analyze a news story")

    mode = st.radio(
        "Choose input method",
        ["News Text", "Article URL"],
        horizontal=True,
    )

    text = ""
    url = ""

    if mode == "News Text":
        text = st.text_area(
            "News headline and article",
            height=260,
            max_chars=20000,
            placeholder="Paste the headline and article text here...",
            help="Include the article body as well as the headline where possible.",
        )

        st.caption(
            "Up to 20,000 characters. Avoid submitting personal or sensitive information."
        )

    else:
        url = st.text_input(
            "Article URL",
            placeholder="https://example.com/news/article",
        )

        st.info(
            "The app will try to extract readable article text from this URL. "
            "Some websites block automated access or require JavaScript. "
            "If extraction fails, paste the article text instead.",
            icon="ℹ️",
        )

    analyze = st.button(
        "Analyze story",
        type="primary",
        use_container_width=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------- ANALYSIS ----------------

if "screening_result" not in st.session_state:
    st.session_state.screening_result = None

if analyze:
    st.session_state.screening_result = None

    if mode == "News Text":
        article = text.strip()

        if not article:
            st.session_state.screening_result = {
                "type": "error",
                "message": "Enter some news text before analyzing.",
            }

        elif len(article) < 30:
            st.session_state.screening_result = {
                "type": "error",
                "message": (
                    "Please provide at least 30 characters "
                    "of meaningful text."
                ),
            }

        else:
            try:
                with st.spinner("Running the trained model..."):
                    model = load_model()
                    prediction = int(model.predict([article])[0])

                if prediction == 0:
                    result_type = "fake"
                    result_message = "Potentially Fake"

                elif prediction == 1:
                    result_type = "real"
                    result_message = "Potentially Real"

                else:
                    raise ValueError(
                        f"Unexpected model label: {prediction}"
                    )

                st.session_state.screening_result = {
                    "type": result_type,
                    "message": result_message,
                    "description": (
                        "The model classified this text based on patterns "
                        "learned during training. This is not fact verification."
                    ),
                }

            except Exception as exc:
                st.session_state.screening_result = {
                    "type": "error",
                    "message": (
                        f"Model analysis failed "
                        f"({type(exc).__name__}): {exc}"
                    ),
                }

    else:
        if not url.strip():
            st.session_state.screening_result = {
                "type": "error",
                "message": "Enter an article URL before analyzing.",
            }

        else:
            try:
                with st.spinner("Fetching and analyzing the article..."):
                    title, article_text, hostname = extract_article(url)

                    model = load_model()
                    prediction = int(model.predict([article_text])[0])

                if prediction == 0:
                    result_type = "fake"
                    result_message = "Potentially Fake"

                elif prediction == 1:
                    result_type = "real"
                    result_message = "Potentially Real"

                else:
                    raise ValueError(
                        f"Unexpected model label: {prediction}"
                    )

                st.session_state.screening_result = {
                    "type": result_type,
                    "message": result_message,
                    "description": (
                        "The model classified the extracted article text "
                        "based on patterns learned during training. "
                        "This is not fact verification."
                    ),
                    "title": title,
                    "hostname": hostname,
                    "article_text": article_text,
                }

            except (ValueError, RuntimeError) as exc:
                st.session_state.screening_result = {
                    "type": "error",
                    "message": str(exc),
                }

            except Exception as exc:
                st.session_state.screening_result = {
                    "type": "error",
                    "message": (
                        f"URL analysis failed "
                        f"({type(exc).__name__}): {exc}"
                    ),
                }


# ---------------- RESULT PANEL ----------------

with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    st.markdown(
        '<div class="section-kicker">02 · SCREENING RESULT</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="result-title">Analysis</div>',
        unsafe_allow_html=True,
    )

    result = st.session_state.screening_result

    if result is None:
        st.info(
            "Your screening result will appear here after you analyze a story."
        )

    elif result["type"] == "error":
        st.error(result["message"])

    elif result["type"] == "fake":
        st.error(f"🚩 {result['message']}")
        st.write(result.get("description", ""))

    elif result["type"] == "real":
        st.success(f"📰 {result['message']}")
        st.write(result.get("description", ""))

    if result and result["type"] in ("fake", "real"):
        if result.get("hostname"):
            st.caption(f"Source website: {result['hostname']}")

        if result.get("title"):
            st.write(f"**Extracted title:** {result['title']}")

        if result.get("article_text"):
            with st.expander("View extracted article text"):
                st.write(result["article_text"])

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------- DISCLAIMER ----------------

st.caption(
    "Disclaimer: This tool is for educational screening purposes only. "
    "Its predictions are based on patterns learned from its training dataset "
    "and do not establish whether a claim is true or false. "
    "Always verify important news using reliable independent sources."
)
