"""
Graph builder — populates Neo4j with entities extracted from biomedical DB results.
Uses spaCy for basic NER if SciSpacy is not available.
"""
import re
import logging
from backend.graph_rag.neo4j_client import upsert_node, upsert_relationship

logger = logging.getLogger(__name__)

# Simple regex-based medical term patterns (fallback if SciSpacy unavailable)
CONDITION_PATTERNS = re.compile(
    r'\b(diabetes|hypertension|obesity|cancer|carcinoma|syndrome|disease|disorder|'
    r'failure|infarction|stroke|asthma|pneumonia|depression|anxiety|arthritis|'
    r'hypothyroidism|hyperthyroidism|anemia|leukemia|lymphoma)\b',
    re.IGNORECASE
)

DRUG_PATTERNS = re.compile(
    r'\b(metformin|aspirin|ibuprofen|lisinopril|atorvastatin|omeprazole|'
    r'losartan|amlodipine|metoprolol|levothyroxine|insulin|warfarin|'
    r'prednisone|amoxicillin|albuterol)\b',
    re.IGNORECASE
)


def build_symptom_nodes(symptoms: list[str]):
    """Create Symptom nodes in Neo4j."""
    for symptom in symptoms:
        upsert_node("Symptom", "name", symptom.lower().strip(), {
            "name": symptom.lower().strip(),
            "display_name": symptom.strip()
        })
    logger.info(f"Upserted {len(symptoms)} symptom nodes.")


def build_from_pubmed(results: list[dict], patient_conditions: list[str]):
    """Extract and link entities from PubMed abstracts."""
    for result in results:
        text = result.get("text", "")
        conditions_found = CONDITION_PATTERNS.findall(text)
        for cond in set(conditions_found):
            upsert_node("Condition", "name", cond.lower(), {
                "name": cond.lower(),
                "display_name": cond,
                "source": "PubMed",
                "pmid": result.get("pmid", "")
            })
        # Link patient symptoms to found conditions
        for symptom in patient_conditions:
            for cond in set(conditions_found):
                try:
                    upsert_relationship(
                        "Symptom", "name", symptom.lower(),
                        "Condition", "name", cond.lower(),
                        "INDICATES", {"confidence": 0.5, "source": "PubMed"}
                    )
                except Exception:
                    pass


def build_from_uniprot(results: list[dict]):
    """Build Gene and Protein nodes from UniProt results."""
    for r in results:
        gene = r.get("gene", "").strip()
        protein = r.get("protein", "").strip()
        accession = r.get("accession", "")

        if gene:
            upsert_node("Gene", "symbol", gene.upper(), {
                "symbol": gene.upper(),
                "function": r.get("function", "")[:500],
                "source": "UniProt"
            })
        if accession:
            upsert_node("Protein", "uniprot_id", accession, {
                "uniprot_id": accession,
                "name": protein,
                "source": "UniProt"
            })
        if gene and accession:
            try:
                upsert_relationship(
                    "Gene", "symbol", gene.upper(),
                    "Protein", "uniprot_id", accession,
                    "ENCODES"
                )
            except Exception:
                pass

        # Link to diseases
        for disease in r.get("diseases", []):
            if disease:
                upsert_node("Condition", "name", disease.lower(), {
                    "name": disease.lower(),
                    "display_name": disease,
                    "source": "UniProt"
                })
                if gene:
                    try:
                        upsert_relationship(
                            "Condition", "name", disease.lower(),
                            "Gene", "symbol", gene.upper(),
                            "ASSOCIATED_WITH", {"source": "UniProt"}
                        )
                    except Exception:
                        pass


def build_from_chembl(results: list[dict], patient_conditions: list[str]):
    """Build Drug nodes and TREATS relationships from ChEMBL."""
    for r in results:
        drug_name = r.get("name", "").lower().strip()
        if not drug_name:
            continue
        upsert_node("Drug", "name", drug_name, {
            "name": drug_name,
            "chembl_id": r.get("chembl_id", ""),
            "indication": r.get("indication", ""),
            "source": "ChEMBL"
        })
        indication = r.get("indication", "").lower()
        for cond in patient_conditions:
            if cond.lower() in indication or indication in cond.lower():
                try:
                    upsert_relationship(
                        "Drug", "name", drug_name,
                        "Condition", "name", cond.lower(),
                        "TREATS", {"source": "ChEMBL"}
                    )
                except Exception:
                    pass


def build_from_clinical_trials(results: list[dict]):
    """Build ClinicalTrial nodes."""
    for r in results:
        nct_id = r.get("nct_id", "")
        if not nct_id:
            continue
        upsert_node("ClinicalTrial", "nct_id", nct_id, {
            "nct_id": nct_id,
            "title": r.get("title", ""),
            "status": r.get("status", ""),
            "url": r.get("url", ""),
            "source": "ClinicalTrials.gov"
        })
