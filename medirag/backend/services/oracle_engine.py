"""
Oracle Engine — main orchestrator for the VeriDX pipeline.
Coordinates: DB fetch -> graph build -> community detect -> hybrid retrieve -> DeepSeek stream
"""
import asyncio
import logging
from typing import AsyncGenerator

from backend.databases import pubmed, uniprot, clinvar, chembl, fda_faers, omim_clintrials
from backend.graph_rag import graph_builder, community_detector
from backend.graph_rag.hybrid_retriever import hybrid_retrieve
from backend.vector_store.chroma_store import add_documents
from backend.services.deepseek_client import stream_oracle_reasoning

logger = logging.getLogger(__name__)


async def run_oracle(patient: dict, uploaded_text: str = "") -> AsyncGenerator[dict, None]:
    """
    Full VeriDX Oracle pipeline. Yields WebSocket events:
      {type: 'phase', phase: str, message: str}
      {type: 'tool_call', tool: str, status: 'running'|'done'|'error'}
      {type: 'reasoning', text: str}        <- DeepSeek think tokens
      {type: 'answer_chunk', text: str}     <- partial JSON tokens
      {type: 'final_answer', data: dict}    <- structured artifacts
      {type: 'graph_data', data: dict}      <- Neo4j subgraph
      {type: 'communities', data: list}     <- Leiden communities
      {type: 'error', text: str}
    """
    symptoms = patient.get("symptoms", [])
    if isinstance(symptoms, str):
        symptoms = [s.strip() for s in symptoms.split(",")]
    # Support both field names from the intake form
    medications = patient.get("medications") or patient.get("current_medications", "")
    if isinstance(medications, str):
        medications = [m.strip() for m in medications.split(",") if m.strip()]
    elif not isinstance(medications, list):
        medications = []
    symptom_query = " ".join(symptoms) or patient.get("chief_complaint", "")
    if uploaded_text:
        patient["uploaded_text"] = uploaded_text[:3000]

    loop = asyncio.get_running_loop()

    # Phase 1: Database fetching
    yield {"type": "phase", "phase": "fetching", "message": "Querying biomedical databases..."}

    # Signal all tools are running
    yield {"type": "tool_call", "tool": "fetch_pubmed", "status": "running"}
    yield {"type": "tool_call", "tool": "fetch_uniprot", "status": "running"}
    yield {"type": "tool_call", "tool": "fetch_clinvar", "status": "running"}
    yield {"type": "tool_call", "tool": "fetch_trials", "status": "running"}
    if medications:
        yield {"type": "tool_call", "tool": "fetch_chembl", "status": "running"}
        yield {"type": "tool_call", "tool": "fetch_faers", "status": "running"}

    # Define parallel query tasks
    pubmed_task = loop.run_in_executor(None, pubmed.fetch_pubmed_text, symptom_query, 8)
    uniprot_task = loop.run_in_executor(None, uniprot.fetch_uniprot, symptom_query, 5)
    clinvar_task = loop.run_in_executor(None, clinvar.fetch_clinvar, symptom_query, 5)
    trial_task = loop.run_in_executor(None, omim_clintrials.fetch_clinical_trials, symptom_query, 5)

    async def fetch_drugs():
        d_docs, f_docs = [], []
        for med in medications[:5]:
            d_docs.extend(await loop.run_in_executor(None, chembl.fetch_drug_info, med))
            f_docs.extend(await loop.run_in_executor(None, fda_faers.fetch_fda_adverse_events, med, 3))
        return d_docs, f_docs

    if medications:
        drugs_task = asyncio.create_task(fetch_drugs())
        pubmed_texts, uniprot_results, clinvar_results, trial_results, (drug_docs, faers_docs) = await asyncio.gather(
            pubmed_task, uniprot_task, clinvar_task, trial_task, drugs_task
        )
    else:
        pubmed_texts, uniprot_results, clinvar_results, trial_results = await asyncio.gather(
            pubmed_task, uniprot_task, clinvar_task, trial_task
        )
        drug_docs, faers_docs = [], []

    # Signal all tools are done
    yield {"type": "tool_call", "tool": "fetch_pubmed", "status": "done"}
    yield {"type": "tool_call", "tool": "fetch_uniprot", "status": "done"}
    yield {"type": "tool_call", "tool": "fetch_clinvar", "status": "done"}
    yield {"type": "tool_call", "tool": "fetch_trials", "status": "done"}
    if medications:
        yield {"type": "tool_call", "tool": "fetch_chembl", "status": "done"}
        yield {"type": "tool_call", "tool": "fetch_faers", "status": "done"}

    # Phase 2: Build Knowledge Graph
    yield {"type": "phase", "phase": "building_graph", "message": "Building knowledge graph..."}
    yield {"type": "tool_call", "tool": "build_graph", "status": "running"}
    try:
        await loop.run_in_executor(None, graph_builder.build_symptom_nodes, symptoms)
        
        # Build comorbidity nodes and link to symptoms
        comorbidities = patient.get("comorbidities", [])
        if isinstance(comorbidities, str):
            comorbidities = [c.strip() for c in comorbidities.split(",") if c.strip()]
        for com in comorbidities:
            await loop.run_in_executor(
                None,
                graph_builder.upsert_node,
                "Condition",
                "name",
                com.lower().strip(),
                {
                    "name": com.lower().strip(),
                    "display_name": com.strip(),
                    "source": "Patient History"
                }
            )
            for symptom in symptoms:
                try:
                    await loop.run_in_executor(
                        None,
                        graph_builder.upsert_relationship,
                        "Symptom", "name", symptom.lower().strip(),
                        "Condition", "name", com.lower().strip(),
                        "ASSOCIATED_WITH", {"source": "Patient History"}
                    )
                except Exception:
                    pass

        # Build from PubMed
        pubmed_dicts = [{"text": text, "pmid": ""} for text in pubmed_texts]
        await loop.run_in_executor(None, graph_builder.build_from_pubmed, pubmed_dicts, symptoms)

        # Build from UniProt
        await loop.run_in_executor(None, graph_builder.build_from_uniprot, uniprot_results)
        
        # Build from ChEMBL
        if drug_docs:
            await loop.run_in_executor(None, graph_builder.build_from_chembl, drug_docs, symptoms + comorbidities)

        # Build from Clinical Trials
        await loop.run_in_executor(None, graph_builder.build_from_clinical_trials, trial_results)

        yield {"type": "tool_call", "tool": "build_graph", "status": "done"}
    except Exception as e:
        logger.warning(f"Graph build failed (Neo4j may not be running): {e}")
        yield {"type": "tool_call", "tool": "build_graph", "status": "error"}

    # Embed all docs into ChromaDB
    all_docs = (
        [{"id": f"pubmed_{i}", "text": t, "source": "PubMed"} for i, t in enumerate(pubmed_texts)]
        + [{"id": f"uniprot_{i}", "text": r.get("text",""), "source": "UniProt"} for i, r in enumerate(uniprot_results)]
        + [{"id": f"clinvar_{i}", "text": r.get("text",""), "source": "ClinVar"} for i, r in enumerate(clinvar_results)]
        + [{"id": f"chembl_{i}", "text": r.get("text",""), "source": "ChEMBL"} for i, r in enumerate(drug_docs)]
        + [{"id": f"faers_{i}", "text": r.get("text",""), "source": "FDA FAERS"} for i, r in enumerate(faers_docs)]
        + [{"id": f"trial_{i}", "text": r.get("text",""), "source": "ClinicalTrials.gov"} for i, r in enumerate(trial_results)]
    )
    if uploaded_text:
        all_docs.append({"id": "upload_0", "text": uploaded_text[:2000], "source": "Patient Upload"})

    try:
        await loop.run_in_executor(None, add_documents, all_docs)
    except Exception as e:
        logger.warning(f"ChromaDB embed failed: {e}")

    # Phase 3: Community Detection
    yield {"type": "tool_call", "tool": "detect_communities", "status": "running"}
    try:
        await loop.run_in_executor(None, community_detector.run_community_detection)
        communities = await loop.run_in_executor(None, community_detector.get_communities_from_neo4j)
        yield {"type": "communities", "data": communities}
        yield {"type": "tool_call", "tool": "detect_communities", "status": "done"}
    except Exception as e:
        logger.warning(f"Community detection failed: {e}")
        communities = []
        yield {"type": "tool_call", "tool": "detect_communities", "status": "error"}

    # Phase 4: Hybrid Retrieval
    yield {"type": "phase", "phase": "retrieving", "message": "Retrieving evidence..."}
    yield {"type": "tool_call", "tool": "hybrid_retrieve", "status": "running"}
    try:
        chunks = await loop.run_in_executor(None, hybrid_retrieve, symptom_query, symptoms, 12)
        context = "\n\n---\n\n".join(chunks)
        yield {"type": "tool_call", "tool": "hybrid_retrieve", "status": "done"}
    except Exception as e:
        logger.warning(f"Hybrid retrieval failed: {e}")
        context = "\n\n".join([d["text"] for d in all_docs[:10] if d.get("text")])
        yield {"type": "tool_call", "tool": "hybrid_retrieve", "status": "error"}

    # Graph visualization data
    try:
        from backend.graph_rag.neo4j_client import get_subgraph_for_symptoms
        graph_data = await loop.run_in_executor(None, get_subgraph_for_symptoms, symptoms, 3)
        yield {"type": "graph_data", "data": graph_data}
    except Exception:
        yield {"type": "graph_data", "data": {"nodes": [], "edges": []}}

    # Phase 5: DeepSeek Reasoner
    yield {"type": "phase", "phase": "reasoning", "message": "Oracle is reasoning..."}
    yield {"type": "tool_call", "tool": "deepseek_reasoner", "status": "running"}
    async for event in stream_oracle_reasoning(patient, context):
        yield event
        if event.get("type") == "final_answer":
            yield {"type": "tool_call", "tool": "deepseek_reasoner", "status": "done"}
            yield {"type": "tool_call", "tool": "generate_report", "status": "done"}

    yield {"type": "phase", "phase": "complete", "message": "Analysis complete."}
