"""Base interface for OCR providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class OCRResult:
    """Result from OCR text extraction."""

    text: str
    confidence: float  # 0.0 to 1.0
    language: Optional[str] = None
    provider: Optional[str] = None
    page_count: int = 1
    metadata: Optional[dict] = None

    @property
    def is_empty(self) -> bool:
        """Check if extracted text is empty."""
        return not self.text or not self.text.strip()


class OCRProvider(ABC):
    """Abstract base class for OCR providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass

    @abstractmethod
    def extract_text(self, file_path: Path) -> OCRResult:
        """
        Extract text from an image or PDF file.

        Args:
            file_path: Path to the image or PDF file

        Returns:
            OCRResult containing extracted text and metadata

        Raises:
            FileNotFoundError: If the file doesn't exist
            OCRError: If text extraction fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this provider is available and configured.

        Returns:
            True if provider can be used, False otherwise
        """
        pass

    def supports_file(self, file_path: Path) -> bool:
        """
        Check if this provider supports the given file type.

        Args:
            file_path: Path to the file

        Returns:
            True if file type is supported
        """
        supported_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif"}
        return file_path.suffix.lower() in supported_extensions


class OCRError(Exception):
    """Exception raised when OCR extraction fails."""

    def __init__(self, message: str, provider: Optional[str] = None):
        self.provider = provider
        super().__init__(f"[{provider}] {message}" if provider else message)
