"""
Dynamic rate fetcher for Israeli labor law rates.

Fetches current rates from official government sources (btl.gov.il) and caches them.
Falls back to hardcoded values if fetching fails.
"""

import json
import os
import re
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error
import ssl

from src.logging_config import get_logger

logger = get_logger("validator.rate_fetcher")

# Cache file location
CACHE_DIR = Path("/tmp/salary_validator_cache")
RATES_CACHE_FILE = CACHE_DIR / "rates_cache.json"
CACHE_EXPIRY_HOURS = 24  # Refresh rates daily


@dataclass
class DynamicRates:
    """Current rates fetched from official sources."""

    # Minimum wage
    minimum_wage_monthly: Decimal
    minimum_wage_hourly: Decimal
    minimum_wage_effective_date: str

    # National Insurance (employee rates)
    ni_lower_threshold: Decimal
    ni_upper_threshold: Decimal
    ni_employee_rate_lower: Decimal  # Rate for income up to threshold
    ni_employee_rate_upper: Decimal  # Rate for income above threshold

    # Health Tax
    health_tax_lower_threshold: Decimal
    health_tax_upper_threshold: Decimal
    health_tax_rate_lower: Decimal
    health_tax_rate_upper: Decimal

    # Pension rates
    pension_employee_rate: Decimal
    pension_employer_rate: Decimal

    # Metadata
    last_updated: str
    source: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {k: str(v) for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict) -> "DynamicRates":
        """Create from dictionary."""
        return cls(
            minimum_wage_monthly=Decimal(data["minimum_wage_monthly"]),
            minimum_wage_hourly=Decimal(data["minimum_wage_hourly"]),
            minimum_wage_effective_date=data["minimum_wage_effective_date"],
            ni_lower_threshold=Decimal(data["ni_lower_threshold"]),
            ni_upper_threshold=Decimal(data["ni_upper_threshold"]),
            ni_employee_rate_lower=Decimal(data["ni_employee_rate_lower"]),
            ni_employee_rate_upper=Decimal(data["ni_employee_rate_upper"]),
            health_tax_lower_threshold=Decimal(data["health_tax_lower_threshold"]),
            health_tax_upper_threshold=Decimal(data["health_tax_upper_threshold"]),
            health_tax_rate_lower=Decimal(data["health_tax_rate_lower"]),
            health_tax_rate_upper=Decimal(data["health_tax_rate_upper"]),
            pension_employee_rate=Decimal(data["pension_employee_rate"]),
            pension_employer_rate=Decimal(data["pension_employer_rate"]),
            last_updated=data["last_updated"],
            source=data["source"],
        )


# Default/fallback rates (updated December 2024)
DEFAULT_RATES = DynamicRates(
    # Minimum wage as of April 2025
    minimum_wage_monthly=Decimal("6247.67"),
    minimum_wage_hourly=Decimal("34.32"),
    minimum_wage_effective_date="2025-04-01",

    # National Insurance 2025
    ni_lower_threshold=Decimal("7522"),
    ni_upper_threshold=Decimal("50695"),
    ni_employee_rate_lower=Decimal("0.004"),  # 0.4%
    ni_employee_rate_upper=Decimal("0.07"),   # 7%

    # Health Tax 2025 (updated rates from Feb 2025)
    health_tax_lower_threshold=Decimal("7522"),
    health_tax_upper_threshold=Decimal("50695"),
    health_tax_rate_lower=Decimal("0.0323"),  # 3.23%
    health_tax_rate_upper=Decimal("0.0517"),  # 5.17%

    # Pension rates (unchanged since 2017)
    pension_employee_rate=Decimal("0.06"),   # 6%
    pension_employer_rate=Decimal("0.065"),  # 6.5%

    last_updated="2024-12-14",
    source="hardcoded_fallback",
)


def _fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch URL content with timeout."""
    try:
        # Create SSL context that doesn't verify certificates (for government sites)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SalaryValidator/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def _extract_number(text: str, pattern: str) -> Optional[Decimal]:
    """Extract a number from text using regex pattern."""
    match = re.search(pattern, text)
    if match:
        num_str = match.group(1).replace(",", "").replace(" ", "")
        try:
            return Decimal(num_str)
        except:
            pass
    return None


def _fetch_minimum_wage() -> tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
    """
    Fetch current minimum wage from official source.
    Returns: (monthly_wage, hourly_wage, effective_date) or (None, None, None) on failure
    """
    # Try gov.il minimum wage page
    urls = [
        "https://www.gov.il/he/departments/general/minimum_wage",
        "https://www.btl.gov.il/English%20Homepage/Mediniyut/GeneralInformation/Pages/MinimumWage.aspx",
    ]

    for url in urls:
        content = _fetch_url(url)
        if not content:
            continue

        # Look for patterns like "6,247.67" or "6247.67" for monthly wage
        # Hebrew: שכר מינימום חודשי
        monthly_patterns = [
            r"(?:minimum.*?monthly.*?|שכר.*?מינימום.*?חודשי)[^\d]*(\d[\d,\.]+)",
            r"(\d{1},?\d{3}(?:\.\d{2})?)\s*(?:ש[\"׳]ח|ILS|NIS)",
            r"NIS\s*(\d[\d,\.]+)",
        ]

        for pattern in monthly_patterns:
            monthly = _extract_number(content, pattern)
            if monthly and 5000 < monthly < 10000:  # Sanity check
                # Calculate hourly from monthly (182 hours standard)
                hourly = (monthly / Decimal("182")).quantize(Decimal("0.01"))
                logger.info(f"Fetched minimum wage: {monthly}/month, {hourly}/hour")
                return monthly, hourly, datetime.now().strftime("%Y-%m-%d")

    return None, None, None


def _fetch_ni_rates() -> dict:
    """
    Fetch National Insurance rates from btl.gov.il.
    Returns dict with rates or empty dict on failure.
    """
    url = "https://www.btl.gov.il/English%20Homepage/Insurance/National%20Insurance/Pages/default.aspx"
    content = _fetch_url(url)

    result = {}
    if not content:
        return result

    # Look for threshold values
    threshold_pattern = r"(\d{1},?\d{3})\s*(?:ILS|NIS|ש)"
    thresholds = re.findall(threshold_pattern, content)
    for t in thresholds:
        val = Decimal(t.replace(",", ""))
        if 7000 < val < 8000:  # Lower threshold (60% of avg wage)
            result["ni_lower_threshold"] = val
        elif 45000 < val < 55000:  # Upper threshold
            result["ni_upper_threshold"] = val

    # Look for percentage rates
    rate_patterns = [
        (r"0\.4\s*%", "ni_employee_rate_lower", Decimal("0.004")),
        (r"7\s*%", "ni_employee_rate_upper", Decimal("0.07")),
    ]

    for pattern, key, value in rate_patterns:
        if re.search(pattern, content):
            result[key] = value

    return result


def _fetch_health_tax_rates() -> dict:
    """
    Fetch Health Tax rates from btl.gov.il.
    Returns dict with rates or empty dict on failure.
    """
    url = "https://www.btl.gov.il/English%20Homepage/Insurance/Health%20Insurance/Pages/Healthinsurancerates.aspx"
    content = _fetch_url(url)

    result = {}
    if not content:
        return result

    # Look for percentage rates - updated rates as of 2025
    # 3.23% for lower bracket, 5.17% for upper bracket
    lower_rate_match = re.search(r"3\.23\s*%", content)
    upper_rate_match = re.search(r"5\.17\s*%", content)

    if lower_rate_match:
        result["health_tax_rate_lower"] = Decimal("0.0323")
    if upper_rate_match:
        result["health_tax_rate_upper"] = Decimal("0.0517")

    # Try older rates if new ones not found
    if "health_tax_rate_lower" not in result:
        if re.search(r"3\.1\s*%", content):
            result["health_tax_rate_lower"] = Decimal("0.031")
    if "health_tax_rate_upper" not in result:
        if re.search(r"5\s*%", content):
            result["health_tax_rate_upper"] = Decimal("0.05")

    # Threshold
    threshold_match = re.search(r"(\d{1},?\d{3})\s*(?:\(as of|ILS|NIS)", content)
    if threshold_match:
        val = Decimal(threshold_match.group(1).replace(",", ""))
        if 7000 < val < 8000:
            result["health_tax_lower_threshold"] = val
            result["health_tax_upper_threshold"] = Decimal("50695")  # Max insurable

    return result


def fetch_current_rates(force_refresh: bool = False) -> DynamicRates:
    """
    Fetch current rates from official sources, with caching.

    Args:
        force_refresh: If True, ignore cache and fetch fresh data

    Returns:
        DynamicRates with current values (falls back to defaults on failure)
    """
    # Check cache first
    if not force_refresh:
        cached = _load_from_cache()
        if cached:
            return cached

    logger.info("Fetching fresh rates from official sources...")

    # Start with defaults
    rates_dict = DEFAULT_RATES.to_dict()
    rates_dict["source"] = "mixed"
    updated_fields = []

    # Try to fetch minimum wage
    monthly, hourly, eff_date = _fetch_minimum_wage()
    if monthly and hourly:
        rates_dict["minimum_wage_monthly"] = str(monthly)
        rates_dict["minimum_wage_hourly"] = str(hourly)
        rates_dict["minimum_wage_effective_date"] = eff_date or rates_dict["minimum_wage_effective_date"]
        updated_fields.append("minimum_wage")

    # Try to fetch NI rates
    ni_rates = _fetch_ni_rates()
    for key, value in ni_rates.items():
        rates_dict[key] = str(value)
        updated_fields.append(key)

    # Try to fetch Health Tax rates
    ht_rates = _fetch_health_tax_rates()
    for key, value in ht_rates.items():
        rates_dict[key] = str(value)
        updated_fields.append(key)

    # Update metadata
    rates_dict["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if updated_fields:
        rates_dict["source"] = f"btl.gov.il (updated: {', '.join(updated_fields)})"
    else:
        rates_dict["source"] = "hardcoded_fallback"

    result = DynamicRates.from_dict(rates_dict)

    # Save to cache
    _save_to_cache(result)

    logger.info(f"Rates updated: {result.source}")
    return result


def _load_from_cache() -> Optional[DynamicRates]:
    """Load rates from cache if valid."""
    try:
        if not RATES_CACHE_FILE.exists():
            return None

        # Check if cache is expired
        cache_age_hours = (time.time() - RATES_CACHE_FILE.stat().st_mtime) / 3600
        if cache_age_hours > CACHE_EXPIRY_HOURS:
            logger.debug("Cache expired")
            return None

        with open(RATES_CACHE_FILE, "r") as f:
            data = json.load(f)

        rates = DynamicRates.from_dict(data)
        logger.debug(f"Loaded rates from cache (age: {cache_age_hours:.1f}h)")
        return rates

    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


def _save_to_cache(rates: DynamicRates) -> None:
    """Save rates to cache file."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(RATES_CACHE_FILE, "w") as f:
            json.dump(rates.to_dict(), f, indent=2)
        logger.debug("Saved rates to cache")
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")


def get_rates_info() -> dict:
    """
    Get current rates info for display in UI.
    Returns dict with rates and metadata.
    """
    rates = fetch_current_rates()
    return {
        "minimum_wage": {
            "monthly": float(rates.minimum_wage_monthly),
            "hourly": float(rates.minimum_wage_hourly),
            "effective_date": rates.minimum_wage_effective_date,
        },
        "national_insurance": {
            "lower_threshold": float(rates.ni_lower_threshold),
            "upper_threshold": float(rates.ni_upper_threshold),
            "employee_rate_lower": f"{float(rates.ni_employee_rate_lower) * 100:.1f}%",
            "employee_rate_upper": f"{float(rates.ni_employee_rate_upper) * 100:.0f}%",
        },
        "health_tax": {
            "lower_threshold": float(rates.health_tax_lower_threshold),
            "upper_threshold": float(rates.health_tax_upper_threshold),
            "rate_lower": f"{float(rates.health_tax_rate_lower) * 100:.2f}%",
            "rate_upper": f"{float(rates.health_tax_rate_upper) * 100:.2f}%",
        },
        "pension": {
            "employee_rate": f"{float(rates.pension_employee_rate) * 100:.0f}%",
            "employer_rate": f"{float(rates.pension_employer_rate) * 100:.1f}%",
        },
        "metadata": {
            "last_updated": rates.last_updated,
            "source": rates.source,
        }
    }


# Global cached rates instance
_cached_rates: Optional[DynamicRates] = None


def get_current_rates() -> DynamicRates:
    """Get current rates (cached in memory for performance)."""
    global _cached_rates
    if _cached_rates is None:
        _cached_rates = fetch_current_rates()
    return _cached_rates


def refresh_rates() -> DynamicRates:
    """Force refresh rates from sources."""
    global _cached_rates
    _cached_rates = fetch_current_rates(force_refresh=True)
    return _cached_rates
