"""Base interface for validation rules."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from src.models import Payslip, Violation, ViolationType


class ViolationSeverity(str, Enum):
    """Severity level of a violation."""

    LOW = "low"  # Minor issue, informational
    MEDIUM = "medium"  # Should be addressed
    HIGH = "high"  # Significant violation
    CRITICAL = "critical"  # Severe legal violation


class ValidationRule(ABC):
    """Abstract base class for validation rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the rule."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this rule checks."""
        pass

    @property
    @abstractmethod
    def violation_type(self) -> ViolationType:
        """The type of violation this rule detects."""
        pass

    @property
    def severity(self) -> ViolationSeverity:
        """Default severity for violations from this rule."""
        return ViolationSeverity.MEDIUM

    @property
    def legal_reference(self) -> Optional[str]:
        """Reference to relevant law or regulation."""
        return None

    @abstractmethod
    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """
        Validate a payslip against this rule.

        Args:
            payslip: The payslip to validate

        Returns:
            Violation if rule is violated, None if compliant
        """
        pass

    def is_applicable(self, payslip: Payslip) -> bool:
        """
        Check if this rule is applicable to the given payslip.

        Override this method to skip validation for certain payslips.

        Args:
            payslip: The payslip to check

        Returns:
            True if rule should be applied
        """
        return True


class ValidationError(Exception):
    """Exception raised when validation process fails."""

    pass
