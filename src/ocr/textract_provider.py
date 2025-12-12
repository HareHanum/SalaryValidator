"""Amazon Textract OCR provider implementation."""

import io
from pathlib import Path
from typing import Optional

from PIL import Image

from src.config import get_settings
from src.logging_config import get_logger
from src.ocr.base import OCRError, OCRProvider, OCRResult
from src.ocr.file_handler import FileHandler

logger = get_logger("ocr.textract")


class TextractProvider(OCRProvider):
    """OCR provider using Amazon Textract."""

    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
    ):
        """
        Initialize Textract provider.

        Args:
            aws_access_key_id: AWS access key (default: from settings/env)
            aws_secret_access_key: AWS secret key (default: from settings/env)
            region_name: AWS region (default: from settings)
        """
        settings = get_settings()
        self.aws_access_key_id = aws_access_key_id or settings.aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key or settings.aws_secret_access_key
        self.region_name = region_name or settings.aws_region
        self.file_handler = FileHandler()
        self._client = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "textract"

    def is_available(self) -> bool:
        """Check if Amazon Textract is available."""
        try:
            import boto3  # noqa: F401

            # Try to create a client
            self._get_client()
            return True
        except ImportError:
            logger.warning("boto3 package not installed")
            return False
        except Exception as e:
            logger.warning(f"Textract not available: {e}")
            return False

    def _get_client(self):
        """Get or create the Textract client."""
        if self._client is None:
            import boto3

            client_kwargs = {"service_name": "textract"}

            if self.region_name:
                client_kwargs["region_name"] = self.region_name

            if self.aws_access_key_id and self.aws_secret_access_key:
                client_kwargs["aws_access_key_id"] = self.aws_access_key_id
                client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key

            self._client = boto3.client(**client_kwargs)

        return self._client

    def extract_text(self, file_path: Path) -> OCRResult:
        """
        Extract text from an image or PDF file using Amazon Textract.

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
            raise OCRError("Amazon Textract is not available", self.name)

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
        client = self._get_client()

        # Read image content
        with open(image_path, "rb") as f:
            content = f.read()

        # Call Textract
        response = client.detect_document_text(Document={"Bytes": content})

        text, confidence = self._parse_textract_response(response)

        return OCRResult(
            text=text,
            confidence=confidence,
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
        client = self._get_client()

        # Convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        content = img_byte_arr.getvalue()

        response = client.detect_document_text(Document={"Bytes": content})

        return self._parse_textract_response(response)

    def _parse_textract_response(self, response: dict) -> tuple[str, float]:
        """
        Parse Textract response to extract text and confidence.

        Args:
            response: Textract API response

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        blocks = response.get("Blocks", [])
        lines = []
        confidences = []

        for block in blocks:
            if block["BlockType"] == "LINE":
                lines.append(block.get("Text", ""))
                if "Confidence" in block:
                    confidences.append(block["Confidence"] / 100)

        text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.8

        return text, avg_confidence
