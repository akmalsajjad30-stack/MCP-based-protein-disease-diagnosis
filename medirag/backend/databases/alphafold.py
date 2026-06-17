"""AlphaFold protein structure confidence fetcher."""
import requests
from backend.config import ALPHAFOLD_BASE_URL
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8))
def fetch_alphafold(uniprot_id: str) -> dict:
    """Fetch AlphaFold structure prediction confidence for a UniProt ID."""
    try:
        resp = requests.get(f"{ALPHAFOLD_BASE_URL}/{uniprot_id}", timeout=10)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return {}
        entry = data[0]
        return {
            "source": "AlphaFold",
            "uniprot_id": uniprot_id,
            "gene": entry.get("gene", ""),
            "plddt_mean": entry.get("globalMetricValue", None),
            "organism": entry.get("organismScientificName", ""),
            "pdb_url": entry.get("pdbUrl", ""),
            "text": (
                f"AlphaFold structure for {entry.get('gene', uniprot_id)}: "
                f"mean pLDDT confidence = {entry.get('globalMetricValue', 'N/A')}. "
                f"Organism: {entry.get('organismScientificName', '')}."
            )
        }
    except Exception as e:
        print(f"[AlphaFold] Error for {uniprot_id}: {e}")
        return {}


def fetch_alphafold_for_proteins(uniprot_ids: list[str]) -> list[dict]:
    """Batch fetch AlphaFold data for a list of UniProt IDs."""
    results = []
    for uid in uniprot_ids[:5]:  # limit to avoid rate issues
        data = fetch_alphafold(uid)
        if data:
            results.append(data)
    return results
