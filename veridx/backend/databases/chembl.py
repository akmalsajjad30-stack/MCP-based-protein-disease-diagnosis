"""ChEMBL drug-target interaction fetcher."""
import requests
from backend.config import CHEMBL_BASE_URL
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_drug_info(drug_name: str) -> list[dict]:
    """Search ChEMBL for drug information and targets."""
    try:
        resp = requests.get(f"{CHEMBL_BASE_URL}/molecule.json", params={
            "pref_name__icontains": drug_name,
            "limit": 3,
            "format": "json"
        }, timeout=15)
        resp.raise_for_status()
        molecules = resp.json().get("molecules", [])

        results = []
        for mol in molecules:
            chembl_id = mol.get("molecule_chembl_id", "")
            name = mol.get("pref_name", drug_name)
            mw = mol.get("molecule_properties", {}).get("mw_freebase", "")
            indication = mol.get("indication_class", "")
            results.append({
                "source": "ChEMBL",
                "chembl_id": chembl_id,
                "name": name,
                "molecular_weight": mw,
                "indication": indication,
                "url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/",
                "text": f"Drug {name} (ChEMBL: {chembl_id}): molecular weight {mw}. Indication class: {indication}."
            })
        return results
    except Exception as e:
        print(f"[ChEMBL] Error for {drug_name}: {e}")
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_drug_mechanisms(chembl_id: str) -> list[dict]:
    """Fetch mechanism of action for a ChEMBL compound."""
    try:
        resp = requests.get(f"{CHEMBL_BASE_URL}/mechanism.json", params={
            "molecule_chembl_id": chembl_id,
            "limit": 5,
            "format": "json"
        }, timeout=10)
        resp.raise_for_status()
        mechs = resp.json().get("mechanisms", [])
        return [{
            "source": "ChEMBL",
            "chembl_id": chembl_id,
            "mechanism": m.get("mechanism_of_action", ""),
            "target": m.get("target_chembl_id", ""),
            "action_type": m.get("action_type", ""),
            "text": f"Mechanism: {m.get('mechanism_of_action', '')}. Action type: {m.get('action_type', '')}."
        } for m in mechs]
    except Exception as e:
        print(f"[ChEMBL] Mechanism error for {chembl_id}: {e}")
        return []
