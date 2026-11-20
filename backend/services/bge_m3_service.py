import os
import re
import math
import logging
from collections import Counter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
EMBEDDING_URL_SINGLE = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={GEMINI_API_KEY}"
EMBEDDING_URL_BATCH = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={GEMINI_API_KEY}"

session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
)
session.mount("https://", adapter)


def compute_lexical_weights(text: str) -> dict[int, float]:
    """Pure Python BM25-style lexical weighting: 0 MB memory footprint."""
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    weights = {}
    for tok, cnt in counts.items():
        tok_id = abs(hash(tok)) % 250000
        tf = cnt / total
        weights[tok_id] = round(tf * (1.0 + math.log(1.0 + cnt)), 4)
    return weights


def encode_text(text: str) -> dict:
    """Computes dense (Gemini API) and sparse lexical vector for a single string."""
    lexical = compute_lexical_weights(text)
    try:
        payload = {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": text[:4000]}]},
        }
        res = session.post(EMBEDDING_URL_SINGLE, json=payload, timeout=12)
        if res.status_code == 200:
            dense = res.json().get("embedding", {}).get("values", [])
            return {"dense": dense, "sparse": lexical}
        else:
            logger.error(f"Gemini embedding error: {res.status_code} - {res.text}")
    except Exception as e:
        logger.error(f"Exception during Gemini embedding: {e}")

    # Fallback zero vector if API call fails
    return {"dense": [0.0] * 3072, "sparse": lexical}


def encode_texts(texts: list[str]) -> dict:
    """Batch computes dense (Gemini API) and sparse lexical vectors."""
    if not texts:
        return {"dense": [], "sparse": []}

    sparse_list = [compute_lexical_weights(t) for t in texts]
    dense_list = []

    # Batch in groups of 25 to respect Gemini batch size limits
    batch_size = 25
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            payload = {
                "requests": [
                    {
                        "model": "models/gemini-embedding-001",
                        "content": {"parts": [{"text": t[:4000]}]},
                    }
                    for t in batch
                ]
            }
            res = session.post(EMBEDDING_URL_BATCH, json=payload, timeout=20)
            if res.status_code == 200:
                vectors = [item["values"] for item in res.json().get("embeddings", [])]
                dense_list.extend(vectors)
            else:
                logger.error(f"Batch embed error: {res.status_code} - {res.text}")
                dense_list.extend([[0.0] * 3072 for _ in batch])
        except Exception as e:
            logger.error(f"Batch embed exception: {e}")
            dense_list.extend([[0.0] * 3072 for _ in batch])

    return {"dense": dense_list, "sparse": sparse_list}
