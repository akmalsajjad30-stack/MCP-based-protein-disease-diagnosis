"""
Community detection using python-leidenalg (free).
Exports graph from Neo4j → NetworkX → Leiden → writes communities back to Neo4j.
"""
import logging
import networkx as nx
from backend.graph_rag.neo4j_client import run_query, upsert_node, upsert_relationship

logger = logging.getLogger(__name__)


def export_graph_to_networkx() -> nx.Graph:
    """Pull the medical knowledge graph from Neo4j into a NetworkX graph."""
    cypher = """
    MATCH (a)-[r]->(b)
    WHERE a.name IS NOT NULL AND b.name IS NOT NULL
    RETURN 
        id(a) AS source_id, labels(a)[0] AS source_label, a.name AS source_name,
        type(r) AS rel_type,
        id(b) AS target_id, labels(b)[0] AS target_label, b.name AS target_name
    LIMIT 5000
    """
    try:
        rows = run_query(cypher)
        G = nx.Graph()
        for row in rows:
            src = row["source_id"]
            tgt = row["target_id"]
            G.add_node(src, label=row["source_label"], name=row["source_name"])
            G.add_node(tgt, label=row["target_label"], name=row["target_name"])
            G.add_edge(src, tgt, rel_type=row["rel_type"])
        logger.info(f"Exported graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G
    except Exception as e:
        logger.error(f"Failed to export graph: {e}")
        return nx.Graph()


def detect_communities_leiden(G: nx.Graph) -> dict[int, int]:
    """
    Run Leiden community detection.
    Falls back to Louvain if leidenalg is unavailable.
    Returns {node_id: community_id}.
    """
    if G.number_of_nodes() < 3:
        return {}
    try:
        # pyrefly: ignore [missing-import]
        # pyrefly: ignore [missing-import]
        # pyrefly: ignore [missing-import]
        # pyrefly: ignore [missing-import]
        import leidenalg
        # pyrefly: ignore [missing-import]
        import igraph as ig
        # Convert NetworkX to igraph
        ig_graph = ig.Graph.from_networkx(G)
        partition = leidenalg.find_partition(
            ig_graph,
            leidenalg.ModularityVertexPartition,
            seed=42
        )
        nx_nodes = list(G.nodes())
        membership = {nx_nodes[i]: partition.membership[i] for i in range(len(nx_nodes))}
        # If all nodes are grouped in a single community, try a higher resolution partition
        if len(set(membership.values())) <= 1:
            try:
                partition = leidenalg.find_partition(
                    ig_graph,
                    leidenalg.RBConfigurationVertexPartition,
                    resolution_parameter=1.5,
                    seed=42
                )
                membership = {nx_nodes[i]: partition.membership[i] for i in range(len(nx_nodes))}
            except Exception:
                pass
        return membership
    except ImportError:
        logger.warning("leidenalg not available, falling back to Louvain.")
        try:
            # pyrefly: ignore [missing-import]
            from community import best_partition
            return best_partition(G, random_state=42)
        except ImportError:
            logger.warning("python-louvain not available, using greedy modularity.")
            communities = nx.community.greedy_modularity_communities(G)
            membership = {}
            for comm_id, comm in enumerate(communities):
                for node in comm:
                    membership[node] = comm_id
            return membership


def write_communities_to_neo4j(G: nx.Graph, membership: dict[int, int]):
    """Write detected communities back to Neo4j as Community nodes."""
    # Group nodes by community
    community_members: dict[int, list] = {}
    for node_id, comm_id in membership.items():
        community_members.setdefault(comm_id, []).append(node_id)

    for comm_id, members in community_members.items():
        # Get member names from graph
        member_names = [
            G.nodes[n].get("name", "") for n in members
            if G.nodes[n].get("name")
        ][:10]  # limit for display

        upsert_node("Community", "community_id", str(comm_id), {
            "community_id": str(comm_id),
            "size": len(members),
            "member_names": member_names,
            "label": f"Community {comm_id}",
            "summary": ""  # filled by community_summarizer
        })

        # Link member nodes to their community
        for node_id in members:
            node_data = G.nodes.get(node_id, {})
            node_name = node_data.get("name", "")
            node_label = node_data.get("label", "")
            if node_name and node_label:
                try:
                    upsert_relationship(
                        node_label, "name", node_name,
                        "Community", "community_id", str(comm_id),
                        "BELONGS_TO"
                    )
                except Exception:
                    pass

    logger.info(f"Wrote {len(community_members)} communities to Neo4j.")
    return community_members


def run_community_detection() -> dict:
    """Full pipeline: export → detect → write back. Returns community map."""
    G = export_graph_to_networkx()
    if G.number_of_nodes() < 3:
        logger.info("Graph too small for community detection.")
        return {}
    membership = detect_communities_leiden(G)
    community_map = write_communities_to_neo4j(G, membership)
    return {
        "num_communities": len(community_map),
        "communities": {
            str(k): [G.nodes[n].get("name", "") for n in v]
            for k, v in community_map.items()
        }
    }


def get_communities_from_neo4j() -> list[dict]:
    """Retrieve all communities with their summaries from Neo4j."""
    cypher = """
    MATCH (cm:Community)
    RETURN cm.community_id AS id, cm.label AS label,
           cm.summary AS summary, cm.member_names AS members, cm.size AS size
    ORDER BY cm.size DESC
    """
    try:
        return run_query(cypher)
    except Exception as e:
        logger.error(f"Failed to get communities: {e}")
        return []
