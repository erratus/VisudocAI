# VisudocAI

Full-stack AI-powered document analysis web application.

## Tech Stack
- Backend: Python Flask, Tesseract OCR (pytesseract), pdf2image, Pillow, HuggingFace Inference API
- Frontend: React 18, Axios, react-dropzone, Webpack

## Prerequisites (Windows)
- Python 3.10+ (recommended)
- Node.js 18+
- Tesseract OCR installed (e.g., `C:\\Program Files\\Tesseract-OCR\\tesseract.exe`)
- Poppler for Windows (download zip, e.g., `C:\\tools\\poppler-24.02.0\\Library\\bin`)
- HuggingFace API key (free tier)

## Setup

### 1) Backend
```
cd visudocai\\backend
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env and set HUGGINGFACE_API_KEY
# Optionally set TESSERACT_CMD and POPPLER_PATH if not on PATH
```

Run the API:
```
venv\\Scripts\\activate
python app.py
```
This starts on http://localhost:5000

### 2) Frontend
```
cd visudocai\\frontend
npm install
npm start
```
The dev server proxies /api to http://localhost:5000 and opens http://localhost:3000

## Notes
- Supported uploads: PDF, PNG, JPG (max 16MB by default)
- First HuggingFace call may be slow (model cold start). We retry automatically.
- OCR quality depends on input quality; scanning at 300 DPI recommended.

## Troubleshooting
- Tesseract not found: set TESSERACT_CMD in backend/.env
- PDF to image fails on Windows: set POPPLER_PATH to the `bin` folder of Poppler
- CORS issues: dev server proxies /api; ensure backend runs on 5000

## Scripts
- Backend: `python app.py`
- Frontend: `npm start`

## Security
This MVP stores files and extracted text in-memory and on local disk for development only. Do not use in production as-is.
