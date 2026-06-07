import os, json, re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

router = APIRouter()

class SymptomRequest(BaseModel):
    symptoms: List[str]
    age: str
    sex: str
    duration: str
    severity: Optional[str] = None
    additional_notes: Optional[str] = None

DISCLAIMER = ("⚠️ MEDICAL DISCLAIMER: This symptom analysis is for informational purposes only. "
               "Always consult a qualified doctor for proper diagnosis and treatment.")

PROMPT = """You are a differential diagnosis assistant. Given the patient's symptoms, respond ONLY with valid JSON:
{
  "summary": "1-2 sentence overview",
  "diagnoses": [
    {"condition": "name", "likelihood": "High/Medium/Low",
     "explanation": "why", "next_step": "what test/specialist confirms this",
     "urgency": "routine/soon/urgent/emergency"}
  ],
  "red_flags": ["symptoms needing emergency care"],
  "recommended_specialist": "who to see first",
  "general_advice": "brief self-care note",
  "questions_for_doctor": ["3-4 questions to ask"]
}"""

def safe_json(text):
    try:
        return json.loads(re.sub(r"```json\s*|\s*```", "", text).strip())
    except:
        return {"summary": text[:300], "diagnoses": [], "red_flags": [],
                "recommended_specialist": "General Physician", "general_advice": "", "questions_for_doctor": []}

@router.post("/symptoms")
async def check_symptoms(data: SymptomRequest):
    if not data.symptoms:
        raise HTTPException(400, "Please provide at least one symptom.")
    prompt = (f"{PROMPT}\n\nPatient: {data.age} year old {data.sex}\n"
              f"Symptoms: {', '.join(data.symptoms)}\nDuration: {data.duration}")
    if data.severity: prompt += f"\nSeverity (1-10): {data.severity}"
    if data.additional_notes: prompt += f"\nNotes: {data.additional_notes}"
    try:
        response = client.models.generate_content(
            model="models/gemini-1.5-flash",
            contents=prompt
        )
        result = safe_json(response.text)
    except Exception as e:
        raise HTTPException(500, f"AI error: {str(e)}")
    return {**result, "disclaimer": DISCLAIMER}
