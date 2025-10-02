import os
import time
import requests
from typing import Optional

HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
HF_QA_MODEL = 'deepset/roberta-base-squad2'
HF_SUM_MODEL = 'facebook/bart-large-cnn'


def _hf_headers():
    if not HF_API_KEY:
        raise RuntimeError('HUGGINGFACE_API_KEY not configured')
    return {"Authorization": f"Bearer {HF_API_KEY}"}


def _post_with_retry(url, payload, timeout=60, retries=2, backoff=2.0):
    last_exc = None
    for i in range(retries + 1):
        try:
            r = requests.post(url, headers=_hf_headers(), json=payload, timeout=timeout)
            if r.status_code == 503:
                # model loading, wait and retry
                time.sleep(backoff * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            time.sleep(backoff * (i + 1))
    raise RuntimeError(f"HF request failed: {last_exc}")


def answer_question(context: str, question: str):
    url = f"https://api-inference.huggingface.co/models/{HF_QA_MODEL}"
    payload = {"inputs": {"question": question, "context": context[:7000]}}
    data = _post_with_retry(url, payload)
    # response has 'answer' and 'score'
    if isinstance(data, dict):
        return data.get('answer', ''), float(data.get('score', 0.0))
    # some responses may be lists
    if isinstance(data, list) and data:
        ans = data[0]
        return ans.get('answer', ''), float(ans.get('score', 0.0))
    return '', 0.0


def _summarize_chunk(text: str, max_len=130, min_len=30):
    url = f"https://api-inference.huggingface.co/models/{HF_SUM_MODEL}"
    payload = {
        "inputs": text,
        "parameters": {"min_length": min_len, "max_length": max_len}
    }
    data = _post_with_retry(url, payload)
    if isinstance(data, list) and data:
        return data[0].get('summary_text', '')
    if isinstance(data, dict):
        # some variants wrap differently
        return data.get('summary_text', '')
    return ''


def generate_summary(text: str, summary_type: str = 'general', doc_type: Optional[str] = None):
    text = text.strip()
    if not text:
        return ''

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
        # turn sentences into bullets
        sentences = [s.strip() for s in combined.replace('\n', ' ').split('.') if s.strip()]
        return '\n'.join(f"- {s}." for s in sentences[:8])

    if summary_type == 'structured':
        # heuristic structure and optional field extraction for invoices/receipts
        lines = []
        if doc_type and doc_type.lower() in {'invoice', 'receipt'}:
            fields = extract_invoice_data(text) if doc_type.lower() == 'invoice' else extract_receipt_data(text)
            lines.append('Structured Fields:')
            for k, v in fields.items():
                if v:
                    lines.append(f"- {k.title()}: {v}")
            lines.append('')
        lines.append('Summary:')
        lines.append(combined)
        lines.append('')
        lines.append('Key Points:')
        lines.extend(f"- {s.strip()}." for s in combined.split('.') if s.strip())
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
