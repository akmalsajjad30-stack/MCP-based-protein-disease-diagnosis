# VeriDX — Clinical Intelligence Oracle

> **MCP-based protein-disease diagnosis system** powered by Graph RAG, DeepSeek Reasoner, and seven biomedical databases.

VeriDX is an agentic medical assistant that takes a patient's symptoms, lab results, medications, and clinical documents, then orchestrates a multi-step reasoning pipeline to produce a ranked differential diagnosis, drug-safety assessment, lifestyle recommendations, and a downloadable PDF clinical report.

> ⚠️ **Disclaimer:** VeriDX is a research and decision-support tool. It is **not a substitute for professional medical advice, diagnosis, or treatment.** Always consult a qualified healthcare provider.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [MCP Server](#mcp-server)
- [Database Integrations](#database-integrations)
- [Knowledge Graph Schema](#knowledge-graph-schema)
- [Frontend UI](#frontend-ui)
- [Contributing](#contributing)

---

## Overview

VeriDX implements a **5-phase clinical reasoning pipeline**:

```
Patient Input
     │
     ▼
Phase 1 ─── Parallel biomedical database queries
            (PubMed · UniProt · ClinVar · ChEMBL · FDA FAERS · OMIM · ClinicalTrials.gov)
     │
     ▼
Phase 2 ─── Knowledge Graph construction (Neo4j / in-memory fallback)
            Symptom → Condition → Gene → Protein → Drug nodes & relationships
     │
     ▼
Phase 3 ─── Leiden community detection (disease cluster discovery)
            LLM-generated summaries per community cluster
     │
     ▼
Phase 4 ─── Hybrid retrieval
            Graph traversal (Neo4j) + semantic vector search (ChromaDB)
     │
     ▼
Phase 5 ─── DeepSeek Reasoner (streaming chain-of-thought)
            → Differential diagnosis · Drug safety · Lifestyle plan · PDF report
```

All pipeline events are streamed in real-time to the frontend via **WebSocket**, so clinicians see reasoning as it happens.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vite + React)               │
│  IntakeForm → ReasoningTheater → ResultsDashboard            │
│  KnowledgeGraph (D3.js) · Charts (Recharts/Chart.js)         │
└───────────────────────┬─────────────────────────────────────┘
                        │  REST + WebSocket
┌───────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend (Python)                   │
│                                                              │
│  POST /oracle/start ─ creates session & de-identifies data   │
│  WS   /ws/{session} ─ streams oracle pipeline events         │
│  GET  /report/{sid} ─ returns generated PDF report           │
│  GET  /health       ─ liveness check                         │
│  /mcp               ─ MCP server (SSE transport)             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │               Oracle Engine                            │  │
│  │  Biomedical DB Fetch → Graph Build → Community Detect  │  │
│  │  → Hybrid Retrieve → DeepSeek Reasoner Stream          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Neo4j Graph │  │  ChromaDB    │  │  MCP Server      │   │
│  │  (Knowledge  │  │  (Vector     │  │  (10 tools,      │   │
│  │   Graph)     │  │   Store)     │  │   6 resources,   │   │
│  └──────────────┘  └──────────────┘  │   4 prompts)     │   │
│                                       └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

### Clinical Reasoning
- **Ranked differential diagnosis** with ICD-10 codes and confidence scores
- **Supporting biomarkers & symptom mapping** for each candidate condition
- **Evidence-backed citations** from PubMed, ClinVar, and OMIM
- **Recommended confirmatory tests** for each diagnosis
- **Streaming chain-of-thought** — watch the AI reason step by step

### Drug Safety
- Cross-checks patient medications against **ChEMBL** drug profiles
- Detects **FDA FAERS adverse event signals**
- Flags high-risk drug-drug interactions
- Classifies each medication as `continue`, `monitor`, or `review with physician`

### Knowledge Graph
- Builds a per-session biomedical **knowledge graph** in Neo4j
- Nodes: `Symptom · Condition · Gene · Protein · Drug · Biomarker · ClinicalTrial · Community`
- Edges: `INDICATES · ASSOCIATED_WITH · ENCODES · TREATS · TARGETS · CONTRAINDICATED_WITH · ELEVATED_IN · BELONGS_TO · STUDIES`
- **Leiden community detection** groups related diseases into clusters with LLM-generated summaries
- Interactive **D3.js graph visualization** in the UI

### Document Ingestion
- Upload **PDF, DOCX, or plain-text** clinical documents (lab reports, discharge summaries)
- Automatic **PII de-identification** via Presidio before any LLM processing
- Extracted text fed into both the knowledge graph and the vector store

### Report Generation
- One-click **downloadable PDF** clinical report with diagnosis, recommendations, and sources
- Structured for **clinician handoff** use

### MCP Protocol Support
- Full **Model Context Protocol** (MCP) server exposed at `/mcp`
- Enables any MCP-compatible AI client (e.g. Claude Desktop, custom agents) to call VeriDX tools directly

---

## Tech Stack

### Backend
| Component | Technology |
|---|---|
| API Framework | FastAPI 0.115 + Uvicorn |
| AI / Reasoning | DeepSeek Reasoner (`deepseek-reasoner` / `deepseek-chat`) via OpenAI SDK |
| Knowledge Graph | Neo4j 5.27 (with in-memory fallback) |
| Vector Store | ChromaDB 0.6 |
| Embeddings | `sentence-transformers` (local, offline-capable) |
| Community Detection | Leiden algorithm (`leidenalg` + `igraph`) with NetworkX |
| Graph Orchestration | NetworkX 3.4 |
| Biomedical NLP | spaCy 3.8 + `en_core_web_sm` |
| PII Anonymization | Microsoft Presidio (Analyzer + Anonymizer) |
| MCP Server | FastMCP (`mcp[cli]` 1.9.2) |
| Orchestration | LangChain 0.3 |
| File Parsing | PyMuPDF (PDF), python-docx (DOCX) |
| Report Generation | ReportLab |
| Security | `cryptography` 44 |
| HTTP | `httpx`, `aiohttp`, `requests` |

### Frontend
| Component | Technology |
|---|---|
| Framework | React 19 + Vite 8 |
| Routing | React Router DOM v7 |
| Animations | Framer Motion |
| Knowledge Graph Viz | D3.js v7 |
| Charts | Recharts + Chart.js / react-chartjs-2 |
| Icons | Lucide React |
| HTTP Client | Axios |

---

## Project Structure

```
AI Project/
├── README.md
└── veridx/
    ├── .env                     # your environment variables (gitignored)
    ├── .env.example             # template — copy to .env and fill in keys
    ├── requirements.txt         # Python dependencies
    ├── start.ps1                # one-click startup script (Windows PowerShell)
    │
    ├── backend/
    │   ├── main.py              # FastAPI app — routes & WebSocket endpoint
    │   ├── config.py            # environment variable loading
    │   │
    │   ├── databases/           # biomedical database connectors
    │   │   ├── pubmed.py        # PubMed / NCBI E-utilities
    │   │   ├── uniprot.py       # UniProt REST + AlphaFold
    │   │   ├── clinvar.py       # ClinVar (NCBI)
    │   │   ├── chembl.py        # ChEMBL drug data
    │   │   ├── fda_faers.py     # FDA FAERS adverse events
    │   │   ├── omim_clintrials.py  # OMIM + ClinicalTrials.gov
    │   │   └── alphafold.py     # AlphaFold protein structure
    │   │
    │   ├── graph_rag/           # Graph RAG layer
    │   │   ├── neo4j_client.py  # Neo4j driver, schema, queries
    │   │   ├── graph_builder.py # builds graph from DB results
    │   │   ├── community_detector.py  # Leiden community detection
    │   │   └── hybrid_retriever.py    # graph + vector hybrid search
    │   │
    │   ├── mcp_server/
    │   │   └── server.py        # FastMCP server (tools, resources, prompts)
    │   │
    │   ├── services/
    │   │   ├── oracle_engine.py # main 5-phase pipeline orchestrator
    │   │   ├── deepseek_client.py  # DeepSeek streaming client
    │   │   ├── file_parser.py   # PDF/DOCX/text extraction
    │   │   ├── report_builder.py   # PDF report generation
    │   │   └── security.py      # Presidio PII de-identification
    │   │
    │   └── vector_store/
    │       └── chroma_store.py  # ChromaDB document store
    │
    ├── frontend/
    │   ├── index.html
    │   ├── package.json
    │   ├── vite.config.js
    │   └── src/
    │       ├── main.jsx
    │       ├── App.jsx              # routing & layout
    │       ├── IntakeForm.jsx       # patient data entry UI
    │       ├── ReasoningTheater.jsx # live streaming reasoning view
    │       ├── ResultsDashboard.jsx # diagnosis results & charts
    │       ├── KnowledgeGraph.jsx   # interactive D3 graph
    │       ├── App.css
    │       └── index.css
    │
    ├── chroma_data/             # ChromaDB persistence directory
    └── reports/                 # generated PDF reports (gitignored)
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | >= 3.10 | Conda env `medirag` recommended |
| Node.js | >= 18 | For the React frontend |
| Neo4j Desktop | >= 5.x | Free; create a local database on port `7687` |
| Conda (Anaconda / Miniconda) | any | Optional but recommended |
| DeepSeek API Key | — | Required for AI analysis; get one at [platform.deepseek.com](https://platform.deepseek.com) |

**Optional API keys** (free tiers available):
- **NCBI API key** — increases PubMed/ClinVar rate limits ([register here](https://www.ncbi.nlm.nih.gov/account/))
- **OMIM API key** — required for OMIM genetic disease lookups ([register here](https://omim.org/api))
- **FDA API key** — increases FAERS rate limits

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/akmalsajjad30-stack/MCP-based-protein-disease-diagnosis.git
cd "MCP-based-protein-disease-diagnosis"
```

### 2. Create the Python Environment

```bash
conda create -n medirag python=3.11 -y
conda activate medirag
cd veridx
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Install Frontend Dependencies

```bash
cd veridx/frontend
npm install
```

### 4. Set Up Neo4j

1. Download and install [Neo4j Desktop](https://neo4j.com/download/).
2. Create a new **local DBMS** with:
   - **URI:** `bolt://localhost:7687`
   - **Username:** `neo4j`
   - **Password:** `medirag2024` *(or your own — update `.env` accordingly)*
3. Start the database before launching VeriDX.

### 5. Configure Environment Variables

```bash
cp veridx/.env.example veridx/.env
```

Then edit `veridx/.env` and fill in your keys (see [Configuration](#configuration)).

---

## Configuration

All settings live in `veridx/.env`. Copy from `.env.example`:

```env
# ── REQUIRED ────────────────────────────────────────────
DEEPSEEK_API_KEY=sk-...           # DeepSeek API key

# ── NEO4J ───────────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=medirag2024

# ── OPTIONAL BIOMEDICAL APIS ────────────────────────────
NCBI_API_KEY=                     # increases PubMed/ClinVar rate limits
OMIM_API_KEY=                     # required for OMIM lookups
FDA_API_KEY=                      # increases FDA FAERS rate limits

# ── APP ─────────────────────────────────────────────────
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# ── CHROMADB ────────────────────────────────────────────
CHROMA_PERSIST_DIR=./chroma_data
```

> **Note:** If Neo4j is not running, the backend falls back to an **in-memory graph store** automatically — the system degrades gracefully.

---

## Running the Application

### Option A — One-Click (Windows, Recommended)

From the `veridx/` directory in PowerShell:

```powershell
.\start.ps1
```

The script will:
1. Detect your `medirag` conda environment automatically
2. Install/verify Python dependencies if needed
3. Start the FastAPI backend on **http://localhost:8000**
4. Start the Vite frontend on **http://localhost:5173**
5. Verify backend health and print status

### Option B — Manual

**Backend:**
```bash
cd veridx
conda activate medirag
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend** (in a separate terminal):
```bash
cd veridx/frontend
npm run dev
```

| Service | URL |
|---|---|
| Frontend UI | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| MCP Server | http://localhost:8000/mcp |

---

## API Reference

### `POST /oracle/start`

Start a new oracle analysis session. Accepts `multipart/form-data`.

| Field | Type | Required | Description |
|---|---|---|---|
| `patient_data` | JSON string | Yes | Patient profile (see below) |
| `file` | File upload | No | PDF / DOCX / TXT clinical document |

**Patient data fields:**

```json
{
  "age": 45,
  "sex": "Female",
  "bmi": 28.5,
  "chief_complaint": "Fatigue and excessive thirst for 3 months",
  "symptoms": ["fatigue", "polyuria", "polydipsia", "blurred vision"],
  "medications": ["metformin", "lisinopril"],
  "comorbidities": ["hypertension"],
  "family_history": "Father had Type 2 diabetes",
  "lab_notes": "HbA1c 7.2%, Fasting glucose 142 mg/dL",
  "blood_pressure": "138/88",
  "heart_rate": 82,
  "temperature": 98.6,
  "allergies": "Penicillin",
  "extra_context": ""
}
```

**Response:**
```json
{ "session_id": "uuid-string" }
```

---

### `WS /ws/{session_id}`

WebSocket endpoint. Connect after `/oracle/start` to receive real-time pipeline events:

| Event type | Payload | Description |
|---|---|---|
| `phase` | `{phase, message}` | Pipeline phase transition |
| `tool_call` | `{tool, status}` | Individual tool running / done / error |
| `reasoning` | `{text}` | DeepSeek chain-of-thought tokens |
| `answer_chunk` | `{text}` | Partial structured answer tokens |
| `final_answer` | `{data}` | Complete structured diagnostic report |
| `graph_data` | `{data}` | Neo4j subgraph (nodes + edges) for visualization |
| `communities` | `{data}` | Leiden community clusters |
| `error` | `{text}` | Error message |

---

### `GET /report/{session_id}`

Download a **PDF clinical report** for a completed session.

**Response:** `application/pdf` — `VeriDX_Report.pdf`

---

### `GET /health`

```json
{ "status": "ok", "service": "VeriDX Oracle v3.0" }
```

---

## MCP Server

VeriDX exposes a full **Model Context Protocol** server at `/mcp` (SSE transport via FastMCP). Any MCP-compatible client can call VeriDX tools directly.

### Tools (10)

| Tool | Description |
|---|---|
| `search_pubmed` | Search PubMed for peer-reviewed abstracts |
| `lookup_protein` | Look up protein function & disease associations from UniProt + AlphaFold |
| `search_clinvar` | Retrieve genetic variant-disease associations from ClinVar |
| `check_drug_interactions` | Check ChEMBL drug info + FDA FAERS adverse event signals |
| `get_adverse_events` | Retrieve FDA FAERS adverse event reports for a specific drug |
| `find_clinical_trials` | Find active recruiting clinical trials for a condition |
| `query_knowledge_graph` | Traverse the Neo4j medical knowledge graph |
| `get_condition_communities` | Get Leiden community clusters from the knowledge graph |
| `get_lifestyle_recommendations` | Evidence-based lifestyle recommendations from PubMed |
| `search_omim` | Search OMIM genetic disease catalog |
| `diagnose_patient` | **Full pipeline** — runs the complete VeriDX oracle for a patient |

### Resources (6)

| Resource URI | Description |
|---|---|
| `patient://current` | Active patient profile context |
| `graph://schema` | Knowledge graph node/edge schema |
| `drugs://chembl-index` | ChEMBL drug lookup capabilities |
| `biomarkers://reference-ranges` | Standard lab reference ranges |
| `communities://condition-clusters` | Leiden community detection results |
| `ontology://umls-map` | UMLS concept normalization info |

### Prompt Templates (4)

| Prompt | Description |
|---|---|
| `differential_diagnosis` | Ranked differential diagnosis generation |
| `lifestyle_recommendations` | Evidence-based lifestyle plan |
| `drug_safety_review` | Medication safety and adverse event review |
| `patient_summary` | Concise clinical handoff summary |

---

## Database Integrations

VeriDX queries **7 biomedical databases** in parallel during each analysis:

| Database | Data Retrieved | API |
|---|---|---|
| **PubMed / NCBI** | Peer-reviewed abstracts | NCBI E-utilities |
| **UniProt** | Protein function, disease associations | UniProt REST + AlphaFold |
| **ClinVar** | Genetic variant-disease associations | NCBI ClinVar API |
| **ChEMBL** | Drug mechanisms, targets, indications | ChEMBL REST API |
| **FDA FAERS** | Adverse event reports | openFDA API |
| **OMIM** | Genetic disease catalog | OMIM API *(requires key)* |
| **ClinicalTrials.gov** | Active recruiting trials | ClinicalTrials REST API |

All database queries run **concurrently** using `asyncio` for maximum speed.

---

## Knowledge Graph Schema

The Neo4j medical knowledge graph uses the following schema:

### Node Labels

| Label | Key Properties | Description |
|---|---|---|
| `Symptom` | `name` | Clinical symptoms |
| `Condition` | `name`, `icd10` | Diseases and conditions |
| `Gene` | `name`, `gene_id` | Human genes |
| `Protein` | `name`, `uniprot_id` | Proteins from UniProt |
| `Drug` | `name`, `chembl_id` | Drugs and compounds |
| `Biomarker` | `name` | Lab values and biomarkers |
| `ClinicalTrial` | `nct_id`, `title` | Clinical trials |
| `Community` | `community_id`, `summary` | Leiden-detected disease clusters |

### Relationship Types

| Relationship | From → To | Description |
|---|---|---|
| `INDICATES` | Symptom → Condition | Symptom suggests condition |
| `ASSOCIATED_WITH` | Symptom → Condition | Epidemiological association |
| `ENCODES` | Gene → Protein | Gene encodes protein |
| `TREATS` | Drug → Condition | Drug treats condition |
| `TARGETS` | Drug → Protein | Drug targets protein |
| `CONTRAINDICATED_WITH` | Drug → Condition | Contraindication |
| `ELEVATED_IN` | Biomarker → Condition | Biomarker elevated in condition |
| `BELONGS_TO` | Any → Community | Node belongs to Leiden community |
| `STUDIES` | ClinicalTrial → Condition | Trial studies condition |

---

## Frontend UI

The React frontend has four main views:

| Component | Description |
|---|---|
| **Intake Form** | Patient data entry — demographics, symptoms, medications, comorbidities, file upload |
| **Reasoning Theater** | Live streaming view — watch the AI reason through the problem with real-time tool-call status indicators |
| **Results Dashboard** | Final structured output — differential diagnosis cards, drug safety table, lifestyle recommendations, biomarker charts |
| **Knowledge Graph** | Interactive D3.js force-directed graph of the constructed medical knowledge graph with Leiden community overlays |

---

## Medical Disclaimer

> ⚠️ **This project is intended for research and educational purposes only.**
>
> VeriDX is a prototype decision-support system. It is **not a substitute for professional medical diagnosis, clinical judgment, or treatment.** All output must be reviewed by a licensed healthcare professional before any clinical decision is made.
>
> - VeriDX has **not been clinically validated**.
> - VeriDX is **not FDA-approved**.
> - VeriDX is **not intended for clinical deployment**.
> - All confidence scores are model estimates, not clinically measured accuracy metrics.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

### Development Notes
- Backend runs with `--reload` in development — file changes auto-restart.
- The backend degrades gracefully if Neo4j is offline (in-memory graph fallback).
- The frontend can run in **demo mode** without a backend (no API key needed).
- All patient data is **de-identified** before reaching any external LLM.

---

## Contributors

Developed at **Riphah International University, Lahore** by:

- **Muhammad Musa** — [GitHub](https://github.com/akmalsajjad30-stack)
- **Paiman Ejaz** — *(add GitHub profile)*
- **Shaheer bin Shahzad** — *(add GitHub profile)*

---

## Citation

If you use VeriDX in your research, please cite:

```
@misc{veridx2026,
  title  = {VeriDX: MCP-Integrated Graph RAG Framework for Differential Diagnosis},
  author = {[Author names]},
  year   = {2026},
  url    = {https://github.com/akmalsajjad30-stack/MCP-based-protein-disease-diagnosis}
}
```

---

## Copyright

Copyright © 2026 Muhammad Musa, Paiman Ejaz, Shaheer bin Shahzad.  
Riphah International University, Lahore. All Rights Reserved.

This software and its source code are proprietary. The source code is made publicly visible for
reference and academic review purposes only.

**No permission is granted to:**
- Copy, modify, or distribute this software
- Use this software for commercial purposes
- Sublicense or sell copies of this software

All rights are reserved by the original authors.

---


## Limitations

- **Not clinically validated** — output reflects retrieved biomedical literature, not measured diagnostic accuracy.
- **API rate limits** — NCBI, FDA FAERS, ChEMBL, and ClinicalTrials.gov impose rate limits; high-volume use may require API keys.
- **Neo4j optional** — Neo4j provides the best graph performance; the in-memory fallback has reduced graph traversal fidelity.
- **DeepSeek dependency** — all reasoning requires an active DeepSeek API connection; the system cannot produce output offline.
- **OMIM requires a key** — OMIM genetic disease lookups will be skipped without a registered API key.
- **Embeddings require local model** — `sentence-transformers` downloads ~400 MB of model weights on first run.

---

<p align="center">
  Built for clinical decision support research
</p>

