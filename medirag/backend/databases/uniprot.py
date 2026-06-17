"""UniProt protein database fetcher."""
import requests
from backend.config import UNIPROT_BASE_URL
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_uniprot(query: str, size: int = 5) -> list[dict]:
    """Fetch protein entries from UniProt."""
    try:
        resp = requests.get(UNIPROT_BASE_URL, params={
            "query": query,
            "format": "json",
            "size": size,
            "fields": "accession,gene_names,protein_name,organism_name,cc_disease,cc_function,go"
        }, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        parsed = []
        for r in results:
            accession = r.get("primaryAccession", "")
            gene = r.get("genes", [{}])[0].get("geneName", {}).get("value", "") if r.get("genes") else ""
            protein_name = r.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "")
            diseases = [
                d.get("disease", {}).get("diseaseId", "")
                for d in r.get("comments", [])
                if d.get("commentType") == "DISEASE"
            ]
            function_text = " ".join([
                c.get("texts", [{}])[0].get("value", "")
                for c in r.get("comments", [])
                if c.get("commentType") == "FUNCTION"
            ])
            parsed.append({
                "source": "UniProt",
                "accession": accession,
                "gene": gene,
                "protein": protein_name,
                "diseases": diseases,
                "function": function_text,
                "url": f"https://www.uniprot.org/uniprotkb/{accession}",
                "text": f"Gene: {gene}. Protein: {protein_name}. Function: {function_text}. Diseases: {', '.join(diseases)}."
            })
        return parsed
    except Exception as e:
        print(f"[UniProt] Error: {e}")
        return []
