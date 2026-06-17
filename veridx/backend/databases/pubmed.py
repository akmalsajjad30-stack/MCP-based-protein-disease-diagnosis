"""PubMed fetcher via NCBI Entrez."""
import requests
from backend.config import NCBI_BASE_URL, NCBI_API_KEY
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_pubmed(query: str, max_results: int = 8) -> list[dict]:
    """Search PubMed and return abstracts with metadata."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "usehistory": "y",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    search_resp = requests.get(f"{NCBI_BASE_URL}esearch.fcgi", params=params, timeout=15)
    search_resp.raise_for_status()
    search_data = search_resp.json()
    ids = search_data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    fetch_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    if NCBI_API_KEY:
        fetch_params["api_key"] = NCBI_API_KEY

    fetch_resp = requests.get(f"{NCBI_BASE_URL}efetch.fcgi", params=fetch_params, timeout=20)
    fetch_resp.raise_for_status()

    results = []
    for pmid in ids:
        results.append({
            "source": "PubMed",
            "pmid": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "text": fetch_resp.text,  # full XML; parsed downstream
        })
    return results


def fetch_pubmed_text(query: str, max_results: int = 8) -> list[str]:
    """Return plain text abstracts for embedding."""
    params = {
        "db": "pubmed", "term": query,
        "retmax": max_results, "retmode": "json",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    try:
        search = requests.get(f"{NCBI_BASE_URL}esearch.fcgi", params=params, timeout=10).json()
        ids = search.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        fetch = requests.get(f"{NCBI_BASE_URL}efetch.fcgi", params={
            "db": "pubmed", "id": ",".join(ids),
            "rettype": "abstract", "retmode": "text",
            **({"api_key": NCBI_API_KEY} if NCBI_API_KEY else {})
        }, timeout=20)
        return [s.strip() for s in fetch.text.split("\n\n") if s.strip()]
    except Exception as e:
        print(f"[PubMed] Error: {e}")
        return []
