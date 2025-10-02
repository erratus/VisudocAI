import os
import requests


# Environment configuration for OpenRouter
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OR_MODEL_CLASS = os.getenv('OR_MODEL_CLASS', 'openrouter/auto')
OR_REFERER = os.getenv('OR_REFERER', '')
OR_TITLE = os.getenv('OR_TITLE', 'VisuDocAI')


# Default categories used across the app
CATEGORIES = [
    'Invoice', 'Receipt', 'Letter', 'Contract', 'Resume', 'Report', 'Other'
]


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


def _or_chat(messages, model: str, max_tokens=64, temperature=0.0):
    url = 'https://openrouter.ai/api/v1/chat/completions'
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    r = requests.post(url, headers=_or_headers(), json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    if data.get('choices'):
        return data['choices'][0]['message'].get('content', '')
    return ''


def _choose_label_llm(text: str, candidate_labels):
    labels_str = ', '.join(candidate_labels)
    messages = [
        {
            'role': 'system',
            'content': 'Choose exactly one label from the provided list that best describes the document. Respond with only the label.'
        },
        {
            'role': 'user',
            'content': f'Labels: {labels_str}\n\nDocument:\n{text[:4000]}\n\nLabel:'
        }
    ]
    out = _or_chat(messages, OR_MODEL_CLASS, max_tokens=16, temperature=0.0)
    answer = (out or '').strip()
    norm = answer.lower()
    best = None
    for lab in candidate_labels:
        if lab.lower() == norm or lab.lower() in norm or norm in lab.lower():
            best = lab
            break
    return best or 'Other'


def classify_document(text: str, candidate_labels=None):
    if candidate_labels is None:
        candidate_labels = CATEGORIES

    best = _choose_label_llm(text, candidate_labels)
    # Return list of (label, score). We use a conservative fixed score since LLM doesn't give probabilities.
    return [(best, 0.85)]


def zero_shot_best_label(text: str, labels):
    pairs = classify_document(text, candidate_labels=labels)
    return pairs[0] if pairs else ('', 0.0)


def get_document_type(text: str):
    pairs = classify_document(text)
    if not pairs:
        return 'Other', 0.0
    label, score = pairs[0]
    return label, float(score)
