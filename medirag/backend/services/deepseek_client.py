"""
DeepSeek Reasoner client.
Streams <think> tokens (chain-of-thought) separately from the final answer.
This is NOT a chatbot — it's a one-shot oracle call with structured JSON output.
"""
import json
import logging
from typing import AsyncGenerator, Callable
from openai import AsyncOpenAI
from backend.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

SYSTEM_PROMPT = """You are MediRAG, a clinical intelligence oracle — NOT a chatbot.
You receive a complete patient profile and retrieved biomedical evidence once.
You reason deeply and output a single comprehensive structured JSON response.

You MUST respond with a valid JSON object containing these exact keys:
{
  "differential_diagnosis": [
    {
      "rank": 1,
      "condition": "condition name",
      "confidence": 0.85,
      "icd10": "code",
      "reasoning": "brief clinical reasoning",
      "key_biomarkers": ["biomarker1"],
      "evidence_sources": ["PubMed PMID 12345", "ClinVar"],
      "red_flags": ["symptom that strongly suggests this"]
    }
  ],
  "diagnostic_tests": [
    {
      "test": "test name",
      "priority": "urgent|routine|optional",
      "targets_condition": "condition name",
      "rationale": "why this test",
      "source": "PubMed|ClinVar|OMIM"
    }
  ],
  "lifestyle_recommendations": [
    {
      "category": "nutrition|sleep|activity|stress|supplements",
      "recommendation": "specific actionable advice",
      "evidence": "study or database reference",
      "priority": "high|medium|low"
    }
  ],
  "drug_review": [
    {
      "drug": "drug name",
      "risk_level": "low|moderate|high",
      "adverse_signals": ["signal1"],
      "interactions": ["drug interaction if any"],
      "faers_reports": "number or description",
      "recommendation": "continue|monitor|review with physician"
    }
  ],
  "clinical_trials": [
    {
      "nct_id": "NCT...",
      "title": "trial title",
      "relevance": "why relevant to this patient"
    }
  ],
  "knowledge_graph_highlights": [
    {
      "from_entity": "entity name",
      "relationship": "INDICATES|ASSOCIATED_WITH|TREATS",
      "to_entity": "entity name",
      "strength": "strong|moderate|weak"
    }
  ],
  "disclaimer": "This analysis is NOT a clinical diagnosis. All findings must be reviewed by a licensed medical professional before any clinical decision is made.",
  "summary": "2-3 sentence executive summary for the clinician"
}

Always include the disclaimer. Always cite evidence sources. Never fabricate PMIDs."""


async def stream_oracle_reasoning(
    patient: dict,
    context: str,
    on_thinking: Callable[[str], None] = None,
    on_tool_call: Callable[[str], None] = None,
) -> AsyncGenerator[dict, None]:
    """
    Stream DeepSeek Reasoner response.
    Yields events: {type: 'reasoning'|'answer'|'error', text: str}
    
    - reasoning events: <think> chain-of-thought tokens → shown in Reasoning Theater
    - answer events: final JSON answer → populates dashboard artifacts
    """
    symptoms = patient.get("symptoms", [])
    medications = patient.get("medications") or patient.get("current_medications", "")
    
    user_prompt = f"""
PATIENT PROFILE:
- Age: {patient.get('age', 'Unknown')}
- Sex: {patient.get('sex', 'Unknown')}
- BMI: {patient.get('bmi', 'Unknown')}
- Chief Complaint: {patient.get('chief_complaint', 'Not provided')}
- Symptoms: {', '.join(symptoms) if isinstance(symptoms, list) else symptoms}
- Duration: {patient.get('duration_days', patient.get('symptom_duration', 'Unknown'))} days
- Vitals: BP {patient.get('blood_pressure', 'N/A')}, HR {patient.get('heart_rate', 'N/A')}, Temp {patient.get('temperature', 'N/A')}
- Smoking: {patient.get('smoking', 'N/A')}, Alcohol: {patient.get('alcohol', 'N/A')}
- Current Medications: {', '.join(medications) if isinstance(medications, list) else medications or 'None'}
- Known Comorbidities: {', '.join(patient.get('comorbidities', [])) if isinstance(patient.get('comorbidities'), list) else patient.get('medical_history', 'None reported')}
- Allergies: {patient.get('allergies', 'None reported')}
- Family History: {patient.get('family_history', 'None reported')}
- Additional Context: {patient.get('extra_context', patient.get('lab_notes', 'None'))}
- Uploaded Lab Report: {patient.get('uploaded_text', 'None')}

RETRIEVED BIOMEDICAL EVIDENCE (from PubMed, UniProt, ClinVar, ChEMBL, FDA FAERS, OMIM, ClinTrials, Neo4j Graph):
{context}

Generate the comprehensive clinical intelligence JSON output now.
"""

    try:
        stream = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # very low for medical factual output
            max_tokens=8000,
            stream=True,
        )

        answer_buffer = ""
        has_started_content = False
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Stream <think> chain-of-thought tokens
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                yield {"type": "reasoning", "text": delta.reasoning_content}

            # Stream final answer tokens
            elif delta.content:
                if not has_started_content:
                    has_started_content = True
                    # Let the pipeline know we've transitioned to compiling the report
                    yield {"type": "phase", "phase": "report", "message": "Structuring clinical findings..."}
                    yield {"type": "tool_call", "tool": "generate_report", "status": "running"}

                answer_buffer += delta.content
                yield {"type": "answer_chunk", "text": delta.content}

        # Parse the complete answer as JSON
        if answer_buffer:
            try:
                # Extract JSON from possible markdown code blocks
                json_str = answer_buffer
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
                
                parsed = json.loads(json_str)
                yield {"type": "final_answer", "data": parsed}
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                # Return raw text as fallback
                yield {"type": "final_answer", "data": {"raw_text": answer_buffer, "parse_error": str(e)}}

    except Exception as e:
        logger.error(f"DeepSeek stream error: {e}")
        yield {"type": "error", "text": str(e)}


async def generate_community_summary(member_names: list[str]) -> str:
    """Quick call to summarize a Leiden community cluster (non-streaming)."""
    try:
        resp = await client.chat.completions.create(
            model="deepseek-chat",  # use cheaper model for summaries
            messages=[{
                "role": "user",
                "content": (
                    f"In one sentence, describe the medical theme connecting these conditions/entities: "
                    f"{', '.join(member_names[:10])}. Be concise and clinical."
                )
            }],
            temperature=0.3,
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Community summary error: {e}")
        return f"Cluster containing: {', '.join(member_names[:5])}"
