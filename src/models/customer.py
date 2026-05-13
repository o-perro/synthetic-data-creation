"""Pydantic models for Customer (CIF) data."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class MaritalStatus(StrEnum):
    SINGLE = "Single"
    MARRIED = "Married"
    DIVORCED = "Divorced"
    WIDOWED = "Widowed"


class EmploymentStatus(StrEnum):
    EMPLOYED = "Employed"
    SELF_EMPLOYED = "Self-Employed"
    RETIRED = "Retired"
    UNEMPLOYED = "Unemployed"
    STUDENT = "Student"


class Address(BaseModel):
    """Mailing address for a customer."""

    street: str
    city: str
    state: str = Field(min_length=2, max_length=2, description="Two-letter US state code")
    zip_code: str = Field(pattern=r"^\d{5}$")


class Customer(BaseModel):
    """CIF (Customer Information File) record for a single banking customer."""

    customer_id: str = Field(description="Unique CIF identifier, e.g. CIF-000001")
    first_name: str
    last_name: str
    date_of_birth: date
    ssn_last4: str = Field(
        pattern=r"^\d{4}$",
        description="Last 4 digits of SSN only — never store full SSN in test data",
    )
    email: EmailStr
    phone: str = Field(pattern=r"^\d{3}-\d{3}-\d{4}$", description="Format: 555-867-5309")
    address: Address
    marital_status: MaritalStatus
    employment_status: EmploymentStatus
    annual_income: float = Field(ge=0.0)
    customer_since: date = Field(description="Date the customer relationship was established")
