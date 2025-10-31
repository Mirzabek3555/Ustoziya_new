import os
from typing import Optional

from django.conf import settings


def extract_text_from_file(file_path: str, source_type: str) -> str:
    """Attestatsiya materiali faylidan matnni ajratib olish.
    Qo'llab-quvvatlanadigan turlar: image, docx, pdf, txt
    """
    source_type = (source_type or '').lower()

    if source_type == 'txt':
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                return f.read()

    if source_type == 'docx':
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ''

    if source_type == 'pdf':
        try:
            import PyPDF2
            text = []
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text.append(page.extract_text() or '')
            return "\n".join(text)
        except Exception:
            return ''

    if source_type == 'image':
        try:
            import cv2
            import pytesseract
            image = cv2.imread(file_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return pytesseract.image_to_string(gray, lang='uzb+eng')
        except Exception:
            return ''

    # Fallback: txt sifatida urinish
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ''


