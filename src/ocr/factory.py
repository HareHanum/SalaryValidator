"""OCR provider factory for selecting and creating providers."""

from pathlib import Path
from typing import Optional

from src.config import OCRProvider as OCRProviderEnum
from src.config import get_settings
from src.logging_config import get_logger
from src.ocr.base import OCRError, OCRProvider, OCRResult

logger = get_logger("ocr.factory")


class OCRFactory:
    """Factory for creating and managing OCR providers."""

    _providers: dict[str, type[OCRProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[OCRProvider]) -> None:
        """Register an OCR provider class."""
        cls._providers[name] = provider_class

    @classmethod
    def get_provider(cls, provider_type: Optional[OCRProviderEnum] = None) -> OCRProvider:
        """
        Get an OCR provider instance.

        Args:
            provider_type: Type of provider to use (default: from settings)

        Returns:
            Configured OCR provider instance

        Raises:
            OCRError: If provider is not available
        """
        if provider_type is None:
            provider_type = get_settings().ocr_provider

        provider_name = provider_type.value

        if provider_name not in cls._providers:
            raise OCRError(f"Unknown OCR provider: {provider_name}")

        provider_class = cls._providers[provider_name]
        provider = provider_class()

        if not provider.is_available():
            raise OCRError(f"OCR provider '{provider_name}' is not available")

        logger.info(f"Using OCR provider: {provider_name}")
        return provider

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        available = []
        for name, provider_class in cls._providers.items():
            try:
                provider = provider_class()
                if provider.is_available():
                    available.append(name)
            except Exception:
                pass
        return available

    @classmethod
    def get_best_available_provider(cls) -> Optional[OCRProvider]:
        """
        Get the best available provider in order of preference.

        Preference order: Google Vision > Textract > Tesseract

        Returns:
            Best available OCR provider, or None if none available
        """
        preference_order = [
            OCRProviderEnum.GOOGLE,
            OCRProviderEnum.TEXTRACT,
            OCRProviderEnum.TESSERACT,
        ]

        for provider_type in preference_order:
            try:
                return cls.get_provider(provider_type)
            except OCRError:
                continue

        return None


def extract_text(file_path: Path, provider_type: Optional[OCRProviderEnum] = None) -> OCRResult:
    """
    Convenience function to extract text from a file.

    Args:
        file_path: Path to the image or PDF file
        provider_type: Type of provider to use (default: from settings)

    Returns:
        OCRResult containing extracted text
    """
    provider = OCRFactory.get_provider(provider_type)
    return provider.extract_text(file_path)


# Register providers
def _register_providers() -> None:
    """Register all available OCR providers."""
    from src.ocr.google_vision_provider import GoogleVisionProvider
    from src.ocr.tesseract_provider import TesseractProvider
    from src.ocr.textract_provider import TextractProvider

    OCRFactory.register("tesseract", TesseractProvider)
    OCRFactory.register("google", GoogleVisionProvider)
    OCRFactory.register("textract", TextractProvider)


_register_providers()
