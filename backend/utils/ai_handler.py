import os
import time
import requests
from typing import Optional

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OR_MODEL_QA = os.getenv('OR_MODEL_QA', 'openrouter/auto')
OR_MODEL_SUMMARY = os.getenv('OR_MODEL_SUMMARY', 'openrouter/auto')
OR_REFERER = os.getenv('OR_REFERER', '')
OR_TITLE = os.getenv('OR_TITLE', 'VisuDocAI')


def _or_headers():
    if not OPENROUTER_API_KEY:
        raise RuntimeError('OPENROUTER_API_KEY not configured')
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json'
    }
    if OR_REFERER:
        headers['HTTP-Referer'] = OR_REFERER
    if OR_TITLE:
        headers['X-Title'] = OR_TITLE
    return headers


def _or_chat(model: str, messages, max_tokens: int = 256, temperature: float = 0.2):
    url = 'https://openrouter.ai/api/v1/chat/completions'
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens
    }
    r = requests.post(url, headers=_or_headers(), json=payload, timeout=90)
    r.raise_for_status()
    data = r.json()
    if data.get('choices'):
        return data['choices'][0]['message'].get('content', '')
    return ''


def answer_question(context: str, question: str):
    # Route to OpenRouter LLM QA
    return answer_question_llm(context, question)


def answer_question_llm(context: str, question: str):
    messages = [
        {"role": "system", "content": "You answer strictly from the provided document. If the answer is not explicitly present, reply exactly: Not found."},
        {"role": "user", "content": f"Question: {question}\n\nDocument:\n{context[:6000]}\n\nAnswer:"}
    ]
    text = _or_chat(OR_MODEL_QA, messages, max_tokens=128, temperature=0.1)
    ans = (text or '').strip().split('\n')[0].strip()
    if not ans:
        return '', 0.0
    conf = 0.1 if ans.lower().startswith('not found') else 0.85
    return ans, conf


def _summarize_chunk(text: str, max_len=130, min_len=30):
    messages = [
        {"role": "system", "content": f"Summarize the document in {min_len}-{max_len} words."},
        {"role": "user", "content": text}
    ]
    return _or_chat(OR_MODEL_SUMMARY, messages, max_tokens=200, temperature=0.2)


def generate_summary(text: str, summary_type: str = 'general', doc_type: Optional[str] = None):
    text = text.strip()
    if not text:
        return ''

    # Always use OpenRouter LLM for summaries
    if summary_type == 'brief':
        instructions = "Provide a brief 2-3 sentence summary focused on the most important information."
    elif summary_type == 'key_points':
        instructions = "Provide 5-10 concise bullet points covering the most important facts only."
    elif summary_type == 'structured':
        instructions = (
            "Provide a structured summary. If it's an invoice or receipt, include Date, Total, Vendor. "
            "If it's a resume, include Name, Email, Phone. Then add a short summary and 5 bullet key points."
        )
    else:
        instructions = "Provide a clear paragraph summary."

    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": f"Document:\n{text[:8000]}\n\nSummary:"}
    ]
    return _or_chat(OR_MODEL_SUMMARY, messages, max_tokens=400, temperature=0.2).strip()

    # determine style
    if summary_type == 'brief':
        max_len, min_len = 60, 15
    elif summary_type == 'key_points':
        # try to get a longer summary; we'll format as bullets
        max_len, min_len = 200, 60
    elif summary_type == 'structured':
        max_len, min_len = 160, 50
    else:
        max_len, min_len = 130, 30

    # basic chunking for very long docs
    chunks = []
    words = text.split()
    chunk_size = 700 if summary_type != 'brief' else 400
    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    summaries = [_summarize_chunk(chunk, max_len, min_len) for chunk in chunks[:3]]  # cap for MVP
    combined = '\n'.join(s for s in summaries if s)

    if summary_type == 'key_points':
        # turn sentences into bullets and dedupe
        seen = set()
        bullets = []
        sentences = [s.strip() for s in combined.replace('\n', ' ').split('.') if s.strip()]
        for s in sentences:
            key = s.lower()
            if key not in seen:
                bullets.append(f"- {s}.")
                seen.add(key)
            if len(bullets) >= 10:
                break
        return '\n'.join(bullets)

    if summary_type == 'structured':
        # heuristic structure and optional field extraction
        lines = []
        if doc_type:
            lt = doc_type.lower()
            if lt in {'invoice', 'receipt'}:
                fields = extract_invoice_data(text) if lt == 'invoice' else extract_receipt_data(text)
                lines.append('Structured Fields:')
                for k, v in fields.items():
                    if v:
                        lines.append(f"- {k.title()}: {v}")
                lines.append('')
            elif lt == 'resume':
                fields = extract_resume_data(text)
                lines.append('Candidate:')
                if fields.get('name'): lines.append(f"- Name: {fields['name']}")
                if fields.get('email'): lines.append(f"- Email: {fields['email']}")
                if fields.get('phone'): lines.append(f"- Phone: {fields['phone']}")
                lines.append('')
        lines.append('Summary:')
        lines.append(combined)
        lines.append('')
        lines.append('Key Points:')
        for s in combined.split('.'):
            s = s.strip()
            if s:
                lines.append(f"- {s}.")
        return '\n'.join(lines)

    return combined or _summarize_chunk(text[:3000], max_len, min_len)


# Simple heuristic extractors for MVP
import re

def _find_date(text: str):
    m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text)
    return m.group(1) if m else ''


def _find_amount(text: str):
    m = re.search(r"(?i)(total|amount due|balance)\s*[:$]?\s*([$€£]?\s?\d+[\d,]*\.?\d{0,2})", text)
    return m.group(2) if m else ''


def _find_vendor(text: str):
    lines = text.splitlines()
    for line in lines[:10]:
        if len(line.strip()) > 2 and not any(k in line.lower() for k in ['invoice', 'receipt']):
            return line.strip()
    return ''


def extract_invoice_data(text: str):
    return {
        'date': _find_date(text),
        'total': _find_amount(text),
        'vendor': _find_vendor(text)
    }


def extract_receipt_data(text: str):
    return {
        'date': _find_date(text),
        'total': _find_amount(text),
        'vendor': _find_vendor(text)
    }


# Resume heuristics
def _find_name(text: str):
    # Heuristic: first non-empty line with alphabetic characters and reasonable length
    for line in text.splitlines():
        s = line.strip()
        if 2 < len(s) < 80 and any(c.isalpha() for c in s):
            # avoid lines starting with contact words
            low = s.lower()
            if not any(k in low for k in ['phone', 'email', 'resume', 'curriculum vitae', 'linkedin', 'github']):
                return s
    return ''


def extract_resume_data(text: str):
    name = _find_name(text)
    # naive extraction for email / phone
    import re
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(\+?\d[\d\s\-()]{7,})", text)
    return {
        'name': name,
        'email': email.group(0) if email else '',
        'phone': phone.group(0) if phone else ''
    }


def smart_answer(context: str, question: str, doc_type: Optional[str] = None):
    q = question.lower().strip()
    # Rule-based for resume name
    if doc_type and doc_type.lower() == 'resume':
        if 'name' in q or 'candidate name' in q:
            data = extract_resume_data(context)
            if data.get('name'):
                return data['name'], 0.9
        if 'phone' in q:
            data = extract_resume_data(context)
            if data.get('phone'):
                return data['phone'], 0.9
        if 'email' in q:
            data = extract_resume_data(context)
            if data.get('email'):
                return data['email'], 0.9
        if 'position' in q or 'role' in q or 'best fit' in q:
            # Use zero-shot on common roles to guess best position
            try:
                from .classifier import zero_shot_best_label
                roles = [
                    'Software Engineer', 'Data Scientist', 'Product Manager', 'UI/UX Designer',
                    'DevOps Engineer', 'QA Engineer', 'Business Analyst', 'Project Manager'
                ]
                label, score = zero_shot_best_label(context[:4000], roles)
                if label:
                    return label, float(score)
            except Exception:
                pass
    # Always use OpenRouter LLM QA
    return answer_question_llm(context, question)
