"""Google Cloud Vision OCR provider implementation."""

import io
import os
from pathlib import Path
from typing import Optional

from PIL import Image

from src.config import get_settings
from src.logging_config import get_logger
from src.ocr.base import OCRError, OCRProvider, OCRResult
from src.ocr.file_handler import FileHandler

logger = get_logger("ocr.google_vision")


class GoogleVisionProvider(OCRProvider):
    """OCR provider using Google Cloud Vision API."""

    def __init__(self, credentials_path: Optional[Path] = None):
        """
        Initialize Google Vision provider.

        Args:
            credentials_path: Path to service account JSON file (default: from settings)
        """
        settings = get_settings()
        self.credentials_path = credentials_path or settings.google_application_credentials
        self.file_handler = FileHandler()
        self._client = None

        # Set credentials environment variable if provided
        if self.credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(self.credentials_path)

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "google_vision"

    def is_available(self) -> bool:
        """Check if Google Cloud Vision is available."""
        try:
            from google.cloud import vision  # noqa: F401

            # Check if credentials are configured
            if self.credentials_path and not self.credentials_path.exists():
                logger.warning(f"Credentials file not found: {self.credentials_path}")
                return False

            # Try to create a client
            self._get_client()
            return True
        except ImportError:
            logger.warning("google-cloud-vision package not installed")
            return False
        except Exception as e:
            logger.warning(f"Google Vision not available: {e}")
            return False

    def _get_client(self):
        """Get or create the Vision API client."""
        if self._client is None:
            from google.cloud import vision

            self._client = vision.ImageAnnotatorClient()
        return self._client

    def extract_text(self, file_path: Path) -> OCRResult:
        """
        Extract text from an image or PDF file using Google Cloud Vision.

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
            raise OCRError("Google Cloud Vision is not available", self.name)

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
        """Extract text from a single image file."""
        from google.cloud import vision

        client = self._get_client()

        # Read image content
        with open(image_path, "rb") as f:
            content = f.read()

        image = vision.Image(content=content)

        # Use document_text_detection for better results with documents
        response = client.document_text_detection(image=image)

        if response.error.message:
            raise OCRError(response.error.message, self.name)

        text = response.full_text_annotation.text if response.full_text_annotation else ""

        # Calculate confidence from page-level confidence
        confidence = self._calculate_confidence(response)

        # Detect language
        language = self._detect_language(response)

        return OCRResult(
            text=text,
            confidence=confidence,
            language=language,
            provider=self.name,
            page_count=1,
        )

    def _extract_from_pdf(self, pdf_path: Path) -> OCRResult:
        """Extract text from all pages of a PDF."""
        all_text = []
        total_confidence = 0.0
        page_count = 0

        # Convert PDF pages to images and process each
        for page_image in self.file_handler.pdf_to_images(pdf_path):
            text, confidence = self._ocr_pil_image(page_image)
            all_text.append(text)
            total_confidence += confidence
            page_count += 1

        avg_confidence = total_confidence / page_count if page_count > 0 else 0.0

        return OCRResult(
            text="\n\n--- Page Break ---\n\n".join(all_text),
            confidence=avg_confidence,
            language="he",  # Assume Hebrew for payslips
            provider=self.name,
            page_count=page_count,
        )

    def _ocr_pil_image(self, image: Image.Image) -> tuple[str, float]:
        """
        Perform OCR on a PIL Image.

        Args:
            image: PIL Image to process

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        from google.cloud import vision

        client = self._get_client()

        # Convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        content = img_byte_arr.getvalue()

        vision_image = vision.Image(content=content)
        response = client.document_text_detection(image=vision_image)

        if response.error.message:
            raise OCRError(response.error.message, self.name)

        text = response.full_text_annotation.text if response.full_text_annotation else ""
        confidence = self._calculate_confidence(response)

        return text, confidence

    def _calculate_confidence(self, response) -> float:
        """Calculate average confidence from Vision API response."""
        if not response.full_text_annotation:
            return 0.0

        confidences = []
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                if hasattr(block, "confidence"):
                    confidences.append(block.confidence)

        return sum(confidences) / len(confidences) if confidences else 0.8

    def _detect_language(self, response) -> Optional[str]:
        """Detect primary language from Vision API response."""
        if not response.full_text_annotation:
            return None

        for page in response.full_text_annotation.pages:
            if page.property and page.property.detected_languages:
                # Return the first (most likely) language
                return page.property.detected_languages[0].language_code

        return None
