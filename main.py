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