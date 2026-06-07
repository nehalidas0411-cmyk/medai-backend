import os, base64, json, re, io
from fastapi import APIRouter, UploadFile, File, HTTPException
from pypdf import PdfReader
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

router = APIRouter()

SYSTEM_PROMPT = """You are MedAI, a medical report interpreter. Analyze the given medical report or image and respond ONLY with valid JSON, no markdown, no extra text:
{
  "report_type": "e.g. Chest X-Ray / ECG / Blood CBC",
  "report_category": "radiology/cardiology/neurology/pathology/hematology/other",
  "explanation": "3-5 sentences in plain patient-friendly language",
  "findings": [{"item": "name", "value": "value", "status": "normal/abnormal/borderline", "note": "brief explanation"}],
  "diagnosis": [{"condition": "name", "likelihood": "possible/likely/highly likely", "explanation": "1-2 sentences"}],
  "recommendation": "which specialist to see and urgency",
  "urgency": "routine/soon/urgent/emergency",
  "confidence": "low/medium/high"
}"""

DISCLAIMER = ("⚠️ MEDICAL DISCLAIMER: This AI analysis is for informational purposes only and does NOT "
               "constitute medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional.")

def extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(p.extract_text() or "" for p in reader.pages)[:8000]
    except:
        return "[Could not extract PDF text]"

def safe_json(text: str) -> dict:
    try:
        return json.loads(re.sub(r"```json\s*|\s*```", "", text).strip())
    except:
        return {"report_type": "Unknown", "report_category": "other",
                "explanation": text[:400], "findings": [], "diagnosis": [],
                "recommendation": "Please consult a doctor.", "urgency": "routine", "confidence": "low"}

@router.post("/analyze")
async def analyze_report(
    file: UploadFile = File(...),
    age: str = None, sex: str = None,
    report_type: str = None, known_conditions: str = None
):
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 15MB)")

    extra = ""
    if age: extra += f"\nPatient age: {age}"
    if sex: extra += f"\nBiological sex: {sex}"
    if known_conditions: extra += f"\nKnown conditions/medications: {known_conditions}"

    is_image = file.content_type and file.content_type.startswith("image/")
    is_pdf = (file.content_type == "application/pdf") or (file.filename or "").lower().endswith(".pdf")

    try:
        if is_image:
            img_part = types.Part.from_bytes(data=content, mime_type=file.content_type)
            response = client.models.generate_content(
                model="models/gemini-2.0-flash",
                contents=[SYSTEM_PROMPT + extra, img_part]
            )
        elif is_pdf:
            text = extract_pdf_text(content)
            response = client.models.generate_content(
                model="models/gemini-2.0-flash",
                contents=f"{SYSTEM_PROMPT}{extra}\n\nReport text:\n{text}"
            )
        else:
            try:
                text = content.decode("utf-8")[:8000]
            except:
                text = "[Binary file]"
            response = client.models.generate_content(
                model="models/gemini-2.0-flash",
                contents=f"{SYSTEM_PROMPT}{extra}\n\nReport:\n{text}"
            )

        result = safe_json(response.text)
    except Exception as e:
        raise HTTPException(500, f"AI error: {str(e)}")

    return {**result, "disclaimer": DISCLAIMER}
