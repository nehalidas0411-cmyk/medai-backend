import json, re, os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from google import genai

router = APIRouter()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

SYMPTOM_SYSTEM_PROMPT = """You are a differential diagnosis assistant for educational purposes.
When given symptoms and patient context, produce a structured analysis.

Respond ONLY with valid JSON, no markdown, no code fences:
{
  "diagnoses": [
    {
      "condition": "Name of the condition",
      "likelihood": "High | Medium | Low",
      "explanation": "Why this fits the symptoms in plain language",
      "next_step": "Test, specialist, or action to confirm/rule out"
    }
  ],
  "emergency_warning": "If symptoms suggest an emergency, state it clearly. Otherwise null.",
  "general_advice": "Brief advice about symptom management",
  "disclaimer": "This is AI-generated educational content only. Not a medical diagnosis. See a doctor."
}

List 3-5 most likely diagnoses ordered from most to least likely.
ALWAYS flag emergencies: chest pain + shortness of breath = possible heart attack, etc."""

EMERGENCY_COMBOS = [
    (["chest pain", "shortness of breath"], "🚨 EMERGENCY: Chest pain with shortness of breath may indicate a heart attack. Call 112 immediately."),
    (["chest pain", "left arm"], "🚨 EMERGENCY: These symptoms may indicate a cardiac event. Call 112 immediately."),
    (["sudden severe headache", "stiff neck"], "🚨 EMERGENCY: May indicate meningitis. Seek emergency care immediately."),
    (["difficulty breathing"], "🚨 EMERGENCY: Severe breathing difficulty needs immediate attention. Call 112."),
]


class SymptomRequest(BaseModel):
    symptoms: List[str]
    age: Optional[str] = None
    sex: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[str] = None


def check_emergency(symptoms: List[str]) -> Optional[str]:
    lower = " ".join(s.lower() for s in symptoms)
    for keywords, warning in EMERGENCY_COMBOS:
        if any(k in lower for k in keywords):
            return warning
    return None


def safe_json_parse(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {
        "diagnoses": [{"condition": "Unable to parse", "likelihood": "Unknown", "explanation": raw, "next_step": "Please consult a doctor."}],
        "emergency_warning": None,
        "general_advice": "Please consult a licensed physician.",
        "disclaimer": "This is AI-generated educational content only."
    }


@router.post("/symptoms")
async def check_symptoms(req: SymptomRequest):
    if not req.symptoms:
        raise HTTPException(status_code=400, detail="At least one symptom is required.")

    emergency = check_emergency(req.symptoms)

    parts = [f"Symptoms: {', '.join(req.symptoms)}"]
    if req.age:      parts.append(f"Age: {req.age}")
    if req.sex:      parts.append(f"Biological sex: {req.sex}")
    if req.duration: parts.append(f"Duration: {req.duration}")
    if req.severity: parts.append(f"Severity (1-10): {req.severity}")

    prompt = SYMPTOM_SYSTEM_PROMPT + "\n\n" + "\n".join(parts) + "\n\nProvide differential diagnosis in the required JSON format."

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        result = safe_json_parse(response.text)
        if emergency and not result.get("emergency_warning"):
            result["emergency_warning"] = emergency
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")
