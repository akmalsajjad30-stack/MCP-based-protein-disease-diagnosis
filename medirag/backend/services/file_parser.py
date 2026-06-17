"""File parser for PDF, DOCX, and image lab reports."""
import logging
logger = logging.getLogger(__name__)


def parse_pdf(file_path: str) -> str:
    try:
        import fitz
        doc = fitz.open(file_path)
        return "\n".join(page.get_text() for page in doc).strip()
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        return ""


def parse_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as e:
        logger.error(f"DOCX parse error: {e}")
        return ""


def parse_image(file_path: str) -> str:
    try:
        from PIL import Image
        img = Image.open(file_path)
        return f"[Image uploaded: {img.format} {img.size[0]}x{img.size[1]}px — OCR not enabled]"
    except Exception as e:
        logger.error(f"Image parse error: {e}")
        return ""


def parse_file(file_path: str, content_type: str = "") -> str:
    ext = file_path.lower().split(".")[-1]
    if ext == "pdf" or "pdf" in content_type:
        return parse_pdf(file_path)
    elif ext in ("docx", "doc") or "word" in content_type:
        return parse_docx(file_path)
    elif ext in ("png", "jpg", "jpeg", "tiff", "bmp") or "image" in content_type:
        return parse_image(file_path)
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(5000)
        except Exception:
            return ""
