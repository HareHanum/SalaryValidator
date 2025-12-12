"""Configuration management for SalaryValidator."""

from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class OCRProvider(str, Enum):
    """Supported OCR providers."""

    GOOGLE = "google"
    TEXTRACT = "textract"
    TESSERACT = "tesseract"


class OutputFormat(str, Enum):
    """Supported output formats."""

    JSON = "json"
    TEXT = "text"
    HTML = "html"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OCR Configuration
    ocr_provider: OCRProvider = Field(
        default=OCRProvider.TESSERACT,
        description="OCR provider to use for text extraction",
    )

    # Google Cloud Vision
    google_application_credentials: Optional[Path] = Field(
        default=None,
        description="Path to Google Cloud service account JSON file",
    )

    # AWS Textract
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    aws_region: str = Field(default="us-east-1")

    # Tesseract
    tesseract_cmd: str = Field(
        default="/usr/bin/tesseract",
        description="Path to Tesseract executable",
    )
    tesseract_lang: str = Field(
        default="heb+eng",
        description="Tesseract language codes",
    )

    # Application Settings
    log_level: str = Field(default="INFO")
    output_format: OutputFormat = Field(default=OutputFormat.JSON)

    # Paths
    data_dir: Path = Field(
        default=Path("data"),
        description="Directory for data files",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the current settings instance."""
    return settings
