"""Main payslip validator that runs all rules."""

from typing import Optional

from src.logging_config import get_logger
from src.models import Payslip, PayslipAnalysis, Violation
from src.validator.base import ValidationRule
from src.validator.rules import (
    EmployerPensionRule,
    HoursRateRule,
    MinimumWageRule,
    OvertimeCalculationRule,
    PensionContributionRule,
    NationalInsuranceRule,
    HealthTaxRule,
    SeveranceFundRule,
)

logger = get_logger("validator.payslip_validator")


class RuleRegistry:
    """Registry for validation rules."""

    def __init__(self):
        """Initialize with empty rule list."""
        self._rules: list[ValidationRule] = []

    def register(self, rule: ValidationRule) -> None:
        """Register a validation rule."""
        self._rules.append(rule)
        logger.debug(f"Registered rule: {rule.name}")

    def unregister(self, rule_name: str) -> bool:
        """Unregister a rule by name."""
        for i, rule in enumerate(self._rules):
            if rule.name == rule_name:
                del self._rules[i]
                logger.debug(f"Unregistered rule: {rule_name}")
                return True
        return False

    def get_rules(self) -> list[ValidationRule]:
        """Get all registered rules."""
        return self._rules.copy()

    def clear(self) -> None:
        """Remove all rules."""
        self._rules.clear()


# Default rule registry with all standard rules
def create_default_registry() -> RuleRegistry:
    """Create a registry with all default validation rules."""
    registry = RuleRegistry()

    # Core rules (initial scope)
    registry.register(MinimumWageRule())
    registry.register(HoursRateRule())
    registry.register(PensionContributionRule())

    # Additional rules
    registry.register(OvertimeCalculationRule())
    registry.register(EmployerPensionRule())

    # Social insurance rules
    registry.register(NationalInsuranceRule())
    registry.register(HealthTaxRule())
    registry.register(SeveranceFundRule())

    return registry


class PayslipValidator:
    """Validator for checking payslips against labor law rules."""

    def __init__(self, registry: Optional[RuleRegistry] = None):
        """
        Initialize the validator.

        Args:
            registry: Rule registry to use (default: all standard rules)
        """
        self.registry = registry or create_default_registry()

    def validate(self, payslip: Payslip) -> PayslipAnalysis:
        """
        Validate a payslip against all registered rules.

        Args:
            payslip: The payslip to validate

        Returns:
            PayslipAnalysis with all found violations
        """
        logger.info(f"Validating payslip for {payslip.payslip_date}")

        violations: list[Violation] = []

        for rule in self.registry.get_rules():
            # Check if rule is applicable
            if not rule.is_applicable(payslip):
                logger.debug(f"Rule '{rule.name}' not applicable, skipping")
                continue

            # Run validation
            try:
                violation = rule.validate(payslip)
                if violation is not None:
                    violations.append(violation)
                    logger.info(f"Violation found: {rule.name}")
            except Exception as e:
                logger.error(f"Error running rule '{rule.name}': {e}")

        # Create analysis result
        analysis = PayslipAnalysis(
            payslip=payslip,
            violations=violations,
        )
        analysis.calculate_totals()

        logger.info(
            f"Validation complete: {len(violations)} violations, "
            f"missing amount: ₪{analysis.total_missing}"
        )

        return analysis

    def validate_single_rule(
        self, payslip: Payslip, rule_name: str
    ) -> Optional[Violation]:
        """
        Validate a payslip against a single rule by name.

        Args:
            payslip: The payslip to validate
            rule_name: Name of the rule to run

        Returns:
            Violation if found, None otherwise
        """
        for rule in self.registry.get_rules():
            if rule.name == rule_name:
                if rule.is_applicable(payslip):
                    return rule.validate(payslip)
                return None

        logger.warning(f"Rule not found: {rule_name}")
        return None

    def get_rule_names(self) -> list[str]:
        """Get names of all registered rules."""
        return [rule.name for rule in self.registry.get_rules()]


def validate_payslip(payslip: Payslip) -> PayslipAnalysis:
    """
    Convenience function to validate a payslip with default rules.

    Args:
        payslip: The payslip to validate

    Returns:
        PayslipAnalysis with all found violations
    """
    validator = PayslipValidator()
    return validator.validate(payslip)
