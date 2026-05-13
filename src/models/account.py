"""Pydantic models for Account data (Checking, Savings, CD)."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class AccountType(StrEnum):
    CHECKING = "Checking"
    SAVINGS = "Savings"
    CD = "CD"


class AccountStatus(StrEnum):
    ACTIVE = "Active"
    CLOSED = "Closed"
    DORMANT = "Dormant"


class CDTerm(StrEnum):
    """Standard CD term lengths in months."""

    MONTHS_3 = "3"
    MONTHS_6 = "6"
    MONTHS_12 = "12"
    MONTHS_24 = "24"
    MONTHS_36 = "36"


class Account(BaseModel):
    """A single bank account linked to a customer (CIF)."""

    account_id: str = Field(description="Unique account identifier, e.g. ACT-000001")
    customer_id: str = Field(description="Foreign key to Customer.customer_id")
    account_type: AccountType
    account_number: str = Field(
        min_length=10,
        max_length=12,
        description="10–12 digit account number, zero-padded",
    )
    routing_number: str = Field(
        pattern=r"^\d{9}$",
        description="9-digit ABA routing number",
    )
    status: AccountStatus
    open_date: date
    balance: float = Field(ge=0.0, description="Current balance in USD")
    interest_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Annual interest rate as a decimal, e.g. 0.045 = 4.5%",
    )

    # CD-specific fields — null for Checking and Savings
    cd_term_months: int | None = Field(
        default=None,
        description="CD term in months; only populated for CD accounts",
    )
    cd_maturity_date: date | None = Field(
        default=None,
        description="Date the CD matures; only populated for CD accounts",
    )
