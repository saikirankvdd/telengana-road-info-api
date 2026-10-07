import re
import logging
from typing import Optional, Any, Dict, List, Tuple
from datetime import datetime

from backend.schemas.data_quality import (
    QualitySeverity,
    QualityStatus,
    ValidationIssue
)

logger = logging.getLogger(__name__)

# Standard placeholder strings that indicate missing/invalid data
PLACEHOLDER_VALUES = {
    "n/a", "na", "unknown", "not available", "null", "none",
    "undefined", "tbd", "to be decided", "nil", "not applicable",
    "-", "--", "???", "no data"
}

# Telangana approximate bounding box for spatial sanity warnings
TELANGANA_LAT_MIN, TELANGANA_LAT_MAX = 15.0, 20.5
TELANGANA_LON_MIN, TELANGANA_LON_MAX = 76.5, 82.0


class FieldValidator:
    """
    Performs field-level validations on strings, numbers, financial amounts,
    geographic coordinates, dates, and identifiers.
    """

    @staticmethod
    def validate_string(field_name: str, value: Any) -> Tuple[QualityStatus, List[ValidationIssue], Optional[str]]:
        """
        Validates string fields for placeholders, whitespace-only values, and normalization.
        """
        issues: List[ValidationIssue] = []
        if value is None:
            return QualityStatus.VALID, issues, None

        if not isinstance(value, str):
            value_str = str(value)
        else:
            value_str = value

        stripped = value_str.strip()
        if not stripped:
            issues.append(ValidationIssue(
                field_name=field_name,
                rule_name="EMPTY_STRING",
                severity=QualitySeverity.WARNING,
                description=f"Field '{field_name}' contains empty or whitespace-only value",
                current_value=value
            ))
            return QualityStatus.INVALID, issues, None

        lowered = stripped.lower()
        if lowered in PLACEHOLDER_VALUES:
            issues.append(ValidationIssue(
                field_name=field_name,
                rule_name="PLACEHOLDER_STRING",
                severity=QualitySeverity.WARNING,
                description=f"Field '{field_name}' contains suspicious placeholder '{stripped}'",
                current_value=value
            ))
            return QualityStatus.INVALID, issues, None

        # Normalized string for comparison purposes
        normalized = re.sub(r'\s+', ' ', stripped)
        return QualityStatus.VALID, issues, normalized

    @staticmethod
    def validate_financial(
        field_name: str,
        value: Any,
        estimated_cost: Optional[float] = None
    ) -> Tuple[QualityStatus, List[ValidationIssue]]:
        """
        Validates financial fields (estimated_cost, awarded_cost).
        """
        issues: List[ValidationIssue] = []
        if value is None:
            return QualityStatus.VALID, issues

        try:
            val_float = float(value)
        except (ValueError, TypeError):
            issues.append(ValidationIssue(
                field_name=field_name,
                rule_name="NON_NUMERIC_COST",
                severity=QualitySeverity.ERROR,
                description=f"Field '{field_name}' value '{value}' is not a valid number",
                current_value=value
            ))
            return QualityStatus.INVALID, issues

        if val_float < 0:
            issues.append(ValidationIssue(
                field_name=field_name,
                rule_name="NEGATIVE_COST",
                severity=QualitySeverity.ERROR,
                description=f"Field '{field_name}' cost cannot be negative ({val_float})",
                current_value=value
            ))
            return QualityStatus.INVALID, issues

        # Unrealistic cost check (e.g., > 50,000 crore)
        if val_float > 50000.0:
            issues.append(ValidationIssue(
                field_name=field_name,
                rule_name="UNREALISTIC_HIGH_COST",
                severity=QualitySeverity.WARNING,
                description=f"Field '{field_name}' value ₹{val_float} crore is extraordinarily high",
                current_value=value
            ))
            return QualityStatus.SUSPICIOUS, issues

        # Awarded cost significantly exceeding estimated cost check
        if field_name == "awarded_cost" and estimated_cost is not None and estimated_cost > 0:
            if val_float > estimated_cost * 2.0:
                issues.append(ValidationIssue(
                    field_name=field_name,
                    rule_name="AWARDED_EXCEEDS_ESTIMATED",
                    severity=QualitySeverity.WARNING,
                    description=f"Awarded cost (₹{val_float} Cr) significantly exceeds estimated cost (₹{estimated_cost} Cr)",
                    current_value=value
                ))
                return QualityStatus.SUSPICIOUS, issues

        return QualityStatus.VALID, issues

    @staticmethod
    def validate_geographic(
        lat: Optional[Any],
        lon: Optional[Any],
        road_length_km: Optional[Any] = None
    ) -> Tuple[Dict[str, QualityStatus], List[ValidationIssue]]:
        """
        Validates latitude, longitude, and road length.
        """
        issues: List[ValidationIssue] = []
        statuses = {
            "latitude": QualityStatus.VALID,
            "longitude": QualityStatus.VALID,
            "road_length_km": QualityStatus.VALID
        }

        # Validate Latitude
        if lat is not None:
            try:
                lat_float = float(lat)
                if lat_float < -90.0 or lat_float > 90.0:
                    statuses["latitude"] = QualityStatus.INVALID
                    issues.append(ValidationIssue(
                        field_name="latitude",
                        rule_name="INVALID_LATITUDE_RANGE",
                        severity=QualitySeverity.ERROR,
                        description=f"Latitude {lat_float} is outside legal range [-90, +90]",
                        current_value=lat
                    ))
                elif lat_float < TELANGANA_LAT_MIN or lat_float > TELANGANA_LAT_MAX:
                    statuses["latitude"] = QualityStatus.SUSPICIOUS
                    issues.append(ValidationIssue(
                        field_name="latitude",
                        rule_name="OUTSIDE_STATE_BOUNDS",
                        severity=QualitySeverity.WARNING,
                        description=f"Latitude {lat_float} is outside typical Telangana boundaries",
                        current_value=lat
                    ))
            except (ValueError, TypeError):
                statuses["latitude"] = QualityStatus.INVALID
                issues.append(ValidationIssue(
                    field_name="latitude",
                    rule_name="MALFORMED_LATITUDE",
                    severity=QualitySeverity.ERROR,
                    description=f"Latitude value '{lat}' is not a valid number",
                    current_value=lat
                ))

        # Validate Longitude
        if lon is not None:
            try:
                lon_float = float(lon)
                if lon_float < -180.0 or lon_float > 180.0:
                    statuses["longitude"] = QualityStatus.INVALID
                    issues.append(ValidationIssue(
                        field_name="longitude",
                        rule_name="INVALID_LONGITUDE_RANGE",
                        severity=QualitySeverity.ERROR,
                        description=f"Longitude {lon_float} is outside legal range [-180, +180]",
                        current_value=lon
                    ))
                elif lon_float < TELANGANA_LON_MIN or lon_float > TELANGANA_LON_MAX:
                    statuses["longitude"] = QualityStatus.SUSPICIOUS
                    issues.append(ValidationIssue(
                        field_name="longitude",
                        rule_name="OUTSIDE_STATE_BOUNDS",
                        severity=QualitySeverity.WARNING,
                        description=f"Longitude {lon_float} is outside typical Telangana boundaries",
                        current_value=lon
                    ))
            except (ValueError, TypeError):
                statuses["longitude"] = QualityStatus.INVALID
                issues.append(ValidationIssue(
                    field_name="longitude",
                    rule_name="MALFORMED_LONGITUDE",
                    severity=QualitySeverity.ERROR,
                    description=f"Longitude value '{lon}' is not a valid number",
                    current_value=lon
                ))

        # Validate Road Length
        if road_length_km is not None:
            try:
                len_float = float(road_length_km)
                if len_float < 0:
                    statuses["road_length_km"] = QualityStatus.INVALID
                    issues.append(ValidationIssue(
                        field_name="road_length_km",
                        rule_name="NEGATIVE_ROAD_LENGTH",
                        severity=QualitySeverity.ERROR,
                        description=f"Road length cannot be negative ({len_float} km)",
                        current_value=road_length_km
                    ))
                elif len_float > 2000.0:
                    statuses["road_length_km"] = QualityStatus.SUSPICIOUS
                    issues.append(ValidationIssue(
                        field_name="road_length_km",
                        rule_name="UNREALISTIC_ROAD_LENGTH",
                        severity=QualitySeverity.WARNING,
                        description=f"Road length {len_float} km is unusually large",
                        current_value=road_length_km
                    ))
            except (ValueError, TypeError):
                statuses["road_length_km"] = QualityStatus.INVALID
                issues.append(ValidationIssue(
                    field_name="road_length_km",
                    rule_name="MALFORMED_ROAD_LENGTH",
                    severity=QualitySeverity.ERROR,
                    description=f"Road length value '{road_length_km}' is not a valid number",
                    current_value=road_length_km
                ))

        return statuses, issues

    @staticmethod
    def parse_date(date_val: Any) -> Optional[datetime]:
        """Utility to safely parse dates from string or datetime objects."""
        if not date_val:
            return None
        if isinstance(date_val, datetime):
            return date_val
        date_str = str(date_val).strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str[:10] if "T" in date_str else date_str, fmt[:10])
            except ValueError:
                continue
        return None

    @staticmethod
    def validate_date_sequence(
        pub_date_val: Optional[Any],
        sub_deadline_val: Optional[Any],
        award_date_val: Optional[Any] = None,
        start_date_val: Optional[Any] = None,
        end_date_val: Optional[Any] = None
    ) -> List[ValidationIssue]:
        """
        Validates chronological order across project date fields.
        """
        issues: List[ValidationIssue] = []

        pub_date = FieldValidator.parse_date(pub_date_val)
        sub_deadline = FieldValidator.parse_date(sub_deadline_val)
        award_date = FieldValidator.parse_date(award_date_val)
        start_date = FieldValidator.parse_date(start_date_val)
        end_date = FieldValidator.parse_date(end_date_val)

        # Rule 1: Submission deadline cannot precede publication date
        if pub_date and sub_deadline and sub_deadline < pub_date:
            issues.append(ValidationIssue(
                field_name="submission_deadline",
                rule_name="DEADLINE_BEFORE_PUBLICATION",
                severity=QualitySeverity.ERROR,
                description=f"Submission deadline ({sub_deadline.strftime('%Y-%m-%d')}) precedes publication date ({pub_date.strftime('%Y-%m-%d')})",
                current_value=str(sub_deadline_val)
            ))

        # Rule 2: Award date should not precede publication date
        if pub_date and award_date and award_date < pub_date:
            issues.append(ValidationIssue(
                field_name="awarded_date",
                rule_name="AWARD_BEFORE_PUBLICATION",
                severity=QualitySeverity.ERROR,
                description=f"Award date ({award_date.strftime('%Y-%m-%d')}) precedes publication date ({pub_date.strftime('%Y-%m-%d')})",
                current_value=str(award_date_val)
            ))

        # Rule 3: Contract end date cannot precede start date
        if start_date and end_date and end_date < start_date:
            issues.append(ValidationIssue(
                field_name="contract_end_date",
                rule_name="END_BEFORE_START_DATE",
                severity=QualitySeverity.ERROR,
                description=f"Contract end date ({end_date.strftime('%Y-%m-%d')}) precedes start date ({start_date.strftime('%Y-%m-%d')})",
                current_value=str(end_date_val)
            ))

        return issues
