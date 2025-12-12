"""Tests for the OCR module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

import pytest
from PIL import Image

from src.ocr.base import OCRError, OCRProvider, OCRResult
from src.ocr.file_handler import FileHandler
from src.ocr.tesseract_provider import TesseractProvider
from src.ocr.google_vision_provider import GoogleVisionProvider
from src.ocr.textract_provider import TextractProvider
from src.ocr.factory import OCRFactory
from src.config import OCRProvider as OCRProviderType


class TestOCRResult:
    """Tests for OCRResult dataclass."""

    def test_ocr_result_creation(self):
        """Test creating an OCRResult."""
        result = OCRResult(
            text="Test text",
            confidence=0.95,
            language="en",
            provider="tesseract",
            page_count=1,
        )
        assert result.text == "Test text"
        assert result.confidence == 0.95
        assert result.language == "en"
        assert result.provider == "tesseract"
        assert result.page_count == 1

    def test_ocr_result_is_empty(self):
        """Test is_empty property."""
        empty_result = OCRResult(text="", confidence=0.0)
        assert empty_result.is_empty is True

        whitespace_result = OCRResult(text="   \n\t  ", confidence=0.0)
        assert whitespace_result.is_empty is True

        non_empty_result = OCRResult(text="Some text", confidence=0.5)
        assert non_empty_result.is_empty is False


class TestOCRError:
    """Tests for OCRError exception."""

    def test_ocr_error_with_provider(self):
        """Test OCRError with provider name."""
        error = OCRError("Test error", provider="tesseract")
        assert "tesseract" in str(error)
        assert "Test error" in str(error)
        assert error.provider == "tesseract"

    def test_ocr_error_without_provider(self):
        """Test OCRError without provider name."""
        error = OCRError("Test error")
        assert str(error) == "Test error"
        assert error.provider is None


class TestFileHandler:
    """Tests for FileHandler class."""

    def test_is_pdf(self):
        """Test PDF file detection."""
        handler = FileHandler()
        assert handler.is_pdf(Path("test.pdf")) is True
        assert handler.is_pdf(Path("test.PDF")) is True
        assert handler.is_pdf(Path("test.png")) is False

    def test_is_image(self):
        """Test image file detection."""
        handler = FileHandler()
        assert handler.is_image(Path("test.png")) is True
        assert handler.is_image(Path("test.jpg")) is True
        assert handler.is_image(Path("test.jpeg")) is True
        assert handler.is_image(Path("test.tiff")) is True
        assert handler.is_image(Path("test.pdf")) is False

    def test_load_image_file_not_found(self):
        """Test loading non-existent image."""
        handler = FileHandler()
        with pytest.raises(FileNotFoundError):
            handler.load_image(Path("/nonexistent/image.png"))

    def test_load_image_unsupported_format(self, tmp_path):
        """Test loading unsupported file format."""
        handler = FileHandler()
        unsupported_file = tmp_path / "test.txt"
        unsupported_file.write_text("test")
        with pytest.raises(ValueError, match="Unsupported image format"):
            handler.load_image(unsupported_file)

    def test_preprocess_image(self):
        """Test image preprocessing."""
        handler = FileHandler()
        # Create a simple test image
        image = Image.new("RGB", (100, 100), color="white")
        processed = handler.preprocess_image(image)
        assert processed.mode == "RGB"
        assert processed.size == (100, 100)


class TestTesseractProvider:
    """Tests for TesseractProvider class."""

    def test_provider_name(self):
        """Test provider name property."""
        provider = TesseractProvider()
        assert provider.name == "tesseract"

    def test_supports_file(self):
        """Test file support checking."""
        provider = TesseractProvider()
        assert provider.supports_file(Path("test.pdf")) is True
        assert provider.supports_file(Path("test.png")) is True
        assert provider.supports_file(Path("test.jpg")) is True
        assert provider.supports_file(Path("test.txt")) is False

    def test_extract_text_file_not_found(self):
        """Test extraction with non-existent file."""
        provider = TesseractProvider()
        with pytest.raises(FileNotFoundError):
            provider.extract_text(Path("/nonexistent/file.png"))

    def test_extract_text_unsupported_format(self, tmp_path):
        """Test extraction with unsupported format."""
        provider = TesseractProvider()
        unsupported_file = tmp_path / "test.txt"
        unsupported_file.write_text("test")
        with pytest.raises(OCRError, match="Unsupported file format"):
            provider.extract_text(unsupported_file)

    @patch("src.ocr.tesseract_provider.pytesseract")
    @patch.object(TesseractProvider, "is_available", return_value=True)
    def test_extract_text_from_image(self, mock_available, mock_pytesseract, tmp_path):
        """Test text extraction from image."""
        # Create a test image
        test_image = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(test_image)

        # Mock pytesseract responses
        mock_pytesseract.image_to_string.return_value = "Extracted text"
        mock_pytesseract.image_to_data.return_value = {
            "conf": ["95", "90", "85"],
        }
        mock_pytesseract.Output.DICT = "dict"

        provider = TesseractProvider()
        result = provider.extract_text(test_image)

        assert result.text == "Extracted text"
        assert result.provider == "tesseract"
        assert result.page_count == 1
        assert 0 <= result.confidence <= 1


class TestOCRFactory:
    """Tests for OCRFactory class."""

    def test_get_available_providers(self):
        """Test getting available providers."""
        from src.ocr.factory import OCRFactory

        available = OCRFactory.get_available_providers()
        assert isinstance(available, list)

    def test_get_provider_unknown(self):
        """Test getting unknown provider."""
        from src.ocr.factory import OCRFactory

        # Create a mock enum value
        mock_provider = MagicMock()
        mock_provider.value = "unknown_provider"

        with pytest.raises(OCRError, match="Unknown OCR provider"):
            OCRFactory.get_provider(mock_provider)


class TestGoogleVisionProviderMocked:
    """Tests for GoogleVisionProvider with mocked API."""

    def test_provider_name(self):
        """Test provider name property."""
        provider = GoogleVisionProvider()
        assert provider.name == "google_vision"

    def test_supports_file(self):
        """Test file support checking."""
        provider = GoogleVisionProvider()
        assert provider.supports_file(Path("test.pdf")) is True
        assert provider.supports_file(Path("test.png")) is True
        assert provider.supports_file(Path("test.jpg")) is True
        assert provider.supports_file(Path("test.txt")) is False

    @patch("src.ocr.google_vision_provider.vision")
    def test_extract_text_from_image_mocked(self, mock_vision, tmp_path):
        """Test text extraction with mocked Google Vision API."""
        # Create a test image
        test_image = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(test_image)

        # Mock the Vision API response
        mock_client = MagicMock()
        mock_vision.ImageAnnotatorClient.return_value = mock_client

        mock_response = MagicMock()
        mock_annotation = MagicMock()
        mock_annotation.description = "שכר בסיס: 5,571.75 ₪\nשעות עבודה: 182"
        mock_response.full_text_annotation = mock_annotation
        mock_response.error.message = ""

        mock_client.document_text_detection.return_value = mock_response

        provider = GoogleVisionProvider()
        result = provider.extract_text(test_image)

        assert "שכר בסיס" in result.text
        assert result.provider == "google_vision"

    @patch("src.ocr.google_vision_provider.vision")
    def test_extract_text_api_error(self, mock_vision, tmp_path):
        """Test handling of Google Vision API errors."""
        test_image = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(test_image)

        mock_client = MagicMock()
        mock_vision.ImageAnnotatorClient.return_value = mock_client

        mock_response = MagicMock()
        mock_response.error.message = "API quota exceeded"
        mock_client.document_text_detection.return_value = mock_response

        provider = GoogleVisionProvider()
        with pytest.raises(OCRError, match="quota"):
            provider.extract_text(test_image)


class TestTextractProviderMocked:
    """Tests for TextractProvider with mocked AWS API."""

    def test_provider_name(self):
        """Test provider name property."""
        provider = TextractProvider()
        assert provider.name == "textract"

    def test_supports_file(self):
        """Test file support checking."""
        provider = TextractProvider()
        assert provider.supports_file(Path("test.pdf")) is True
        assert provider.supports_file(Path("test.png")) is True
        assert provider.supports_file(Path("test.jpg")) is True
        assert provider.supports_file(Path("test.txt")) is False

    @patch("src.ocr.textract_provider.boto3")
    def test_extract_text_from_image_mocked(self, mock_boto3, tmp_path):
        """Test text extraction with mocked Textract API."""
        test_image = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(test_image)

        # Mock boto3 client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        mock_response = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "שכר בסיס: 5,571.75 ₪",
                    "Confidence": 95.5,
                },
                {
                    "BlockType": "LINE",
                    "Text": "שעות עבודה: 182",
                    "Confidence": 98.2,
                },
            ]
        }
        mock_client.detect_document_text.return_value = mock_response

        provider = TextractProvider()
        result = provider.extract_text(test_image)

        assert "שכר בסיס" in result.text
        assert result.provider == "textract"


class TestOCRProviderInterface:
    """Tests for the OCRProvider abstract interface."""

    def test_ocr_provider_is_abstract(self):
        """Test that OCRProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            OCRProvider()

    def test_concrete_provider_implements_interface(self):
        """Test that concrete providers implement all required methods."""
        provider = TesseractProvider()

        # Check required properties
        assert hasattr(provider, "name")
        assert isinstance(provider.name, str)

        # Check required methods
        assert hasattr(provider, "extract_text")
        assert callable(provider.extract_text)

        assert hasattr(provider, "supports_file")
        assert callable(provider.supports_file)


class TestOCRResultMethods:
    """Additional tests for OCRResult methods and properties."""

    def test_ocr_result_with_metadata(self):
        """Test OCRResult with metadata."""
        result = OCRResult(
            text="Test text",
            confidence=0.95,
            provider="test",
            metadata={"pages": 2, "language": "he"},
        )
        assert result.metadata["pages"] == 2
        assert result.metadata["language"] == "he"

    def test_ocr_result_default_values(self):
        """Test OCRResult default values."""
        result = OCRResult(text="Test", confidence=0.9)
        assert result.provider is None
        assert result.language is None
        assert result.page_count == 1
        assert result.metadata == {}

    def test_ocr_result_confidence_range(self):
        """Test that confidence values are accepted."""
        # Valid confidence values
        result_low = OCRResult(text="Test", confidence=0.0)
        result_high = OCRResult(text="Test", confidence=1.0)
        result_mid = OCRResult(text="Test", confidence=0.5)

        assert result_low.confidence == 0.0
        assert result_high.confidence == 1.0
        assert result_mid.confidence == 0.5


class TestFileHandlerAdvanced:
    """Advanced tests for FileHandler."""

    def test_preprocess_image_grayscale(self):
        """Test preprocessing grayscale images."""
        handler = FileHandler()
        image = Image.new("L", (100, 100), color=128)  # Grayscale
        processed = handler.preprocess_image(image)
        assert processed is not None

    def test_preprocess_image_rgba(self):
        """Test preprocessing RGBA images."""
        handler = FileHandler()
        image = Image.new("RGBA", (100, 100), color=(255, 255, 255, 255))
        processed = handler.preprocess_image(image)
        assert processed is not None

    def test_load_image_valid(self, tmp_path):
        """Test loading a valid image file."""
        handler = FileHandler()
        test_image = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(test_image)

        loaded = handler.load_image(test_image)
        assert loaded is not None
        assert loaded.size == (100, 100)

    def test_file_extension_case_insensitive(self):
        """Test that file extension checking is case insensitive."""
        handler = FileHandler()
        assert handler.is_pdf(Path("test.PDF")) is True
        assert handler.is_pdf(Path("test.Pdf")) is True
        assert handler.is_image(Path("test.PNG")) is True
        assert handler.is_image(Path("test.JPG")) is True
        assert handler.is_image(Path("test.JPEG")) is True


class TestOCRFactoryAdvanced:
    """Advanced tests for OCRFactory."""

    @patch.object(TesseractProvider, "is_available", return_value=True)
    def test_get_provider_tesseract(self, mock_available):
        """Test getting Tesseract provider."""
        provider = OCRFactory.get_provider(OCRProviderType.TESSERACT)
        assert isinstance(provider, TesseractProvider)

    @patch.object(GoogleVisionProvider, "is_available", return_value=True)
    def test_get_provider_google_vision(self, mock_available):
        """Test getting Google Vision provider."""
        provider = OCRFactory.get_provider(OCRProviderType.GOOGLE)
        assert isinstance(provider, GoogleVisionProvider)

    @patch.object(TextractProvider, "is_available", return_value=True)
    def test_get_provider_textract(self, mock_available):
        """Test getting Textract provider."""
        provider = OCRFactory.get_provider(OCRProviderType.TEXTRACT)
        assert isinstance(provider, TextractProvider)

    def test_provider_type_enum_values(self):
        """Test OCRProviderType enum values."""
        assert OCRProviderType.TESSERACT.value == "tesseract"
        assert OCRProviderType.GOOGLE.value == "google"
        assert OCRProviderType.TEXTRACT.value == "textract"


class TestOCRWithHebrewText:
    """Tests for OCR handling of Hebrew text."""

    @patch("src.ocr.tesseract_provider.pytesseract")
    @patch.object(TesseractProvider, "is_available", return_value=True)
    def test_hebrew_text_extraction(self, mock_available, mock_pytesseract, tmp_path):
        """Test extraction of Hebrew text."""
        test_image = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(test_image)

        hebrew_text = """
        תלוש שכר לחודש ינואר 2024
        שכר בסיס: 5,571.75 ₪
        שעות עבודה: 182
        """

        mock_pytesseract.image_to_string.return_value = hebrew_text
        mock_pytesseract.image_to_data.return_value = {"conf": ["95"]}
        mock_pytesseract.Output.DICT = "dict"

        provider = TesseractProvider()
        result = provider.extract_text(test_image)

        assert "תלוש שכר" in result.text
        assert "שכר בסיס" in result.text
        assert "5,571.75" in result.text

    @patch("src.ocr.tesseract_provider.pytesseract")
    @patch.object(TesseractProvider, "is_available", return_value=True)
    def test_mixed_hebrew_english_text(self, mock_available, mock_pytesseract, tmp_path):
        """Test extraction of mixed Hebrew/English text."""
        test_image = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(test_image)

        mixed_text = """
        Company Name Ltd.
        תלוש שכר - January 2024
        Employee ID: 123456789
        שכר ברוטו: 5,571.75 ₪
        """

        mock_pytesseract.image_to_string.return_value = mixed_text
        mock_pytesseract.image_to_data.return_value = {"conf": ["90"]}
        mock_pytesseract.Output.DICT = "dict"

        provider = TesseractProvider()
        result = provider.extract_text(test_image)

        assert "Company Name" in result.text
        assert "תלוש שכר" in result.text
        assert "123456789" in result.text


class TestOCRErrorHandling:
    """Tests for OCR error handling."""

    def test_ocr_error_chaining(self):
        """Test OCR error exception chaining."""
        original_error = ValueError("Original error")
        ocr_error = OCRError("OCR failed", provider="test")
        ocr_error.__cause__ = original_error

        assert ocr_error.__cause__ is original_error

    def test_file_not_found_error(self):
        """Test error when file doesn't exist."""
        provider = TesseractProvider()
        with pytest.raises(FileNotFoundError):
            provider.extract_text(Path("/nonexistent/path/file.png"))

    def test_invalid_file_content(self, tmp_path):
        """Test error with invalid file content."""
        invalid_file = tmp_path / "invalid.png"
        invalid_file.write_bytes(b"not a valid image")

        handler = FileHandler()
        with pytest.raises(Exception):  # PIL.UnidentifiedImageError
            handler.load_image(invalid_file)
