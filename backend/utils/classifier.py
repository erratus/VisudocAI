import os
import requests

HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
HF_ZSC_MODEL = 'facebook/bart-large-mnli'

CATEGORIES = [
    'Invoice', 'Receipt', 'Letter', 'Contract', 'Resume', 'Report', 'Other'
]


def _hf_headers():
    if not HF_API_KEY:
        raise RuntimeError('HUGGINGFACE_API_KEY not configured')
    return {"Authorization": f"Bearer {HF_API_KEY}"}


def classify_document(text: str, candidate_labels=None):
    if candidate_labels is None:
        candidate_labels = CATEGORIES
    payload = {
        "inputs": text[:4000],  # keep under common limits
        "parameters": {"candidate_labels": candidate_labels, "multi_label": False}
    }
    url = f"https://api-inference.huggingface.co/models/{HF_ZSC_MODEL}"
    try:
        r = requests.post(url, headers=_hf_headers(), json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        # HF returns labels/scores arrays
        labels = data.get('labels') or []
        scores = data.get('scores') or []
        return list(zip(labels, scores))
    except requests.HTTPError as e:
        # If model is loading, HF returns 503; suggest retry
        if e.response is not None and e.response.status_code == 503:
            return [('Other', 0.0)]
        raise RuntimeError(f"HF classification error: {e}")
    except Exception as e:
        raise RuntimeError(f"Classification failed: {e}")


def get_document_type(text: str):
    pairs = classify_document(text)
    if not pairs:
        return 'Other', 0.0
    label, score = pairs[0]
    return label, float(score)
