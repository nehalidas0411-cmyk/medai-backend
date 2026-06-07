# MedAI Diagnostics — Setup Guide

A free, open-source medical report analysis platform using Claude AI.

---

## What You're Getting

- **Report Analysis**: Upload X-ray, ECG, EEG, EMG, EOG, lab PDFs → get plain-language explanation
- **Symptom Checker**: Enter symptoms → differential diagnosis
- **Nearby Facilities**: Find hospitals, clinics, labs near you (OpenStreetMap, no API key needed)
- **Full history**: Stored only in your browser — nothing goes to a server

---

## Step 1: Get Your Free Anthropic API Key

1. Go to https://console.anthropic.com
2. Sign up for a free account
3. Go to "API Keys" → click "Create Key"
4. Copy the key (starts with `sk-ant-...`)

The free tier gives you enough credits to test extensively.

---

## Step 2: Set Up the Backend

### Prerequisites
- Python 3.10 or higher
- pip

### Install

```bash
# Clone / download this folder, then:
cd medai-backend

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configure

```bash
# Create your .env file
copy .env.example .env      # Windows
cp .env.example .env        # Mac/Linux

# Open .env and paste your Anthropic API key:
# ANTHROPIC_API_KEY=sk-ant-...your-key-here
```

### Run the backend

```bash
# Make sure your venv is active, then:
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

Test it: open http://localhost:8000/health in your browser → should show `{"status":"ok"}`

---

## Step 3: Set Up the Frontend

The frontend is a single HTML file — no build step needed.

1. Open `medai-frontend.html` in your browser (double-click it)
2. That's it. It connects to your backend at `http://localhost:8000`

---

## Step 4: Test It End-to-End

1. Backend running at http://localhost:8000
2. Frontend open in browser
3. Go to "Report Analysis" → upload any medical image or PDF
4. Go to "Symptom Checker" → add symptoms → click Find Diagnoses
5. Go to "Nearby Facilities" → click "Use My Current Location"

---

## Free Deployment (Optional)

### Backend: Render.com (free tier)

1. Push your `medai-backend/` folder to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variable: `ANTHROPIC_API_KEY` = your key
7. Deploy → copy the URL (e.g. `https://medai-backend.onrender.com`)

### Frontend: GitHub Pages (free)

1. Create a GitHub repo
2. Upload `medai-frontend.html` as `index.html`
3. In `index.html`, change `const BACKEND_URL = 'http://localhost:8000'`
   to `const BACKEND_URL = 'https://your-render-url.onrender.com'`
4. Enable GitHub Pages in repo Settings → Pages → Deploy from main branch

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `GET /health` | GET | Health check |
| `POST /api/analyze` | POST (multipart) | Analyze medical report (image or PDF) |
| `POST /api/symptoms` | POST (JSON) | Symptom-to-diagnosis |
| `GET /api/facilities?lat=&lng=&radius=` | GET | Nearby medical facilities |

### POST /api/analyze

Form fields:
- `file` (required): image (JPEG/PNG/WebP) or PDF
- `age` (optional): patient age
- `sex` (optional): biological sex
- `report_type` (optional): e.g. "Chest X-Ray"
- `known_conditions` (optional): existing conditions / medications

Response:
```json
{
  "explanation": "Plain language explanation...",
  "findings": ["Finding 1", "Finding 2"],
  "diagnosis": "Possible diagnosis...",
  "recommendation": "See a cardiologist...",
  "urgency": "routine | soon | urgent | emergency",
  "disclaimer": "..."
}
```

### POST /api/symptoms

```json
{
  "symptoms": ["headache", "fever", "nausea"],
  "age": "28",
  "sex": "Female",
  "duration": "1–3 days",
  "severity": "6"
}
```

Response:
```json
{
  "diagnoses": [
    {
      "condition": "Migraine",
      "likelihood": "High",
      "explanation": "...",
      "next_step": "..."
    }
  ],
  "emergency_warning": null,
  "general_advice": "...",
  "disclaimer": "..."
}
```

---

## Do You Need to Train a Model?

No — for this version, Claude handles everything:

| Report Type | How it's handled |
|---|---|
| X-Ray, CT, MRI images | Claude vision (claude-haiku-4-5) |
| ECG, EEG, EMG, EOG graphs | Claude vision |
| Lab report PDFs | Text extracted → Claude text |
| Discharge summaries | Text extracted → Claude text |

For a future research-grade version, you could fine-tune on:
- NIH ChestX-ray14 (chest X-ray classification)
- PhysioNet MIT-BIH (ECG arrhythmia)
- Temple University EEG Corpus
- MIMIC-III (clinical notes)

But that requires GPU resources and is not needed for this working platform.

---

## Legal & Safety

- Always display the medical disclaimer on every result
- This platform is for educational purposes only
- Not approved by any medical regulatory body
- Complies with India's DPDP Act 2023 (no personal data stored)
- Users must be reminded to consult a licensed physician

---

## Troubleshooting

**"Error: Failed to fetch"** — Backend isn't running. Start it with `uvicorn main:app --reload`

**"AI service error: 401"** — Check your ANTHROPIC_API_KEY in the `.env` file

**"File too large"** — File must be under 15 MB

**"Could not extract PDF text"** — The PDF may be a scanned image. Save it as an image (PNG/JPG) and upload that instead.

**Backend runs but CORS error in browser** — The backend allows all origins by default. If this persists, check that you're connecting to the right port (8000).
