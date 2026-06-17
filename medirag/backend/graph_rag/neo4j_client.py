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


def get_subgraph_for_symptoms(symptoms: list, depth: int = 3) -> dict:
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
        relationshipFilter: 'INDICATES>|ASSOCIATED_WITH>|TREATS>|TARGETS>|BELONGS_TO>|ENCODES>'
    })
    YIELD nodes, relationships
    RETURN nodes, relationships
    LIMIT 200
    """
    # Fallback without APOC
    cypher_simple = """
    UNWIND $symptoms AS symptom_name
    MATCH (s:Symptom)-[r1:INDICATES]->(c:Condition)
    WHERE toLower(s.name) CONTAINS toLower(symptom_name)
    OPTIONAL MATCH (c)-[r2:ASSOCIATED_WITH]->(g:Gene)
    OPTIONAL MATCH (g)-[r3:ENCODES]->(p:Protein)
    OPTIONAL MATCH (d:Drug)-[r4:TREATS]->(c)
    RETURN s, r1, c, r2, g, r3, p, r4, d
    LIMIT 150
    """
    nodes = []
    edges = []
    seen_nodes = set()
    seen_edges = set()

    def process_value(val):
        if val is None:
            return
        if isinstance(val, (list, set, tuple)):
            for item in val:
                process_value(item)
            return

        # Check if Node
        if hasattr(val, "labels"):
            node_id = str(val.element_id) if hasattr(val, "element_id") else str(val.id)
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                labels = list(val.labels)
                label = labels[0] if labels else "Node"
                props = dict(val)
                if label == "Gene":
                    name = props.get("symbol") or props.get("name") or ""
                elif label == "ClinicalTrial":
                    name = props.get("nct_id") or props.get("title") or ""
                else:
                    name = props.get("display_name") or props.get("name") or ""
                nodes.append({
                    "id": node_id,
                    "label": label,
                    "name": name,
                    "properties": props
                })
        # Check if Relationship
        elif hasattr(val, "start_node") and hasattr(val, "end_node"):
            rel_id = str(val.element_id) if hasattr(val, "element_id") else str(val.id)
            if rel_id not in seen_edges:
                seen_edges.add(rel_id)
                src = str(val.start_node.element_id) if hasattr(val.start_node, "element_id") else str(val.start_node.id)
                tgt = str(val.end_node.element_id) if hasattr(val.end_node, "element_id") else str(val.end_node.id)
                edges.append({
                    "source": src,
                    "target": tgt,
                    "type": val.type
                })

    try:
        results = run_query(cypher, {"symptoms": symptoms, "depth": depth})
        for row in results:
            for val in dict(row).values():
                process_value(val)
        return {"nodes": nodes, "edges": edges}
    except Exception:
        try:
            results = run_query(cypher_simple, {"symptoms": symptoms})
            for row in results:
                for val in dict(row).values():
                    process_value(val)
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
