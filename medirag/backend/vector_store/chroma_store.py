"""
ChromaDB vector store — embedding + semantic retrieval.
Uses sentence-transformers (free, runs locally).
"""
import logging
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions
from backend.config import CHROMA_PERSIST_DIR
from backend.services.security import encrypt_text, decrypt_text

logger = logging.getLogger(__name__)

_client: Optional[chromadb.PersistentClient] = None
_collection = None

COLLECTION_NAME = "medirag_medical_knowledge"

_embedding_fn = None

def get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embedding_fn


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=get_embedding_fn(),
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def add_documents(docs: list, batch_size: int = 100):
    """
    Add documents to ChromaDB.
    Each doc must have: {id, text, source, metadata (optional)}
    """
    collection = get_collection()
    ids, texts, metadatas = [], [], []

    for doc in docs:
        doc_id = str(doc.get("id", hash(doc.get("text", ""))))
        text = doc.get("text", "").strip()
        if not text:
            continue
        ids.append(doc_id)
        texts.append(text[:2000])  # ChromaDB has token limits
        metadatas.append({
            "source": str(doc.get("source", "unknown")),
            "url": str(doc.get("url", "")),
        })

    if not ids:
        return

    # Add in batches
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        # Skip existing IDs
        existing = collection.get(ids=batch_ids)["ids"]
        new_mask = [bid not in existing for bid in batch_ids]
        if not any(new_mask):
            continue
            
        filtered_ids = [bid for bid, keep in zip(batch_ids, new_mask) if keep]
        filtered_texts = [t for t, keep in zip(texts[i:i+batch_size], new_mask) if keep]
        filtered_metas = [m for m, keep in zip(metadatas[i:i+batch_size], new_mask) if keep]
        
        # 1. Generate embeddings on PLAINTEXT
        embed_fn = get_embedding_fn()
        embeddings = embed_fn(filtered_texts)
        
        # 2. Encrypt text for storage
        encrypted_texts = [encrypt_text(t) for t in filtered_texts]
        
        collection.add(
            ids=filtered_ids,
            embeddings=embeddings,
            documents=encrypted_texts,
            metadatas=filtered_metas,
        )
    logger.info(f"Added {len(ids)} documents to ChromaDB.")


def query_chroma(query: str, n_results: int = 8) -> list:
    """Query ChromaDB for semantically similar documents."""
    try:
        collection = get_collection()
        count = collection.count()
        if count == 0:
            return []
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, count),
            include=["documents", "metadatas", "distances"]
        )
        output = []
        for text, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            decrypted_text = decrypt_text(text)
            output.append({
                "text": decrypted_text,
                "source": meta.get("source", ""),
                "url": meta.get("url", ""),
                "score": 1 - dist  # convert cosine distance to similarity
            })
        return output
    except Exception as e:
        logger.error(f"ChromaDB query error: {e}")
        return []


def clear_collection():
    """Clear all documents from the collection."""
    collection = get_collection()
    collection.delete(where={"source": {"$ne": "___never___"}})
