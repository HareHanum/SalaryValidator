"""Tesseract OCR provider implementation."""

import shutil
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image

from src.config import get_settings
from src.logging_config import get_logger
from src.ocr.base import OCRError, OCRProvider, OCRResult
from src.ocr.file_handler import FileHandler

logger = get_logger("ocr.tesseract")


class TesseractProvider(OCRProvider):
    """OCR provider using Tesseract OCR engine."""

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        lang: Optional[str] = None,
        preprocess: bool = True,
    ):
        """
        Initialize Tesseract provider.

        Args:
            tesseract_cmd: Path to tesseract executable (default: from settings)
            lang: Language codes for OCR (default: from settings, e.g., "heb+eng")
            preprocess: Whether to preprocess images before OCR
        """
        settings = get_settings()
        self.tesseract_cmd = tesseract_cmd or settings.tesseract_cmd
        self.lang = lang or settings.tesseract_lang
        self.preprocess = preprocess
        self.file_handler = FileHandler()

        # Configure pytesseract
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "tesseract"

    def is_available(self) -> bool:
        """Check if Tesseract is available."""
        # Check if tesseract executable exists
        if self.tesseract_cmd and Path(self.tesseract_cmd).exists():
            return True

        # Check if tesseract is in PATH
        return shutil.which("tesseract") is not None

    def extract_text(self, file_path: Path) -> OCRResult:
        """
        Extract text from an image or PDF file using Tesseract.

        Args:
            file_path: Path to the image or PDF file

        Returns:
            OCRResult containing extracted text

        Raises:
            FileNotFoundError: If the file doesn't exist
            OCRError: If text extraction fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.supports_file(file_path):
            raise OCRError(f"Unsupported file format: {file_path.suffix}", self.name)

        if not self.is_available():
            raise OCRError("Tesseract is not available", self.name)

        logger.info(f"Extracting text from: {file_path}")

        try:
            if self.file_handler.is_pdf(file_path):
                return self._extract_from_pdf(file_path)
            else:
                return self._extract_from_image(file_path)
        except Exception as e:
            if isinstance(e, (FileNotFoundError, OCRError)):
                raise
            raise OCRError(f"Failed to extract text: {str(e)}", self.name) from e

    def _extract_from_image(self, image_path: Path) -> OCRResult:
        """Extract text from a single image."""
        image = self.file_handler.load_image(image_path)

        if self.preprocess:
            image = self.file_handler.preprocess_image(image)

        text, confidence = self._ocr_image(image)

        return OCRResult(
            text=text,
            confidence=confidence,
            language=self.lang,
            provider=self.name,
            page_count=1,
        )

    def _extract_from_pdf(self, pdf_path: Path) -> OCRResult:
        """Extract text from all pages of a PDF."""
        all_text = []
        total_confidence = 0.0
        page_count = 0

        for page_image in self.file_handler.pdf_to_images(pdf_path):
            if self.preprocess:
                page_image = self.file_handler.preprocess_image(page_image)

            text, confidence = self._ocr_image(page_image)
            all_text.append(text)
            total_confidence += confidence
            page_count += 1

        avg_confidence = total_confidence / page_count if page_count > 0 else 0.0

        return OCRResult(
            text="\n\n--- Page Break ---\n\n".join(all_text),
            confidence=avg_confidence,
            language=self.lang,
            provider=self.name,
            page_count=page_count,
        )

    def _ocr_image(self, image: Image.Image) -> tuple[str, float]:
        """
        Perform OCR on a single image.

        Args:
            image: PIL Image to process

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        # Get detailed OCR data including confidence
        ocr_data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            output_type=pytesseract.Output.DICT,
        )

        # Extract text
        text = pytesseract.image_to_string(image, lang=self.lang)

        # Calculate average confidence from words with valid confidence
        confidences = [
            int(conf)
            for conf in ocr_data["conf"]
            if conf != "-1" and str(conf).isdigit()
        ]
        avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.5

        logger.debug(f"OCR completed with confidence: {avg_confidence:.2%}")

        return text.strip(), avg_confidence
