"""FDA FAERS adverse event reporting fetcher."""
import requests
from backend.config import FDA_BASE_URL, FDA_API_KEY
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_fda_adverse_events(drug_name: str, limit: int = 5) -> list[dict]:
    """Fetch adverse event reports from FDA FAERS."""
    try:
        params = {
            "search": f'patient.drug.medicinalproduct:"{drug_name}"',
            "limit": limit,
        }
        if FDA_API_KEY:
            params["api_key"] = FDA_API_KEY

        resp = requests.get(FDA_BASE_URL, params=params, timeout=15)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()

        results = []
        for r in data.get("results", []):
            reactions = [
                rx.get("reactionmeddrapt", "")
                for rx in r.get("patient", {}).get("reaction", [])
            ]
            serious = r.get("serious", "")
            outcome = r.get("patient", {}).get("patientdeath", "0")
            results.append({
                "source": "FDA FAERS",
                "drug": drug_name,
                "reactions": reactions,
                "serious": serious == "1",
                "fatal": outcome == "1",
                "text": (
                    f"FDA FAERS adverse event for {drug_name}: "
                    f"reactions reported: {', '.join(reactions[:5])}. "
                    f"Serious: {'Yes' if serious == '1' else 'No'}."
                )
            })
        return results
    except Exception as e:
        print(f"[FDA FAERS] Error for {drug_name}: {e}")
        return []


def get_top_reactions(drug_name: str) -> dict:
    """Get aggregated top reaction counts for a drug."""
    try:
        params = {
            "search": f'patient.drug.medicinalproduct:"{drug_name}"',
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": 10,
        }
        if FDA_API_KEY:
            params["api_key"] = FDA_API_KEY
        resp = requests.get(FDA_BASE_URL, params=params, timeout=10)
        if resp.status_code != 200:
            return {}
        results = resp.json().get("results", [])
        return {r["term"]: r["count"] for r in results}
    except Exception as e:
        print(f"[FDA FAERS] Top reactions error: {e}")
        return {}
