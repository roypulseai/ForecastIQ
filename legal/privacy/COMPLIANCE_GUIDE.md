# Data Privacy Compliance Guide

**ForecastIQ** is committed to data privacy compliance across multiple jurisdictions. This document outlines the privacy requirements for operating in the USA, European Union, Switzerland, and India.

---

## Table of Contents
1. [Jurisdiction Overview](#jurisdiction-overview)
2. [USA Privacy Requirements](#usa-privacy-requirements)
3. [European Union (GDPR)](#european-union-gdpr)
4. [Switzerland (FADP)](#switzerland-fadp)
5. [India (PDPA)](#india-pdpa)
6. [Data Classification](#data-classification)
7. [Consent Management](#consent-management)
8. [Data Retention Requirements](#data-retention-requirements)
9. [Data Subject Rights](#data-subject-rights)
10. [Breach Notification](#breach-notification)
11. [Implementation Checklist](#implementation-checklist)

---

## Jurisdiction Overview

| Jurisdiction | Primary Law | Regulator | Key Focus |
|--------------|-------------|-----------|-----------|
| USA | Sector-specific (CCPA, HIPAA, GLBA) | FTC, State AGs | Notice, Choice, Security |
| European Union | GDPR | EDPS, DPAs | Lawfulness, Consent, Rights |
| Switzerland | FADP (revised 2023) | FDPIC | Transparency, Proportionality |
| India | DPDP Act 2023 | Data Protection Board | Consent, Purpose Limitation |

---

## USA Privacy Requirements

### Applicable Laws
- **CCPA/CPRA** (California) - Consumer rights, opt-out of sale
- **VCDPA** (Virginia), **CPA** (Colorado), **CTDPA** (Connecticut) - Similar to CCPA
- **HIPAA** (Healthcare) - PHI protection if applicable
- **GLBA** (Financial) - Financial data protection if applicable

### Key Requirements

#### 1. Notice & Disclosure
```
- Privacy policy must be publicly available
- Categories of data collected must be disclosed
- Purpose of data collection must be stated
- Third-party sharing practices must be outlined
```

#### 2. Consumer Rights (CCPA)
| Right | Description | Response Time |
|-------|-------------|---------------|
| Right to Know | Access personal data collected | 45 days |
| Right to Delete | Request data deletion | 45 days |
| Right to Opt-Out | Stop sale of personal data | 15 days (sale opt-out) |
| Right to Correct | Correct inaccurate data | 45 days |
| Right to Non-Discrimination | Equal service for exercising rights | Immediate |

#### 3. Data Security
- Implement reasonable security measures (NIST guidelines)
- Encrypt sensitive data at rest and in transit
- Conduct regular security assessments
- Maintain incident response procedures

#### 4. Sale of Data
- Provide opt-out mechanism for data sale
- Honor "Do Not Sell My Personal Information" requests
- Verify age (13-16) before sale to minors

### Implementation Requirements

```python
# USA Privacy Configuration
USA_PRIVACY_CONFIG = {
    "requires_consent": True,
    "consent_type": "opt_in",  # or "opt_out" for CCPA
    "minor_age": 13,  # COPPA
    "data_retention_days": 2555,  # 7 years for financial records
    "breach_notification_days": [30, 60],  # State-dependent
    "requires_privacy_policy": True,
    "requires_dpo": False,  # Not required at federal level
}
```

---

## European Union (GDPR)

### Key Principles (Article 5)

| Principle | Description |
|-----------|-------------|
| Lawfulness, Fairness, Transparency | Process data legally and openly |
| Purpose Limitation | Collect for specified, explicit purposes |
| Data Minimisation | Only collect necessary data |
| Accuracy | Keep data accurate and up-to-date |
| Storage Limitation | Don't keep longer than necessary |
| Integrity & Confidentiality | Ensure appropriate security |
| Accountability | Demonstrate compliance |

### Legal Bases for Processing (Article 6)

| Legal Basis | Use Case | Consent Required |
|-------------|----------|-----------------|
| Consent | Marketing, profiling | Yes - freely given, specific, informed |
| Contract | Service delivery | No |
| Legal Obligation | Tax, fraud prevention | No |
| Vital Interests | Life-saving measures | No |
| Public Task | Government functions | No |
| Legitimate Interests | Security, fraud prevention | No (but must balance) |

### Special Categories (Article 9)

Processing of special categories requires explicit consent:
- Race, ethnic origin, political opinions
- Religious/philosophical beliefs
- Trade union membership
- Genetic/biometric data
- Health data
- Sexual orientation

### Data Subject Rights

| Right | Article | Description |
|-------|---------|-------------|
| Right to be informed | 13-14 | Transparency about processing |
| Right of access | 15 | Access personal data |
| Right to rectification | 16 | Correct inaccurate data |
| Right to erasure | 17 | "Right to be forgotten" |
| Right to restrict | 18 | Limit processing |
| Right to data portability | 20 | Transfer to another controller |
| Right to object | 21 | Stop processing |
| Rights re: automated decisions | 22 | No solely automated decisions |

### Breach Notification
- **72 hours** to supervisory authority (Article 33)
- Without undue delay to data subjects if high risk (Article 34)

### Implementation Requirements

```python
# EU GDPR Configuration
GDPR_CONFIG = {
    "legal_bases": ["consent", "contract", "legitimate_interest"],
    "requires_consent": True,
    "consent_type": "explicit",
    "requires_dpo": True,  # Data Protection Officer required
    "requires_dpia": True,  # Data Protection Impact Assessment
    "data_retention_days": 730,  # 2 years from last interaction
    "breach_notification_hours": 72,
    "cross_border_transfer": ["SCCs", "Adequacy", "BCRs"],
    "right_to_erasure": True,
    "data_portability": True,
    "automated_decisions": {"allowed": False, "profiling_allowed": False},
}
```

---

## Switzerland (FADP)

### Overview
The revised Federal Act on Data Protection (FADP) came into effect on **September 1, 2023**, aligning more closely with GDPR.

### Key Changes (2023 Revision)
- Extended territorial scope
- Risk-based approach to data protection
- Strengthened rights for data subjects
- Mandatory data protection impact assessments
- Breach notification requirements

### Principles

| Principle | Description |
|-----------|-------------|
| Lawfulness | Processing must have legal basis |
| Good Faith | Fair and transparent processing |
| Proportionality | Only necessary data collection |
| Purpose Limitation | Specified, legitimate purposes |
| Data Minimisation | Adequate, relevant, limited |
| Accuracy | Correct, complete |
| Transparency | Clear information provision |
| Security | Appropriate technical/organizational measures |

### Legal Bases

| Basis | Description |
|-------|-------------|
| Consent | Informed, freely given, unambiguous |
| Contract | Necessary for contract performance |
| Legal Obligation | Federal/ cantonal law requirement |
| Vital Interests | Protection of life |
| Public Task | Public interest or official authority |
| Legitimate Interests | Balancing test required |

### Data Subject Rights

| Right | Description |
|-------|-------------|
| Right to be informed | Identity of controller, purpose, recipients |
| Right to access | Access to stored personal data |
| Right to correction | Correction of inaccurate data |
| Right to deletion | Erasure when no longer needed |
| Right to object | Object to processing |
| Right to data portability | Export data in common format |

### Breach Notification
- **72 hours** to FDPIC for high-risk breaches
- Notification to affected individuals if high risk

### Implementation Requirements

```python
# Switzerland FADP Configuration
FADP_CONFIG = {
    "legal_bases": ["consent", "contract", "legitimate_interest"],
    "requires_consent": True,
    "consent_type": "explicit",
    "requires_dpo": True,  # If processing warrants it
    "data_retention_days": 3650,  # 10 years for business records
    "breach_notification_hours": 72,
    "cross_border_transfer": [" adequacy", "SCCs", "BCRs"],
    "data_subject_rights": ["access", "correction", "deletion", "portability"],
}
```

---

## India (DPDP Act 2023)

### Overview
The Digital Personal Data Protection Act (DPDP) was enacted in August 2023. Rules are still being finalized.

### Key Principles

| Principle | Description |
|-----------|-------------|
| Consent | Freely given, informed, specific, clear |
| Purpose Limitation | Collect for specified, notified purpose |
| Data Minimisation | Only necessary data collection |
| Accuracy | Accuracy, completeness of data |
| Storage Limitation | Retention only as necessary |
| Accountability | Fiduciary responsibility to data principal |

### Consent Requirements

| Element | Requirement |
|---------|-------------|
| Clear affirmative action | Opt-in mechanism |
| Purpose specification | Why data is collected |
| Withdrawal capability | Easy consent withdrawal |
| Child consent | Verified parental consent under 18 |
| Guardian consent | For children, verified guardian |

### Data Principal Rights

| Right | Description |
|-------|-------------|
| Right to access | Information about processing |
| Right to correction | Correct inaccurate/incomplete data |
| Right to erasure | Deletion of data |
| Right to grievance | Address complaints |
| Right to nominate | Nominate heir for data |

### Significant Data Fiduciary
Additional obligations for entities designated as Significant Data Fiduciary by Central Government:
- Data Protection Impact Assessment
- Annual Data Protection Audit
- Resident data storage in India
- Strictersecurity measures

### Implementation Requirements

```python
# India DPDP Act Configuration
DPDP_CONFIG = {
    "requires_consent": True,
    "consent_type": "affirmative",  # Opt-in
    "minor_age": 18,
    "requires_verified_parent": True,  # For minors
    "data_retention_days": 1825,  # 5 years (recommended)
    "requires_consent_manager": True,
    "cross_border_transfer": ["allowed_with_restrictions"],
    "data_localization": {"required": False, "residence_required": True},
    "significant_data_fiduciary": {
        "requires_dpia": True,
        "requires_audit": True,
        "local_storage_required": True,
    },
}
```

---

## Data Classification

ForecastIQ handles multiple data types with different sensitivity levels:

### Data Categories

| Category | Examples | Sensitivity | Retention |
|----------|----------|-------------|-----------|
| PII (Personally Identifiable) | Names, emails, addresses | High | Per jurisdiction |
| Financial | Sales, revenue, transactions | High | 7 years |
| Operational | Inventory, supply chain | Medium | 3 years |
| Public | Marketing, press releases | Low | Indefinite |
| Anonymous | Aggregated analytics | None | Unlimited |

### Data Handling Matrix

```python
DATA_CLASSIFICATION = {
    "pii": {
        "encryption": "required",
        "access_control": "strict",
        "audit_log": "required",
        "retention": "minimum_necessary",
    },
    "financial": {
        "encryption": "required",
        "access_control": "strict",
        "audit_log": "required",
        "retention": "7_years",
    },
    "operational": {
        "encryption": "recommended",
        "access_control": "standard",
        "audit_log": "recommended",
        "retention": "3_years",
    },
    "anonymous": {
        "encryption": "optional",
        "access_control": "standard",
        "audit_log": "optional",
        "retention": "unlimited",
    },
}
```

---

## Consent Management

### Consent Requirements by Jurisdiction

| Jurisdiction | Consent Type | Granularity | Withdrawable | Documented |
|--------------|--------------|-------------|--------------|------------|
| USA (CCPA) | Opt-out | Category | Yes | Yes |
| EU (GDPR) | Explicit | Purpose | Yes | Yes |
| Switzerland | Explicit | Purpose | Yes | Yes |
| India (DPDP) | Affirmative | Purpose | Yes | Yes |

### Consent Record Schema

```python
class ConsentRecord(BaseModel):
    consent_id: str
    user_id: str
    purposes: List[Purpose]
    legal_basis: LegalBasis
    consent_given_at: datetime
    consent_updated_at: datetime
    consent_withdrawn_at: Optional[datetime]
    jurisdiction: Jurisdiction
    ip_address: str
    user_agent: str
    proof: str  # Hash of consent details
```

### Consent Categories in ForecastIQ

```python
CONSENT_CATEGORIES = {
    "essential": {
        "required": True,
        "withdrawable": False,
        "description": "Core platform functionality",
    },
    "analytics": {
        "required": False,
        "withdrawable": True,
        "description": "Usage analytics and improvements",
    },
    "marketing": {
        "required": False,
        "withdrawable": True,
        "description": "Promotional communications",
    },
    "profiling": {
        "required": False,
        "withdrawable": True,
        "description": "Automated decision-making",
    },
    "third_party_sharing": {
        "required": False,
        "withdrawable": True,
        "description": "Sharing with partners",
    },
}
```

---

## Data Retention Requirements

### By Jurisdiction

| Jurisdiction | Financial Data | Customer Data | Logs | Backup |
|--------------|----------------|---------------|------|--------|
| USA | 7 years | Per policy | 90 days | 30 days |
| EU (GDPR) | 6 years | 2 years inactive | 90 days | 30 days |
| Switzerland | 10 years | 5 years inactive | 90 days | 30 days |
| India (DPDP) | 8 years | 5 years | 90 days | 30 days |

### Data Deletion Schedule

```python
RETENTION_POLICY = {
    "active_users": {
        "pii": 365,  # 1 year from last activity
        "financial": 2555,  # 7 years
        "analytics": 730,  # 2 years
    },
    "inactive_users": {
        "pii": 730,  # 2 years
        "financial": 2555,  # 7 years
        "analytics": 180,  # 6 months
    },
    "deleted_users": {
        "pii": 30,  # 30 days after deletion request
        "financial": 2555,  # 7 years (legal hold)
        "analytics": 0,  # Immediate
    },
    "logs": {
        "access": 90,
        "security": 365,
        "audit": 730,
    },
}
```

---

## Data Subject Rights

### Implementation Matrix

| Right | USA | EU | Switzerland | India |
|-------|-----|-----|-------------|-------|
| Access | ✓ | ✓ | ✓ | ✓ |
| Rectification | ✓ | ✓ | ✓ | ✓ |
| Erasure | Limited | ✓ | ✓ | ✓ |
| Restriction | - | ✓ | ✓ | ✓ |
| Portability | - | ✓ | ✓ | ✓ |
| Object | - | ✓ | ✓ | ✓ |
| Automated Decisions | - | ✓ | ✓ | ✓ |
| Grievance | - | - | - | ✓ |

### Response Timeframes

| Jurisdiction | Access Request | Deletion Request | General |
|--------------|----------------|------------------|---------|
| USA (CCPA) | 45 days | 45 days | 45 days |
| EU (GDPR) | 30 days | 30 days | 30 days (extendable) |
| Switzerland | 30 days | 30 days | 30 days |
| India (DPDP) | 30 days | 30 days | 30 days |

---

## Breach Notification

### Requirements by Jurisdiction

| Jurisdiction | Authority | Timeline | Data Subjects | Content |
|--------------|-----------|----------|---------------|---------|
| USA | State AG/FTC | 30-90 days | If high risk | Nature, counts, remediation |
| EU (GDPR) | Supervisory Authority | 72 hours | If high risk | Nature, categories, consequences |
| Switzerland | FDPIC | 72 hours | If high risk | Nature, consequences, measures |
| India (DPDP) | Data Protection Board | 72 hours (SDF) | TBD | As prescribed |

### Breach Classification

```python
BREACH_RISK_LEVELS = {
    "low": {
        "notification_required": False,
        "authority_notification": False,
        "examples": ["Encrypted data, no key compromised"],
    },
    "medium": {
        "notification_required": True,
        "authority_notification": True,
        "data_subject_notification": False,
        "examples": ["Internal system breach, no data exfiltration"],
    },
    "high": {
        "notification_required": True,
        "authority_notification": True,
        "data_subject_notification": True,
        "examples": ["Unencrypted PII, financial data exposed"],
    },
}
```

---

## Implementation Checklist

### Technical Requirements

- [ ] Data encryption at rest (AES-256)
- [ ] Data encryption in transit (TLS 1.3)
- [ ] Access control mechanisms (RBAC)
- [ ] Audit logging for all data access
- [ ] Consent management system
- [ ] Data subject rights portal
- [ ] Automated data retention enforcement
- [ ] Breach detection and response system
- [ ] Cross-border transfer safeguards
- [ ] Data localization options

### Organizational Requirements

- [ ] Privacy policy published and accessible
- [ ] Privacy notices at collection points
- [ ] Data Protection Officer appointed (EU/Switzerland)
- [ ] Privacy impact assessments conducted
- [ ] Staff privacy training completed
- [ ] Data processing agreements with vendors
- [ ] Records of processing activities maintained
- [ ] Incident response plan documented
- [ ] Regular privacy audits scheduled

### Documentation Requirements

- [ ] Privacy policy (all jurisdictions)
- [ ] Cookie policy (if applicable)
- [ ] Data processing agreement template
- [ ] Consent forms
- [ ] Data subject rights request forms
- [ ] Breach notification templates
- [ ] Records of processing activities
- [ ] Data protection impact assessments

---

## Sanctions for Non-Compliance

| Jurisdiction | Maximum Penalty |
|--------------|-----------------|
| USA (CCPA) | $2,500 - $7,500 per violation |
| EU (GDPR) | €20 million or 4% global revenue |
| Switzerland | CHF 250,000 (FADP); higher under criminal provisions |
| India (DPDP) | ₹250 crore (≈$30M) |

---

## References

- [USA FTC Privacy](https://www.ftc.gov/business-guidance/privacy-security)
- [EU GDPR Official Text](https://gdpr.eu/)
- [Swiss FDPIC](https://www.edoeb.admin.ch/)
- [India MeitY DPDP](https://www.meity.gov.in/)

---

*Last Updated: July 2026*
*Version: 1.0*
*Document Owner: Legal/Compliance Team*
