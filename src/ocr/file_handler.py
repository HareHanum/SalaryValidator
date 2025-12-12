"""File handling utilities for OCR processing."""

from pathlib import Path
from typing import Generator

import fitz  # PyMuPDF
from PIL import Image

from src.logging_config import get_logger

logger = get_logger("ocr.file_handler")


class FileHandler:
    """Handles file loading and conversion for OCR processing."""

    # Supported image formats
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif"}
    PDF_EXTENSIONS = {".pdf"}

    def __init__(self, dpi: int = 300):
        """
        Initialize file handler.

        Args:
            dpi: Resolution for PDF to image conversion
        """
        self.dpi = dpi

    def is_pdf(self, file_path: Path) -> bool:
        """Check if file is a PDF."""
        return file_path.suffix.lower() in self.PDF_EXTENSIONS

    def is_image(self, file_path: Path) -> bool:
        """Check if file is an image."""
        return file_path.suffix.lower() in self.IMAGE_EXTENSIONS

    def load_image(self, file_path: Path) -> Image.Image:
        """
        Load an image file.

        Args:
            file_path: Path to the image file

        Returns:
            PIL Image object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        if not self.is_image(file_path):
            raise ValueError(f"Unsupported image format: {file_path.suffix}")

        logger.debug(f"Loading image: {file_path}")
        return Image.open(file_path)

    def pdf_to_images(self, pdf_path: Path) -> Generator[Image.Image, None, None]:
        """
        Convert PDF pages to images.

        Args:
            pdf_path: Path to the PDF file

        Yields:
            PIL Image for each page

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a PDF
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if not self.is_pdf(pdf_path):
            raise ValueError(f"Not a PDF file: {pdf_path}")

        logger.debug(f"Converting PDF to images: {pdf_path}")

        doc = fitz.open(pdf_path)
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Create a matrix for the desired DPI
                # Default PDF resolution is 72 DPI
                zoom = self.dpi / 72
                matrix = fitz.Matrix(zoom, zoom)

                # Render page to pixmap
                pixmap = page.get_pixmap(matrix=matrix)

                # Convert to PIL Image
                img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)

                logger.debug(f"Converted page {page_num + 1}/{len(doc)}")
                yield img
        finally:
            doc.close()

    def get_page_count(self, file_path: Path) -> int:
        """
        Get the number of pages in a file.

        Args:
            file_path: Path to the file

        Returns:
            Number of pages (1 for images)
        """
        if self.is_image(file_path):
            return 1

        if self.is_pdf(file_path):
            doc = fitz.open(file_path)
            try:
                return len(doc)
            finally:
                doc.close()

        return 0

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.

        Args:
            image: Input PIL Image

        Returns:
            Preprocessed PIL Image
        """
        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Convert to grayscale for OCR
        grayscale = image.convert("L")

        # Increase contrast using simple thresholding
        # This helps with payslip documents that may have low contrast
        threshold = 180
        binary = grayscale.point(lambda x: 255 if x > threshold else 0)

        # Convert back to RGB for compatibility
        return binary.convert("RGB")
