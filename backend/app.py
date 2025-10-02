import os
import logging
import uuid
import json
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Utils (to be implemented next)
from utils.ocr import extract_text_from_pdf, extract_text_from_image, detect_file_type
from utils.classifier import get_document_type
from utils.ai_handler import answer_question, generate_summary, smart_answer

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 16 * 1024 * 1024))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# simple in-memory store for extracted text by file_id in MVP
DOCUMENT_CACHE = {}

# logging setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
logger = app.logger

@app.before_request
def _log_request():
    logger.info(f"{request.method} {request.path}")

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large"}), 413

@app.errorhandler(Exception)
def handle_error(e):
    code = getattr(e, 'code', 500)
    return jsonify({"error": str(e)}), code

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Unsupported file type"}), 400

    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    save_name = f"{file_id}{ext}"
    path = os.path.join(app.config['UPLOAD_FOLDER'], save_name)
    file.save(path)

    return jsonify({"file_id": file_id, "filename": filename})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json(force=True)
    file_id = data.get('file_id')
    if not file_id:
        return jsonify({"error": "file_id is required"}), 400

    # find file path
    path = None
    for name in os.listdir(app.config['UPLOAD_FOLDER']):
        if name.startswith(file_id):
            path = os.path.join(app.config['UPLOAD_FOLDER'], name)
            break
    if not path or not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    file_type = detect_file_type(path)
    if file_type == 'pdf':
        text = extract_text_from_pdf(path)
    elif file_type == 'image':
        text = extract_text_from_image(path)
    else:
        return jsonify({"error": "Unsupported file"}), 400

    if not text:
        return jsonify({"error": "No text extracted"}), 422

    doc_type, confidence = get_document_type(text)

    DOCUMENT_CACHE[file_id] = {
        'text': text,
        'type': doc_type,
        'confidence': confidence,
        'path': path,
        'ts': time.time()
    }

    return jsonify({
        'file_id': file_id,
        'extracted_text': text,
        'document_type': doc_type,
        'confidence': confidence
    })

@app.route('/api/query', methods=['POST'])
def query():
    data = request.get_json(force=True)
    file_id = data.get('file_id')
    question = data.get('question', '').strip()
    if not file_id or not question:
        return jsonify({"error": "file_id and question are required"}), 400

    doc = DOCUMENT_CACHE.get(file_id)
    if not doc:
        return jsonify({"error": "Analyze the document first"}), 400

    ans, score = smart_answer(doc['text'], question, doc_type=doc.get('type'))
    return jsonify({"answer": ans, "confidence": score})

@app.route('/api/summarize', methods=['POST'])
def summarize():
    data = request.get_json(force=True)
    file_id = data.get('file_id')
    summary_type = data.get('summary_type', 'general')
    if not file_id:
        return jsonify({"error": "file_id is required"}), 400

    doc = DOCUMENT_CACHE.get(file_id)
    if not doc:
        return jsonify({"error": "Analyze the document first"}), 400

    summary = generate_summary(doc['text'], summary_type, doc_type=doc.get('type'))
    return jsonify({"summary_type": summary_type, "summary": summary})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

# basic cleanup route for MVP, deletes files older than given hours (default 24)
@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    hours = int(request.json.get('hours', 24))
    cutoff = time.time() - hours * 3600
    removed = 0
    for fid, meta in list(DOCUMENT_CACHE.items()):
        if meta['ts'] < cutoff:
            try:
                if os.path.exists(meta['path']):
                    os.remove(meta['path'])
            except Exception:
                pass
            DOCUMENT_CACHE.pop(fid, None)
            removed += 1
    return jsonify({"removed": removed})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
