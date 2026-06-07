from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import reports, symptoms, facilities

app = FastAPI(title="MedAI Diagnostics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router,    prefix="/api", tags=["Report Analysis"])
app.include_router(symptoms.router,   prefix="/api", tags=["Symptom Checker"])
app.include_router(facilities.router, prefix="/api", tags=["Facilities"])

@app.get("/")
def root():
    return {"status": "MedAI backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug/models")
async def list_models():
    from google import genai
    import os
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    models = client.models.list()
    return {"models": [m.name for m in models]}
