"""OCR module for extracting text from payslip images and PDFs."""

from src.ocr.base import OCRError, OCRProvider, OCRResult
from src.ocr.factory import OCRFactory, extract_text
from src.ocr.file_handler import FileHandler

__all__ = [
    "OCRProvider",
    "OCRResult",
    "OCRError",
    "OCRFactory",
    "FileHandler",
    "extract_text",
]
