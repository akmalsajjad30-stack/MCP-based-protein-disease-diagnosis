"""OMIM + ClinicalTrials.gov fetchers."""
import requests
from backend.config import OMIM_API_KEY, CLINTRIALS_BASE_URL
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_omim(query: str, limit: int = 5) -> list[dict]:
    """Fetch OMIM genetic disease entries. Requires OMIM API key."""
    if not OMIM_API_KEY:
        return []
    try:
        resp = requests.get("https://api.omim.org/api/entry/search", params={
            "search": query,
            "include": "text:description",
            "limit": limit,
            "apiKey": OMIM_API_KEY,
            "format": "json",
        }, timeout=15)
        resp.raise_for_status()
        entries = resp.json().get("omim", {}).get("searchResponse", {}).get("entryList", [])
        results = []
        for e in entries:
            entry = e.get("entry", {})
            mim_number = entry.get("mimNumber", "")
            titles = entry.get("titles", {})
            preferred_title = titles.get("preferredTitle", "")
            results.append({
                "source": "OMIM",
                "mim_number": mim_number,
                "title": preferred_title,
                "url": f"https://omim.org/entry/{mim_number}",
                "text": f"OMIM #{mim_number}: {preferred_title}."
            })
        return results
    except Exception as e:
        print(f"[OMIM] Error: {e}")
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_clinical_trials(condition: str, max_results: int = 5) -> list[dict]:
    """Fetch active clinical trials from ClinicalTrials.gov."""
    try:
        resp = requests.get("https://clinicaltrials.gov/api/v2/studies", params={
            "query.cond": condition,
            "filter.overallStatus": "RECRUITING",
            "pageSize": max_results,
            "format": "json",
        }, timeout=15)
        resp.raise_for_status()
        studies = resp.json().get("studies", [])
        results = []
        for s in studies:
            protocol = s.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            desc_module = protocol.get("descriptionModule", {})
            nct_id = id_module.get("nctId", "")
            title = id_module.get("briefTitle", "")
            status = status_module.get("overallStatus", "")
            summary = desc_module.get("briefSummary", "")[:300]
            results.append({
                "source": "ClinicalTrials.gov",
                "nct_id": nct_id,
                "title": title,
                "status": status,
                "url": f"https://clinicaltrials.gov/study/{nct_id}",
                "text": f"Trial {nct_id}: {title}. Status: {status}. {summary}"
            })
        return results
    except Exception as e:
        print(f"[ClinicalTrials] Error: {e}")
        return []
