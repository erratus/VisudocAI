import os
import io
from typing import Tuple, List
from PIL import Image, ImageOps, ImageFilter
import pytesseract

# Optional backends for PDF rendering
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from pdf2image import convert_from_path as _convert_from_path
except Exception:
    _convert_from_path = None

TESSERACT_CMD = os.getenv('TESSERACT_CMD')
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

POPPLER_PATH = os.getenv('POPPLER_PATH')

SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg'}


def detect_file_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return 'pdf'
    if ext in SUPPORTED_IMAGE_EXTS:
        return 'image'
    return 'unknown'


def preprocess_image(image: Image.Image) -> Image.Image:
    # convert to grayscale, increase contrast, denoise
    img = ImageOps.grayscale(image)
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return img


def extract_text_from_image(file_path: str) -> str:
    try:
        with Image.open(file_path) as img:
            img = preprocess_image(img)
            text = pytesseract.image_to_string(img)
            return text.strip()
    except Exception as e:
        raise RuntimeError(f"Image OCR failed: {e}")


def extract_text_from_pdf(file_path: str) -> str:
    try:
        texts: List[str] = []
        if fitz is not None:
            # Render pages with PyMuPDF (no Poppler required)
            doc = fitz.open(file_path)
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                with Image.open(io.BytesIO(img_bytes)) as img:
                    proc = preprocess_image(img)
                    texts.append(pytesseract.image_to_string(proc))
        else:
            if _convert_from_path is None:
                raise RuntimeError(
                    "PDF OCR requires either PyMuPDF (fitz) or Poppler + pdf2image. "
                    "Install PyMuPDF (pip install PyMuPDF) to avoid Poppler on Windows."
                )
            pages = _convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH)
            for page in pages:
                proc = preprocess_image(page)
                texts.append(pytesseract.image_to_string(proc))
        return '\n\n'.join(t.strip() for t in texts if t and t.strip())
    except Exception as e:
        raise RuntimeError(f"PDF OCR failed: {e}")
