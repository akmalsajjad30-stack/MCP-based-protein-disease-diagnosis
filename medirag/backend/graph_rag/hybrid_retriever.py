"""
Hybrid retriever — fuses 3 retrieval modes via Reciprocal Rank Fusion (RRF).
Mode 1: ChromaDB vector similarity (semantic)
Mode 2: Neo4j Cypher graph traversal (structural)
Mode 3: Community summaries (global context)
"""
import logging
from backend.vector_store.chroma_store import query_chroma
from backend.graph_rag.neo4j_client import run_query, get_subgraph_for_symptoms
from backend.graph_rag.community_detector import get_communities_from_neo4j

logger = logging.getLogger(__name__)


def rrf_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
    """
    Reciprocal Rank Fusion of multiple ranked lists.
    Returns merged ranked list of document IDs/texts.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked):
            scores[doc] = scores.get(doc, 0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)


def vector_retrieve(query: str, k: int = 8) -> list[str]:
    """Mode 1: ChromaDB semantic similarity search."""
    try:
        results = query_chroma(query, n_results=k)
        return [r["text"] for r in results if r.get("text")]
    except Exception as e:
        logger.warning(f"Vector retrieval failed: {e}")
        return []


def graph_retrieve(symptoms: list[str], depth: int = 2) -> list[str]:
    """Mode 2: Neo4j graph traversal — get condition/gene/drug context."""
    try:
        # Multi-hop Cypher: symptom → condition → gene/drug
        cypher = """
        UNWIND $symptoms AS sym
        MATCH (s:Symptom)-[:INDICATES]->(c:Condition)
        WHERE toLower(s.name) CONTAINS toLower(sym)
        OPTIONAL MATCH (c)-[:ASSOCIATED_WITH]->(g:Gene)
        OPTIONAL MATCH (d:Drug)-[:TREATS]->(c)
        OPTIONAL MATCH (c)-[:BELONGS_TO]->(cm:Community)
        RETURN 
            s.name AS symptom,
            c.name AS condition,
            c.description AS cond_desc,
            g.symbol AS gene,
            g.function AS gene_function,
            d.name AS drug,
            d.indication AS drug_indication,
            cm.summary AS community_summary
        LIMIT 50
        """
        rows = run_query(cypher, {"symptoms": symptoms})
        texts = []
        for row in rows:
            parts = []
            if row.get("condition"):
                parts.append(f"Condition: {row['condition']}")
            if row.get("gene"):
                parts.append(f"Gene: {row['gene']} — {row.get('gene_function', '')[:200]}")
            if row.get("drug"):
                parts.append(f"Drug: {row['drug']} treats {row.get('condition', '')}")
            if row.get("community_summary"):
                parts.append(f"Disease cluster: {row['community_summary']}")
            if parts:
                texts.append(" | ".join(parts))
        return texts
    except Exception as e:
        logger.warning(f"Graph retrieval failed: {e}")
        return []


def community_retrieve(query_terms: list[str]) -> list[str]:
    """Mode 3: Match condition communities to patient's context."""
    try:
        communities = get_communities_from_neo4j()
        texts = []
        for cm in communities:
            summary = cm.get("summary", "")
            members = cm.get("members", [])
            if not summary and not members:
                continue
            # Simple relevance: check if any query term appears in member names
            relevant = any(
                any(term.lower() in m.lower() for m in (members or []))
                for term in query_terms
            )
            if relevant or not query_terms:
                member_str = ", ".join(str(m) for m in (members or [])[:8])
                texts.append(
                    f"Disease community: {summary or 'No summary yet'}. "
                    f"Related conditions: {member_str}."
                )
        return texts
    except Exception as e:
        logger.warning(f"Community retrieval failed: {e}")
        return []


def hybrid_retrieve(
    query: str,
    symptoms: list[str],
    k_total: int = 12
) -> list[str]:
    """
    Full hybrid retrieval: vector + graph + community → RRF fusion.
    Returns top-k context chunks for DeepSeek.
    """
    logger.info(f"Hybrid retrieve: query='{query[:50]}', symptoms={symptoms}")

    vector_results = vector_retrieve(query, k=8)
    graph_results = graph_retrieve(symptoms, depth=2)
    community_results = community_retrieve(symptoms)

    # RRF fusion
    all_ranked = [r for r in [vector_results, graph_results, community_results] if r]
    if not all_ranked:
        return []

    fused = rrf_fusion(all_ranked)
    return fused[:k_total]
