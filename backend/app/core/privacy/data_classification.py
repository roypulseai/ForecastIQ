from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SensitivityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class DataCategory(str, Enum):
    PII = "pii"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    PUBLIC = "public"
    ANONYMOUS = "anonymous"
    SPECIAL = "special"


DATA_CLASSIFICATION_CONFIG = {
    DataCategory.PII: {
        "sensitivity": SensitivityLevel.HIGH,
        "encryption": "required",
        "access_control": "strict",
        "audit_log": "required",
        "retention": "minimum_necessary",
        "examples": [
            "Names",
            "Email addresses",
            "Phone numbers",
            "IP addresses",
            "Device identifiers",
        ],
    },
    DataCategory.FINANCIAL: {
        "sensitivity": SensitivityLevel.HIGH,
        "encryption": "required",
        "access_control": "strict",
        "audit_log": "required",
        "retention": "7_years",
        "examples": [
            "Sales revenue",
            "Transaction amounts",
            "Payment information",
            "Invoice data",
        ],
    },
    DataCategory.OPERATIONAL: {
        "sensitivity": SensitivityLevel.MEDIUM,
        "encryption": "recommended",
        "access_control": "standard",
        "audit_log": "recommended",
        "retention": "3_years",
        "examples": [
            "Inventory levels",
            "Supply chain data",
            "Product SKUs",
            "Store locations",
        ],
    },
    DataCategory.PUBLIC: {
        "sensitivity": SensitivityLevel.LOW,
        "encryption": "optional",
        "access_control": "standard",
        "audit_log": "optional",
        "retention": "indefinite",
        "examples": [
            "Marketing materials",
            "Press releases",
            "Product listings",
        ],
    },
    DataCategory.ANONYMOUS: {
        "sensitivity": SensitivityLevel.NONE,
        "encryption": "optional",
        "access_control": "standard",
        "audit_log": "optional",
        "retention": "unlimited",
        "examples": [
            "Aggregated analytics",
            "Statistical summaries",
            "Anonymized forecasts",
        ],
    },
    DataCategory.SPECIAL: {
        "sensitivity": SensitivityLevel.HIGH,
        "encryption": "required",
        "access_control": "strict",
        "audit_log": "required",
        "retention": "minimum_necessary",
        "legal_basis_required": "explicit_consent",
        "examples": [
            "Genetic data",
            "Biometric data",
            "Health data",
            "Political opinions",
            "Religious beliefs",
        ],
    },
}


class DataClassification(BaseModel):
    category: DataCategory
    sensitivity: SensitivityLevel
    requires_encryption: bool
    access_control_level: str
    audit_log_required: bool
    retention_period: str
    examples: List[str] = []
    legal_basis_required: Optional[str] = None


class ClassifiedDataField(BaseModel):
    field_name: str
    category: DataCategory
    is_identifier: bool = False
    is_special_category: bool = False
    custom_retention_days: Optional[int] = None


class DataClassifier:
    def __init__(self):
        self._field_mappings: Dict[str, DataClassification] = {}

    def register_field(self, field: ClassifiedDataField) -> None:
        config = DATA_CLASSIFICATION_CONFIG[field.category]
        self._field_mappings[field.field_name] = DataClassification(
            category=field.category,
            sensitivity=config["sensitivity"],
            requires_encryption=config["encryption"] == "required",
            access_control_level=config["access_control"],
            audit_log_required=config["audit_log"] == "required",
            retention_period=config["retention"],
            examples=config.get("examples", []),
            legal_basis_required=config.get("legal_basis_required"),
        )

    def classify_data(self, data: Dict[str, Any]) -> Dict[str, DataClassification]:
        result = {}
        for field_name in data.keys():
            if field_name in self._field_mappings:
                result[field_name] = self._field_mappings[field_name]
            else:
                result[field_name] = self._auto_classify(field_name, data[field_name])
        return result

    def _auto_classify(self, field_name: str, value: Any) -> DataClassification:
        field_lower = field_name.lower()

        pii_indicators = ["name", "email", "phone", "address", "ip", "user", "customer"]
        financial_indicators = ["price", "cost", "revenue", "sales", "amount", "payment"]
        operational_indicators = ["sku", "product", "inventory", "stock", "store"]

        if any(indicator in field_lower for indicator in pii_indicators):
            category = DataCategory.PII
        elif any(indicator in field_lower for indicator in financial_indicators):
            category = DataCategory.FINANCIAL
        elif any(indicator in field_lower for indicator in operational_indicators):
            category = DataCategory.OPERATIONAL
        else:
            category = DataCategory.PUBLIC

        config = DATA_CLASSIFICATION_CONFIG[category]
        return DataClassification(
            category=category,
            sensitivity=config["sensitivity"],
            requires_encryption=config["encryption"] == "required",
            access_control_level=config["access_control"],
            audit_log_required=config["audit_log"] == "required",
            retention_period=config["retention"],
            examples=config.get("examples", []),
        )

    def get_data_inventory(self) -> List[Dict[str, Any]]:
        return [
            {
                "field_name": field_name,
                "category": classification.category.value,
                "sensitivity": classification.sensitivity.value,
                "encryption_required": classification.requires_encryption,
            }
            for field_name, classification in self._field_mappings.items()
        ]

    def requires_encryption(self, field_name: str) -> bool:
        if field_name in self._field_mappings:
            return self._field_mappings[field_name].requires_encryption
        classification = self._auto_classify(field_name, None)
        return classification.requires_encryption

    def get_retention_period(self, field_name: str) -> str:
        if field_name in self._field_mappings:
            return self._field_mappings[field_name].retention_period
        classification = self._auto_classify(field_name, None)
        return classification.retention_period
