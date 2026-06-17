"""
Neo4j client — manages driver lifecycle and Cypher query helpers.
Uses free Neo4j Community Edition (no GDS needed for Leiden — we use python-leidenalg).
"""
from neo4j import GraphDatabase, Driver
from backend.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_driver: Optional[Driver] = None



def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            connection_timeout=3,
            max_connection_lifetime=300,
        )
    return _driver



def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def run_query(cypher: str, params: dict = None) -> list:
    """Execute a Cypher query and return results as list of dicts."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [dict(record) for record in result]


def init_schema():
    """Create indexes and constraints for the medical knowledge graph."""
    constraints = [
        "CREATE CONSTRAINT symptom_name IF NOT EXISTS FOR (s:Symptom) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT condition_name IF NOT EXISTS FOR (c:Condition) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT gene_symbol IF NOT EXISTS FOR (g:Gene) REQUIRE g.symbol IS UNIQUE",
        "CREATE CONSTRAINT protein_id IF NOT EXISTS FOR (p:Protein) REQUIRE p.uniprot_id IS UNIQUE",
        "CREATE CONSTRAINT drug_name IF NOT EXISTS FOR (d:Drug) REQUIRE d.name IS UNIQUE",
        "CREATE CONSTRAINT biomarker_name IF NOT EXISTS FOR (b:Biomarker) REQUIRE b.name IS UNIQUE",
        "CREATE CONSTRAINT trial_id IF NOT EXISTS FOR (t:ClinicalTrial) REQUIRE t.nct_id IS UNIQUE",
        "CREATE CONSTRAINT community_id IF NOT EXISTS FOR (cm:Community) REQUIRE cm.community_id IS UNIQUE",
    ]
    indexes = [
        "CREATE INDEX symptom_cui IF NOT EXISTS FOR (s:Symptom) ON (s.cui)",
        "CREATE INDEX condition_cui IF NOT EXISTS FOR (c:Condition) ON (c.cui)",
        "CREATE FULLTEXT INDEX medical_search IF NOT EXISTS FOR (n:Symptom|Condition|Drug|Gene) ON EACH [n.name, n.description]",
    ]
    driver = get_driver()
    with driver.session() as session:
        for stmt in constraints + indexes:
            try:
                session.run(stmt)
            except Exception as e:
                logger.warning(f"Schema init warning: {e}")
    logger.info("Neo4j schema initialized.")


def get_subgraph_for_symptoms(symptoms: list, depth: int = 2) -> dict:
    """
    Retrieve a subgraph of nodes and edges related to given symptoms.
    Returns nodes and relationships for frontend visualization.
    """
    cypher = """
    UNWIND $symptoms AS symptom_name
    MATCH (s:Symptom)
    WHERE toLower(s.name) CONTAINS toLower(symptom_name)
    CALL apoc.path.subgraphAll(s, {
        maxLevel: $depth,
        relationshipFilter: 'INDICATES>|ASSOCIATED_WITH>|TREATS>|TARGETS>|BELONGS_TO>'
    })
    YIELD nodes, relationships
    RETURN nodes, relationships
    LIMIT 200
    """
    # Fallback without APOC
    cypher_simple = """
    UNWIND $symptoms AS symptom_name
    MATCH (s:Symptom)-[:INDICATES]->(c:Condition)
    WHERE toLower(s.name) CONTAINS toLower(symptom_name)
    OPTIONAL MATCH (c)-[:ASSOCIATED_WITH]->(g:Gene)
    OPTIONAL MATCH (d:Drug)-[:TREATS]->(c)
    RETURN s, c, g, d
    LIMIT 100
    """
    try:
        results = run_query(cypher, {"symptoms": symptoms, "depth": depth})
        nodes = []
        edges = []
        seen_nodes = set()
        seen_edges = set()
        for row in results:
            for node in (row.get("nodes") or []):
                node_id = str(node.element_id) if hasattr(node, "element_id") else str(node.id)
                if node_id not in seen_nodes:
                    seen_nodes.add(node_id)
                    labels = list(node.labels) if hasattr(node, "labels") else []
                    nodes.append({
                        "id": node_id,
                        "label": labels[0] if labels else "Node",
                        "name": dict(node).get("name", ""),
                        "properties": dict(node)
                    })
            for rel in (row.get("relationships") or []):
                rel_id = str(rel.element_id) if hasattr(rel, "element_id") else str(rel.id)
                if rel_id not in seen_edges:
                    seen_edges.add(rel_id)
                    src = str(rel.start_node.element_id) if hasattr(rel.start_node, "element_id") else str(rel.start_node.id)
                    tgt = str(rel.end_node.element_id) if hasattr(rel.end_node, "element_id") else str(rel.end_node.id)
                    edges.append({"source": src, "target": tgt, "type": rel.type})
        return {"nodes": nodes, "edges": edges}
    except Exception:
        try:
            results = run_query(cypher_simple, {"symptoms": symptoms})
            nodes = []
            edges = []
            seen_nodes = set()
            for row in results:
                for key in ["s", "c", "g", "d"]:
                    node = row.get(key)
                    if node:
                        node_id = str(node.element_id) if hasattr(node, "element_id") else str(node.id)
                        if node_id not in seen_nodes:
                            seen_nodes.add(node_id)
                            labels = list(node.labels) if hasattr(node, "labels") else []
                            nodes.append({
                                "id": node_id,
                                "label": labels[0] if labels else "Node",
                                "name": dict(node).get("name", ""),
                                "properties": dict(node)
                            })
            return {"nodes": nodes, "edges": edges}
        except Exception as e2:
            logger.error(f"Graph query failed: {e2}")
            return {"nodes": [], "edges": []}


def upsert_node(label: str, key_field: str, key_value: str, properties: dict):
    """Upsert a node in Neo4j."""
    cypher = f"""
    MERGE (n:{label} {{{key_field}: $key_value}})
    SET n += $props
    RETURN n
    """
    run_query(cypher, {"key_value": key_value, "props": properties})


def upsert_relationship(
    from_label: str, from_key: str, from_val: str,
    to_label: str, to_key: str, to_val: str,
    rel_type: str, rel_props: dict = None
):
    """Upsert a relationship between two nodes."""
    cypher = f"""
    MATCH (a:{from_label} {{{from_key}: $from_val}})
    MATCH (b:{to_label} {{{to_key}: $to_val}})
    MERGE (a)-[r:{rel_type}]->(b)
    SET r += $props
    RETURN r
    """
    run_query(cypher, {"from_val": from_val, "to_val": to_val, "props": rel_props or {}})
