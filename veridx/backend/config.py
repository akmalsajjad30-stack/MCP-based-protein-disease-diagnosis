"""
VeriDX v3 — Configuration
Loads all environment variables with sensible defaults.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Optimize HuggingFace local loading speed (offline mode)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")  # Can be overridden (e.g. to deepseek-chat)
DEEPSEEK_CHAT_MODEL = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")


# Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "medirag2024")

# External APIs
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
OMIM_API_KEY = os.getenv("OMIM_API_KEY", "")
FDA_API_KEY = os.getenv("FDA_API_KEY", "")

# ChromaDB
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

# App
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# PubMed base URL
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
UNIPROT_BASE_URL = "https://rest.uniprot.org/uniprotkb/search"
ALPHAFOLD_BASE_URL = "https://alphafold.ebi.ac.uk/api/prediction"
CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
FDA_BASE_URL = "https://api.fda.gov/drug/event.json"
CLINTRIALS_BASE_URL = "https://clinicaltrials.gov/api/query/full_studies"
