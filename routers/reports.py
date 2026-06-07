import json, base64, re, io, os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import google.generativeai as genai

router = APIRouter()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

SYSTEM_PROMPT = """You are an expert medical report interpreter. When given a medical image 
(X-ray, ECG, EEG, EMG, EOG, MRI, CT, ultrasound) or a medical text report (lab results, 
discharge summary, etc.), you must:

1. Explain ALL findings in simple, clear, patient-friendly language
2. List every key finding or abnormality as a separate item
3. Suggest the 2-4 most likely diagnoses based ONLY on what is in the report
4. Recommend what type of specialist or next step is appropriate
5. Note any urgent or emergency findings prominently

Respond ONLY with valid JSON, no markdown, no code fences:
{
  "explanation": "A 2-4 paragraph plain-language explanation",
  "findings": ["Finding 1", "Finding 2", "Finding 3"],
  "diagnosis": "Most likely condition or differential diagnosis list",
  "recommendation": "Who to see and what to do next",
  "urgency": "routine | soon | urgent | emergency",
  "disclaimer": "This is AI-generated analysis for educational purposes only. Not a medical diagnosis. Always consult a qualified physician."
}"""


def extract_pdf_text(content: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip() if text.strip() else "[PDF appears to be scanned/image-only — no text extracted]"
    except Exception as e:
        return f"[Could not extract PDF text: {e}]"


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
        "explanation": raw,
        "findings": ["Could not parse structured findings — see explanation above."],
        "diagnosis": "Unable to determine — please consult a doctor.",
        "recommendation": "Please see a qualified medical professional.",
        "urgency": "routine",
        "disclaimer": "This is AI-generated analysis for educational purposes only."
    }


@router.post("/analyze")
async def analyze_report(
    file: UploadFile = File(...),
    age: Optional[str] = Form(None),
    sex: Optional[str] = Form(None),
    report_type: Optional[str] = Form(None),
    known_conditions: Optional[str] = Form(None),
):
    allowed_types = {
        "image/jpeg", "image/jpg", "image/png", "image/webp",
        "image/gif", "application/pdf"
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 15 MB.")

    context_parts = []
    if age:              context_parts.append(f"Patient age: {age}")
    if sex:              context_parts.append(f"Patient biological sex: {sex}")
    if report_type:      context_parts.append(f"Report type: {report_type}")
    if known_conditions: context_parts.append(f"Known conditions/medications: {known_conditions}")
    context = "\n".join(context_parts)

    try:
        if file.content_type == "application/pdf":
            pdf_text = extract_pdf_text(content)
            prompt = f"{SYSTEM_PROMPT}\n\n{context}\n\nMedical Report Text:\n{pdf_text}" if context else f"{SYSTEM_PROMPT}\n\nMedical Report Text:\n{pdf_text}"
            response = model.generate_content(prompt)
        else:
            import PIL.Image
            img = PIL.Image.open(io.BytesIO(content))
            prompt_text = SYSTEM_PROMPT
            if context:
                prompt_text += f"\n\nPatient context:\n{context}"
            prompt_text += "\n\nAnalyze this medical image and provide findings in the required JSON format."
            response = model.generate_content([prompt_text, img])

        raw = response.text
        result = safe_json_parse(raw)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")
