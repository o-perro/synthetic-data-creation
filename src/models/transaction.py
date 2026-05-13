"""Pydantic models for Transaction data."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class TransactionType(StrEnum):
    """High-level classification of a transaction."""

    DEBIT = "Debit"
    CREDIT = "Credit"


class TransactionCode(StrEnum):
    """Specific transaction codes that describe the nature of the movement."""

    # Debits
    ATM_WITHDRAWAL = "ATM_WITHDRAWAL"
    PURCHASE = "PURCHASE"
    BILL_PAY = "BILL_PAY"
    ACH_DEBIT = "ACH_DEBIT"
    WIRE_OUT = "WIRE_OUT"
    CHECK_PAID = "CHECK_PAID"
    TRANSFER_OUT = "TRANSFER_OUT"
    SERVICE_FEE = "SERVICE_FEE"

    # Credits
    DIRECT_DEPOSIT = "DIRECT_DEPOSIT"
    ACH_CREDIT = "ACH_CREDIT"
    WIRE_IN = "WIRE_IN"
    TRANSFER_IN = "TRANSFER_IN"
    INTEREST_POSTING = "INTEREST_POSTING"
    CHECK_DEPOSIT = "CHECK_DEPOSIT"
    MOBILE_DEPOSIT = "MOBILE_DEPOSIT"


# Maps each code to its transaction type (debit or credit) for validation
TRANSACTION_CODE_TYPE_MAP: dict[TransactionCode, TransactionType] = {
    TransactionCode.ATM_WITHDRAWAL: TransactionType.DEBIT,
    TransactionCode.PURCHASE: TransactionType.DEBIT,
    TransactionCode.BILL_PAY: TransactionType.DEBIT,
    TransactionCode.ACH_DEBIT: TransactionType.DEBIT,
    TransactionCode.WIRE_OUT: TransactionType.DEBIT,
    TransactionCode.CHECK_PAID: TransactionType.DEBIT,
    TransactionCode.TRANSFER_OUT: TransactionType.DEBIT,
    TransactionCode.SERVICE_FEE: TransactionType.DEBIT,
    TransactionCode.DIRECT_DEPOSIT: TransactionType.CREDIT,
    TransactionCode.ACH_CREDIT: TransactionType.CREDIT,
    TransactionCode.WIRE_IN: TransactionType.CREDIT,
    TransactionCode.TRANSFER_IN: TransactionType.CREDIT,
    TransactionCode.INTEREST_POSTING: TransactionType.CREDIT,
    TransactionCode.CHECK_DEPOSIT: TransactionType.CREDIT,
    TransactionCode.MOBILE_DEPOSIT: TransactionType.CREDIT,
}


class Transaction(BaseModel):
    """A single financial transaction on a bank account."""

    transaction_id: str = Field(description="Unique transaction identifier, e.g. TXN-0000001")
    account_id: str = Field(description="Foreign key to Account.account_id")
    customer_id: str = Field(description="Denormalized for query convenience in Snowflake")
    transaction_date: date
    post_date: date = Field(
        description="Date the transaction settled (1–2 business days after transaction_date)"
    )
    transaction_type: TransactionType
    transaction_code: TransactionCode
    amount: float = Field(
        gt=0.0,
        description="Always positive; direction is determined by transaction_type",
    )
    running_balance: float = Field(
        description="Account balance immediately after this transaction posts"
    )
    description: str = Field(
        description="Human-readable memo, e.g. 'PAYROLL DIRECT DEPOSIT - ACME CORP'"
    )
    merchant_name: str | None = Field(
        default=None,
        description="Merchant or payee name for purchase/payment transactions; null for transfers",
    )
    merchant_category: str | None = Field(
        default=None,
        description="Merchant category description, e.g. 'Grocery Stores', 'Gas Stations'",
    )
    check_number: str | None = Field(
        default=None,
        description="Check number; only populated for CHECK_PAID and CHECK_DEPOSIT transactions",
    )
