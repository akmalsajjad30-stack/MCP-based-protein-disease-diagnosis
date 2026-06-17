"""ClinVar variant-disease association fetcher via NCBI Entrez."""
import requests
from backend.config import NCBI_BASE_URL, NCBI_API_KEY
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_clinvar(query: str, max_results: int = 5) -> list[dict]:
    """Fetch ClinVar variant-disease associations."""
    try:
        params = {
            "db": "clinvar", "term": query,
            "retmax": max_results, "retmode": "json",
        }
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY

        search = requests.get(f"{NCBI_BASE_URL}esearch.fcgi", params=params, timeout=10).json()
        ids = search.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        summary = requests.get(f"{NCBI_BASE_URL}esummary.fcgi", params={
            "db": "clinvar", "id": ",".join(ids), "retmode": "json",
            **({"api_key": NCBI_API_KEY} if NCBI_API_KEY else {})
        }, timeout=15).json()

        results = []
        for uid, data in summary.get("result", {}).items():
            if uid == "uids":
                continue
            title = data.get("title", "")
            clinical_sig = data.get("clinical_significance", {}).get("description", "")
            condition = data.get("trait_set", [{}])[0].get("trait_name", "") if data.get("trait_set") else ""
            results.append({
                "source": "ClinVar",
                "id": uid,
                "title": title,
                "clinical_significance": clinical_sig,
                "condition": condition,
                "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/",
                "text": f"ClinVar variant: {title}. Clinical significance: {clinical_sig}. Associated condition: {condition}."
            })
        return results
    except Exception as e:
        print(f"[ClinVar] Error: {e}")
        return []
