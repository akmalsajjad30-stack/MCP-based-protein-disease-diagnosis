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


class InMemoryGraphStore:
    def __init__(self):
        self.nodes = {}  # node_id -> node_dict
        self.edges = []  # list of edge_dicts
        self.lookup = {} # (label, key_field, key_val_str) -> node_id
        self.counter = 0

    def upsert_node(self, label: str, key_field: str, key_value: str, properties: dict):
        key_value_str = str(key_value)
        key = (label, key_field, key_value_str)
        if key in self.lookup:
            node_id = self.lookup[key]
            self.nodes[node_id]["properties"].update(properties)
            name = properties.get("name") or properties.get("symbol") or properties.get("display_name") or properties.get("nct_id") or key_value_str
            self.nodes[node_id]["name"] = name
        else:
            self.counter += 1
            node_id = f"in_mem_{self.counter}"
            name = properties.get("name") or properties.get("symbol") or properties.get("display_name") or properties.get("nct_id") or key_value_str
            props = dict(properties)
            if "name" not in props:
                props["name"] = name
            self.nodes[node_id] = {
                "id": node_id,
                "label": label,
                "name": name,
                "properties": props
            }
            self.lookup[key] = node_id

    def upsert_relationship(
        self, from_label: str, from_key: str, from_val: str,
        to_label: str, to_key: str, to_val: str,
        rel_type: str, rel_props: dict = None
    ):
        src_id = self.lookup.get((from_label, from_key, str(from_val)))
        tgt_id = self.lookup.get((to_label, to_key, str(to_val)))
        if not src_id or not tgt_id:
            return
        for edge in self.edges:
            if edge["source"] == src_id and edge["target"] == tgt_id and edge["type"] == rel_type:
                edge["properties"].update(rel_props or {})
                return
        self.edges.append({
            "source": src_id,
            "target": tgt_id,
            "type": rel_type,
            "properties": rel_props or {}
        })

    def get_subgraph_for_symptoms(self, symptoms: list, depth: int = 3) -> dict:
        root_ids = set()
        for node_id, node in self.nodes.items():
            if node["label"] == "Symptom":
                node_name = node["name"].lower()
                if any(sym.lower() in node_name for sym in symptoms):
                    root_ids.add(node_id)
        
        visited_nodes = set(root_ids)
        visited_edges = []
        
        current_level = set(root_ids)
        for d in range(depth):
            next_level = set()
            for edge in self.edges:
                if edge["source"] in current_level:
                    if edge["target"] not in visited_nodes:
                        visited_nodes.add(edge["target"])
                        next_level.add(edge["target"])
                    visited_edges.append(edge)
                elif edge["target"] in current_level:
                    if edge["source"] not in visited_nodes:
                        visited_nodes.add(edge["source"])
                        next_level.add(edge["source"])
                    visited_edges.append(edge)
            current_level = next_level
            if not current_level:
                break
        
        out_nodes = []
        for nid in visited_nodes:
            node = self.nodes[nid]
            out_nodes.append({
                "id": node["id"],
                "label": node["label"],
                "name": node["name"],
                "properties": node["properties"]
            })
            
        out_edges = []
        seen_edges = set()
        for edge in visited_edges:
            edge_key = (edge["source"], edge["target"], edge["type"])
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                out_edges.append({
                    "source": edge["source"],
                    "target": edge["target"],
                    "type": edge["type"]
                })
                
        return {"nodes": out_nodes, "edges": out_edges}

    def query(self, cypher: str, params: dict = None) -> list:
        # Match exporter query in community_detector.py
        if "MATCH (a)-[r]->(b)" in cypher:
            rows = []
            for edge in self.edges:
                src_node = self.nodes.get(edge["source"])
                tgt_node = self.nodes.get(edge["target"])
                if src_node and tgt_node:
                    src_name = src_node.get("name")
                    tgt_name = tgt_node.get("name")
                    if src_name and tgt_name:
                        rows.append({
                            "source_id": src_node["id"],
                            "source_label": src_node["label"],
                            "source_name": src_name,
                            "rel_type": edge["type"],
                            "target_id": tgt_node["id"],
                            "target_label": tgt_node["label"],
                            "target_name": tgt_name,
                        })
            return rows

        # Match get communities query in community_detector.py
        if "MATCH (cm:Community)" in cypher:
            rows = []
            for node in self.nodes.values():
                if node["label"] == "Community":
                    props = node["properties"]
                    rows.append({
                        "id": props.get("community_id"),
                        "label": props.get("label"),
                        "summary": props.get("summary", ""),
                        "members": props.get("member_names", []),
                        "size": props.get("size", 0)
                    })
            rows.sort(key=lambda x: x["size"], reverse=True)
            return rows

        # Match hybrid search query
        if "MATCH (s:Symptom)-[:INDICATES]->(c:Condition)" in cypher:
            symptoms = (params or {}).get("symptoms", [])
            rows = []
            for sym in symptoms:
                for s_node in self.nodes.values():
                    if s_node["label"] == "Symptom" and sym.lower() in s_node["name"].lower():
                        for edge1 in self.edges:
                            if edge1["source"] == s_node["id"] and edge1["type"] == "INDICATES":
                                c_node = self.nodes.get(edge1["target"])
                                if c_node and c_node["label"] == "Condition":
                                    genes = []
                                    for edge2 in self.edges:
                                        if edge2["source"] == c_node["id"] and edge2["type"] == "ASSOCIATED_WITH":
                                            g_node = self.nodes.get(edge2["target"])
                                            if g_node and g_node["label"] == "Gene":
                                                genes.append(g_node)
                                    if not genes:
                                        genes = [None]
                                    
                                    drugs = []
                                    for edge3 in self.edges:
                                        if edge3["target"] == c_node["id"] and edge3["type"] == "TREATS":
                                            d_node = self.nodes.get(edge3["source"])
                                            if d_node and d_node["label"] == "Drug":
                                                drugs.append(d_node)
                                    if not drugs:
                                        drugs = [None]
                                        
                                    communities = []
                                    for edge4 in self.edges:
                                        if edge4["source"] == c_node["id"] and edge4["type"] == "BELONGS_TO":
                                            cm_node = self.nodes.get(edge4["target"])
                                            if cm_node and cm_node["label"] == "Community":
                                                communities.append(cm_node)
                                    if not communities:
                                        communities = [None]
                                        
                                    for g in genes:
                                        for d in drugs:
                                            for cm in communities:
                                                rows.append({
                                                    "symptom": s_node["name"],
                                                    "condition": c_node["name"],
                                                    "cond_desc": c_node["properties"].get("description", ""),
                                                    "gene": g["properties"].get("symbol") if g else None,
                                                    "gene_function": g["properties"].get("function", "") if g else None,
                                                    "drug": d["name"] if d else None,
                                                    "drug_indication": d["properties"].get("indication", "") if d else None,
                                                    "community_summary": cm["properties"].get("summary", "") if cm else None
                                                })
            return rows[:50]

        return []


in_memory_store = InMemoryGraphStore()
USE_IN_MEMORY_FALLBACK = False
_connectivity_checked = False


def check_neo4j_availability() -> bool:
    global USE_IN_MEMORY_FALLBACK, _connectivity_checked
    if _connectivity_checked:
        return not USE_IN_MEMORY_FALLBACK
    _connectivity_checked = True
    try:
        driver = get_driver()
        if hasattr(driver, "verify_connectivity"):
            driver.verify_connectivity()
        else:
            with driver.session() as session:
                session.run("RETURN 1")
        USE_IN_MEMORY_FALLBACK = False
        logger.info("Neo4j database is online and reachable.")
    except Exception as e:
        USE_IN_MEMORY_FALLBACK = True
        logger.warning(f"Neo4j database not reachable: {e}. Falling back to in-memory graph.")
    return not USE_IN_MEMORY_FALLBACK


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
    check_neo4j_availability()
    if USE_IN_MEMORY_FALLBACK:
        return in_memory_store.query(cypher, params)
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [dict(record) for record in result]


def init_schema():
    """Create indexes and constraints for the medical knowledge graph."""
    check_neo4j_availability()
    if USE_IN_MEMORY_FALLBACK:
        logger.info("Using in-memory fallback schema (no action needed).")
        return
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
    check_neo4j_availability()
    if USE_IN_MEMORY_FALLBACK:
        return in_memory_store.get_subgraph_for_symptoms(symptoms, depth)
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
    check_neo4j_availability()
    if USE_IN_MEMORY_FALLBACK:
        in_memory_store.upsert_node(label, key_field, key_value, properties)
        return
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
    check_neo4j_availability()
    if USE_IN_MEMORY_FALLBACK:
        in_memory_store.upsert_relationship(
            from_label, from_key, from_val,
            to_label, to_key, to_val,
            rel_type, rel_props
        )
        return
    cypher = f"""
    MATCH (a:{from_label} {{{from_key}: $from_val}})
    MATCH (b:{to_label} {{{to_key}: $to_val}})
    MERGE (a)-[r:{rel_type}]->(b)
    SET r += $props
    RETURN r
    """
    run_query(cypher, {"from_val": from_val, "to_val": to_val, "props": rel_props or {}})
