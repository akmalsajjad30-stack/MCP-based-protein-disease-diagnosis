"""
MCP Server — FastMCP with 10 medical tools, 6 resources, 4 prompt templates.
Mounted into FastAPI at /mcp via SSE transport.
"""
# pyrefly: ignore [missing-import]
from mcp.server.fastmcp import FastMCP
from backend.databases import pubmed, uniprot, clinvar, chembl, fda_faers, omim_clintrials
from backend.graph_rag.neo4j_client import get_subgraph_for_symptoms
from backend.graph_rag.community_detector import get_communities_from_neo4j
import json

mcp = FastMCP("VeriDX Clinical Intelligence Oracle")

# ═══════════════════════════════════════════════════════════════
# TOOLS
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
def search_pubmed(query: str, max_results: int = 8) -> str:
    """Search PubMed for peer-reviewed abstracts related to a medical query."""
    results = pubmed.fetch_pubmed_text(query, max_results)
    return json.dumps({"results": results, "count": len(results), "source": "PubMed/NCBI"})


@mcp.tool()
def lookup_protein(gene_or_keyword: str) -> str:
    """Look up protein function, disease associations, and structure from UniProt."""
    results = uniprot.fetch_uniprot(gene_or_keyword, 3)
    return json.dumps({"results": results, "source": "UniProt + AlphaFold"})


@mcp.tool()
def search_clinvar(query: str) -> str:
    """Search ClinVar for genetic variant-disease associations."""
    results = clinvar.fetch_clinvar(query, 5)
    return json.dumps({"results": results, "source": "ClinVar/NCBI"})


@mcp.tool()
def check_drug_interactions(drug_names: list[str]) -> str:
    """Check ChEMBL drug information and FDA FAERS adverse event signals for given drugs."""
    output = {"drugs": []}
    for drug in drug_names[:5]:
        info = chembl.fetch_drug_info(drug)
        adverse = fda_faers.get_top_reactions(drug)
        output["drugs"].append({
            "name": drug,
            "chembl_info": info,
            "top_adverse_reactions": adverse
        })
    return json.dumps(output)


@mcp.tool()
def get_adverse_events(drug_name: str, limit: int = 5) -> str:
    """Retrieve FDA FAERS adverse event reports for a specific drug."""
    results = fda_faers.fetch_fda_adverse_events(drug_name, limit)
    return json.dumps({"results": results, "drug": drug_name, "source": "FDA FAERS"})


@mcp.tool()
def find_clinical_trials(condition: str, max_results: int = 5) -> str:
    """Find active recruiting clinical trials for a medical condition."""
    results = omim_clintrials.fetch_clinical_trials(condition, max_results)
    return json.dumps({"results": results, "source": "ClinicalTrials.gov"})


@mcp.tool()
def query_knowledge_graph(symptoms: list[str], depth: int = 3) -> str:
    """Traverse the Neo4j medical knowledge graph to find conditions, genes, and drugs related to symptoms."""
    try:
        data = get_subgraph_for_symptoms(symptoms, depth)
        return json.dumps({"graph": data, "source": "Neo4j Medical Knowledge Graph"})
    except Exception as e:
        return json.dumps({"error": str(e), "nodes": [], "edges": []})


@mcp.tool()
def get_condition_communities(condition_name: str = "") -> str:
    """Get Leiden community clusters from the medical knowledge graph showing related disease groups."""
    try:
        communities = get_communities_from_neo4j()
        if condition_name:
            communities = [
                c for c in communities
                if any(condition_name.lower() in str(m).lower()
                       for m in (c.get("members") or []))
            ]
        return json.dumps({"communities": communities, "source": "Leiden Community Detection"})
    except Exception as e:
        return json.dumps({"error": str(e), "communities": []})


@mcp.tool()
def get_lifestyle_recommendations(conditions: list[str], biomarkers: dict = None) -> str:
    """Get evidence-based lifestyle recommendations for given conditions from medical literature."""
    query = f"lifestyle recommendations {' '.join(conditions)}"
    pubs = pubmed.fetch_pubmed_text(query, 5)
    return json.dumps({
        "conditions": conditions,
        "biomarkers": biomarkers or {},
        "evidence": pubs[:3],
        "source": "PubMed lifestyle evidence retrieval"
    })


@mcp.tool()
def search_omim(query: str) -> str:
    """Search OMIM for genetic disease catalog entries. Requires OMIM API key."""
    results = omim_clintrials.fetch_omim(query, 5)
    return json.dumps({"results": results, "source": "OMIM"})


# ═══════════════════════════════════════════════════════════════
# RESOURCES
# ═══════════════════════════════════════════════════════════════

@mcp.resource("patient://current")
def get_patient_context() -> str:
    """Current active patient profile context."""
    return json.dumps({
        "description": "Active patient profile submitted via VeriDX intake form",
        "fields": ["age", "sex", "bmi", "symptoms", "medications", "medical_history",
                   "family_history", "blood_pressure", "heart_rate", "temperature"]
    })


@mcp.resource("graph://schema")
def get_graph_schema() -> str:
    """Neo4j medical knowledge graph schema — node and edge types."""
    return json.dumps({
        "nodes": ["Symptom", "Condition", "Gene", "Protein", "Drug", "Biomarker",
                  "ClinicalTrial", "Community"],
        "edges": ["INDICATES", "ASSOCIATED_WITH", "ENCODES", "TREATS", "TARGETS",
                  "CONTRAINDICATED_WITH", "ELEVATED_IN", "BELONGS_TO", "STUDIES"],
        "description": "Medical knowledge graph populated from 7 biomedical databases"
    })


@mcp.resource("drugs://chembl-index")
def get_drug_index() -> str:
    """ChEMBL drug index — available drug lookup capabilities."""
    return json.dumps({
        "source": "ChEMBL",
        "capabilities": ["drug_name_lookup", "mechanism_of_action", "target_proteins",
                         "indication_class"],
        "base_url": "https://www.ebi.ac.uk/chembl/api/data/"
    })


@mcp.resource("biomarkers://reference-ranges")
def get_biomarker_ranges() -> str:
    """Standard lab reference ranges for common biomarkers."""
    return json.dumps({
        "HbA1c": {"normal": "<5.7%", "prediabetes": "5.7-6.4%", "diabetes": ">=6.5%"},
        "fasting_glucose": {"normal": "70-100 mg/dL", "prediabetes": "100-125", "diabetes": ">=126"},
        "LDL": {"optimal": "<100 mg/dL", "borderline_high": "130-159", "high": ">=160"},
        "HDL": {"low_risk_male": ">40 mg/dL", "low_risk_female": ">50 mg/dL"},
        "TSH": {"normal": "0.4-4.0 mIU/L"},
        "creatinine": {"male": "0.74-1.35 mg/dL", "female": "0.59-1.04 mg/dL"},
        "hemoglobin": {"male": "13.5-17.5 g/dL", "female": "12.0-15.5 g/dL"}
    })


@mcp.resource("communities://condition-clusters")
def get_community_clusters() -> str:
    """Leiden community detection results — disease cluster summaries."""
    try:
        communities = get_communities_from_neo4j()
        return json.dumps({"communities": communities})
    except Exception:
        return json.dumps({"communities": [], "note": "Neo4j not connected"})


@mcp.resource("ontology://umls-map")
def get_ontology_info() -> str:
    """UMLS ontology mapping information."""
    return json.dumps({
        "description": "Unified Medical Language System concept normalization",
        "purpose": "Maps synonymous medical terms to canonical CUI identifiers",
        "example": {"T2D": "C0011860", "Type 2 Diabetes": "C0011860"},
        "note": "Full UMLS requires license; basic normalization via SciSpacy"
    })


# ═══════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════

@mcp.prompt()
def differential_diagnosis(patient_profile: str, evidence_context: str) -> str:
    """Clinical prompt template for generating ranked differential diagnosis."""
    return f"""You are a clinical reasoning AI. Given the patient profile and evidence below,
generate a ranked differential diagnosis (most to least likely) with:
- Condition name and ICD-10 code
- Confidence score (0-1)
- Key supporting biomarkers and symptoms
- Evidence sources (PubMed, ClinVar, OMIM)
- Recommended confirmatory tests

Patient: {patient_profile}
Evidence: {evidence_context}

Output as structured JSON."""


@mcp.prompt()
def lifestyle_recommendations(conditions: str, biomarkers: str) -> str:
    """Clinical prompt for evidence-based lifestyle recommendations."""
    return f"""Based on the following conditions and biomarkers, provide specific,
evidence-backed lifestyle recommendations covering:
- Nutrition and dietary changes (with specific foods/quantities)
- Physical activity prescription
- Sleep optimization
- Stress management
- Supplement considerations (if evidence-supported)

Each recommendation must cite its evidence source.

Conditions: {conditions}
Biomarkers: {biomarkers}"""


@mcp.prompt()
def drug_safety_review(medications: str, conditions: str, faers_data: str) -> str:
    """Prompt for reviewing medication safety and potential adverse events."""
    return f"""Review the following medications for:
1. Suitability given the patient's conditions
2. Known drug-drug interactions
3. FDA FAERS adverse event signals
4. Dose appropriateness

Medications: {medications}
Patient Conditions: {conditions}
FAERS Data: {faers_data}

Flag any high-risk combinations. Recommend 'continue', 'monitor', or 'review with physician'."""


@mcp.prompt()
def patient_summary(patient_profile: str, top_diagnosis: str) -> str:
    """Generate a concise patient summary for clinician handoff."""
    return f"""Generate a 3-sentence clinical handoff summary for a licensed physician.
Include: key presentation, most likely diagnosis with confidence, and immediate recommended action.

Patient: {patient_profile}
Primary Diagnosis: {top_diagnosis}

Format: plain clinical language, no jargon."""


# ═══════════════════════════════════════════════════════════════
# CLINICAL SERVICE GATEWAY
# ═══════════════════════════════════════════════════════════════

@mcp.tool()
async def diagnose_patient(
    symptoms: list[str],
    age: int = None,
    sex: str = None,
    chief_complaint: str = "",
    current_medications: list[str] = None,
    comorbidities: list[str] = None,
    allergies: str = "",
    family_history: str = "",
    extra_context: str = "",
    uploaded_text: str = ""
) -> str:
    """Run the complete clinical reasoning pipeline for a patient and return the structured diagnostic report.
    
    This encapsulates the entire VeriDX pipeline (database queries, knowledge graph construction,
    community detection, hybrid retrieval, and clinical reasoning) behind a single service call.
    """
    import json
    from backend.services.oracle_engine import run_oracle
    
    patient = {
        "age": age or 0,
        "sex": sex or "Unknown",
        "symptoms": symptoms,
        "medications": current_medications or [],
        "chief_complaint": chief_complaint,
        "comorbidities": comorbidities or [],
        "allergies": allergies,
        "family_history": family_history,
        "extra_context": extra_context
    }
    
    final_data = None
    try:
        async for event in run_oracle(patient, uploaded_text):
            if event.get("type") == "final_answer":
                final_data = event.get("data")
                
        if final_data:
            return json.dumps(final_data, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": "Oracle pipeline execution completed but no final structured report was compiled."
            }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Oracle execution encountered an error: {str(e)}"
        }, indent=2)

