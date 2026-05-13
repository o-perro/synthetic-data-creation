"""
Transaction generator using rule-based distributions.

No real bank data is used. Each account type has its own transaction
pattern — frequency, amount ranges, and transaction code mix — modeled
after typical retail banking behavior.
"""

import logging
from datetime import date, timedelta
from random import Random

import numpy as np

from src.models.account import Account, AccountType
from src.models.transaction import (
    TRANSACTION_CODE_TYPE_MAP,
    Transaction,
    TransactionCode,
    TransactionType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transaction mix per account type
# Each entry is (TransactionCode, relative_weight)
# Weights are normalized internally — they don't need to sum to 1.
# ---------------------------------------------------------------------------

_CHECKING_CODES: list[tuple[TransactionCode, float]] = [
    (TransactionCode.PURCHASE, 30.0),
    (TransactionCode.ATM_WITHDRAWAL, 10.0),
    (TransactionCode.BILL_PAY, 8.0),
    (TransactionCode.ACH_DEBIT, 6.0),
    (TransactionCode.CHECK_PAID, 4.0),
    (TransactionCode.TRANSFER_OUT, 3.0),
    (TransactionCode.SERVICE_FEE, 1.0),
    (TransactionCode.DIRECT_DEPOSIT, 12.0),
    (TransactionCode.ACH_CREDIT, 5.0),
    (TransactionCode.TRANSFER_IN, 4.0),
    (TransactionCode.MOBILE_DEPOSIT, 4.0),
    (TransactionCode.CHECK_DEPOSIT, 3.0),
    (TransactionCode.INTEREST_POSTING, 1.0),
]

_SAVINGS_CODES: list[tuple[TransactionCode, float]] = [
    (TransactionCode.TRANSFER_OUT, 20.0),
    (TransactionCode.ACH_DEBIT, 5.0),
    (TransactionCode.TRANSFER_IN, 30.0),
    (TransactionCode.ACH_CREDIT, 10.0),
    (TransactionCode.INTEREST_POSTING, 15.0),
    (TransactionCode.MOBILE_DEPOSIT, 5.0),
    (TransactionCode.CHECK_DEPOSIT, 5.0),
]

# CDs only post interest — no other transactions in this simplified model
_CD_CODES: list[tuple[TransactionCode, float]] = [
    (TransactionCode.INTEREST_POSTING, 1.0),
]

# Average transactions per month per account type
_MONTHLY_FREQUENCY: dict[AccountType, tuple[int, int]] = {
    AccountType.CHECKING: (15, 40),
    AccountType.SAVINGS: (2, 6),
    AccountType.CD: (1, 1),  # always exactly 1 interest posting per month
}

# Amount ranges (USD) per transaction code
_AMOUNT_RANGES: dict[TransactionCode, tuple[float, float]] = {
    TransactionCode.PURCHASE: (5.0, 300.0),
    TransactionCode.ATM_WITHDRAWAL: (20.0, 500.0),
    TransactionCode.BILL_PAY: (25.0, 2_500.0),
    TransactionCode.ACH_DEBIT: (10.0, 1_500.0),
    TransactionCode.CHECK_PAID: (50.0, 5_000.0),
    TransactionCode.TRANSFER_OUT: (100.0, 10_000.0),
    TransactionCode.SERVICE_FEE: (5.0, 35.0),
    TransactionCode.DIRECT_DEPOSIT: (500.0, 8_000.0),
    TransactionCode.ACH_CREDIT: (50.0, 2_000.0),
    TransactionCode.WIRE_IN: (500.0, 50_000.0),
    TransactionCode.WIRE_OUT: (500.0, 50_000.0),
    TransactionCode.TRANSFER_IN: (100.0, 10_000.0),
    TransactionCode.INTEREST_POSTING: (0.01, 500.0),  # computed from balance; this is the fallback
    TransactionCode.CHECK_DEPOSIT: (50.0, 5_000.0),
    TransactionCode.MOBILE_DEPOSIT: (25.0, 2_500.0),
}

# Merchant categories mapped to common transaction codes
_MERCHANT_CATEGORIES: dict[TransactionCode, list[str]] = {
    TransactionCode.PURCHASE: [
        "Grocery Stores",
        "Gas Stations",
        "Restaurants",
        "Department Stores",
        "Pharmacies",
        "Online Retail",
        "Coffee Shops",
        "Home Improvement",
        "Clothing Stores",
        "Entertainment",
    ],
    TransactionCode.ATM_WITHDRAWAL: ["ATM"],
    TransactionCode.BILL_PAY: [
        "Utilities",
        "Insurance",
        "Telecommunications",
        "Cable & Streaming",
        "Rent/Mortgage",
    ],
}

_MERCHANT_NAMES: dict[str, list[str]] = {
    "Grocery Stores": ["Green Valley Market", "Fresh Basket", "City Grocers", "The Food Depot"],
    "Gas Stations": ["QuickFuel", "Speedway", "Road Runner Gas", "Prime Fuel"],
    "Restaurants": ["Riverside Grill", "The Corner Bistro", "Urban Eats", "Park Ave Diner"],
    "Department Stores": ["Metro Goods", "Everstone", "ShopRight", "ValueMart"],
    "Pharmacies": ["MedPlus Pharmacy", "CareRx", "Health Hub"],
    "Online Retail": ["ShopOnline", "QuickCart", "DigitalMart"],
    "Coffee Shops": ["Morning Brew", "The Daily Grind", "Sunrise Coffee"],
    "Home Improvement": ["BuildRight", "HomePro", "FixIt Supplies"],
    "Clothing Stores": ["StyleHouse", "Urban Thread", "FashionForward"],
    "Entertainment": ["CineMax Theater", "Event Hub", "GameZone"],
    "ATM": ["ATM"],
    "Utilities": ["City Electric & Gas", "AquaCity Water", "Sunshine Energy"],
    "Insurance": ["Shield Insurance Co.", "SafeGuard Life", "BlueStar Health"],
    "Telecommunications": ["ConnectTel", "NetSpark Mobile", "ClearVoice"],
    "Cable & Streaming": ["StreamPlus", "MediaLink", "BroadView Cable"],
    "Rent/Mortgage": ["Property Management LLC", "HomeBase Rentals"],
}


def generate_transactions(
    accounts: list[Account],
    total_transactions: int,
    seed: int,
    history_months: int = 12,
) -> list[Transaction]:
    """
    Generate transactions distributed across all accounts.

    Transaction volume is allocated proportionally: Checking accounts get the
    bulk of transactions, Savings a moderate share, CDs only interest postings.

    Args:
        accounts: The account population to generate transactions for.
        total_transactions: Target total transaction count across all accounts.
        seed: Random seed for reproducibility.
        history_months: How many months of history to generate (default: 12).

    Returns:
        List of Transaction records sorted by account_id then transaction_date.
    """
    rng = Random(seed)
    np_rng = np.random.default_rng(seed)

    transactions: list[Transaction] = []
    txn_counter = 1

    # Allocate transaction budget per account based on type weights
    checking_accounts = [a for a in accounts if a.account_type == AccountType.CHECKING]
    savings_accounts = [a for a in accounts if a.account_type == AccountType.SAVINGS]
    cd_accounts = [a for a in accounts if a.account_type == AccountType.CD]

    # CDs always get exactly 1 interest posting per month — fixed allocation
    cd_txn_count = len(cd_accounts) * history_months
    remaining_txns = max(0, total_transactions - cd_txn_count)

    # Split remaining between Checking (70%) and Savings (30%)
    checking_txn_count = int(remaining_txns * 0.70)
    savings_txn_count = remaining_txns - checking_txn_count

    account_budgets: dict[str, int] = {}
    _distribute_budget(checking_accounts, checking_txn_count, account_budgets, rng)
    _distribute_budget(savings_accounts, savings_txn_count, account_budgets, rng)
    for acc in cd_accounts:
        account_budgets[acc.account_id] = history_months

    for account in accounts:
        budget = account_budgets.get(account.account_id, 0)
        if budget == 0:
            continue

        acct_txns, txn_counter = _generate_account_transactions(
            account=account,
            budget=budget,
            history_months=history_months,
            txn_counter=txn_counter,
            rng=rng,
            np_rng=np_rng,
        )
        transactions.extend(acct_txns)

    transactions.sort(key=lambda t: (t.account_id, t.post_date))
    logger.info(
        "Generated %d transactions across %d accounts (seed=%d)",
        len(transactions),
        len(accounts),
        seed,
    )
    return transactions


def _generate_account_transactions(
    account: Account,
    budget: int,
    history_months: int,
    txn_counter: int,
    rng: Random,
    np_rng: np.random.Generator,
) -> tuple[list[Transaction], int]:
    """Generate all transactions for a single account."""
    code_pool = _code_pool_for_type(account.account_type)
    history_start = date.today() - timedelta(days=history_months * 30)
    total_days = (date.today() - history_start).days

    # Spread transactions randomly across the history window
    transaction_days = sorted(rng.randint(0, total_days - 1) for _ in range(budget))

    running_balance = account.balance
    transactions: list[Transaction] = []

    for day_offset in transaction_days:
        txn_date = history_start + timedelta(days=day_offset)
        post_date = txn_date + timedelta(days=rng.randint(0, 2))  # 0–2 day settlement lag

        code = _pick_code(code_pool, rng)
        txn_type = TRANSACTION_CODE_TYPE_MAP[code]
        amount = _pick_amount(code, account, running_balance, np_rng)

        # Adjust running balance: credits add, debits subtract
        if txn_type == TransactionType.CREDIT:
            running_balance = round(running_balance + amount, 2)
        else:
            # Don't let balance go negative — clamp the debit amount
            amount = min(amount, max(1.0, running_balance))
            running_balance = round(running_balance - amount, 2)

        merchant_category, merchant_name = _pick_merchant(code, rng)
        description = _build_description(code, merchant_name, account)
        check_number = _maybe_check_number(code, rng)

        txn = Transaction(
            transaction_id=f"TXN-{txn_counter:07d}",
            account_id=account.account_id,
            customer_id=account.customer_id,
            transaction_date=txn_date,
            post_date=post_date,
            transaction_type=txn_type,
            transaction_code=code,
            amount=round(amount, 2),
            running_balance=running_balance,
            description=description,
            merchant_name=merchant_name,
            merchant_category=merchant_category,
            check_number=check_number,
        )
        transactions.append(txn)
        txn_counter += 1

    return transactions, txn_counter


def _code_pool_for_type(
    account_type: AccountType,
) -> list[tuple[TransactionCode, float]]:
    """Return the weighted transaction code pool for a given account type."""
    return {
        AccountType.CHECKING: _CHECKING_CODES,
        AccountType.SAVINGS: _SAVINGS_CODES,
        AccountType.CD: _CD_CODES,
    }[account_type]


def _pick_code(pool: list[tuple[TransactionCode, float]], rng: Random) -> TransactionCode:
    """Select a transaction code using weighted sampling."""
    codes = [c for c, _ in pool]
    weights = [w for _, w in pool]
    total = sum(weights)
    r = rng.uniform(0, total)
    cumulative = 0.0
    for code, weight in zip(codes, weights, strict=True):
        cumulative += weight
        if r <= cumulative:
            return code
    return codes[-1]


def _pick_amount(
    code: TransactionCode,
    account: Account,
    running_balance: float,
    np_rng: np.random.Generator,
) -> float:
    """
    Sample a transaction amount.

    Interest postings are computed from the current balance and APY so
    they're proportional to what the account would actually earn.
    """
    if code == TransactionCode.INTEREST_POSTING:
        # Monthly interest = (balance * APY) / 12
        monthly_interest = (running_balance * account.interest_rate) / 12
        return max(0.01, round(monthly_interest, 2))

    low, high = _AMOUNT_RANGES[code]
    # Use log-normal distribution so small amounts are more common than large ones
    mean = (low + high) / 2
    raw = float(np_rng.lognormal(mean=np.log(mean), sigma=0.5))
    return round(max(low, min(high, raw)), 2)


def _pick_merchant(
    code: TransactionCode,
    rng: Random,
) -> tuple[str | None, str | None]:
    """Return (merchant_category, merchant_name) for the transaction code."""
    categories = _MERCHANT_CATEGORIES.get(code)
    if not categories:
        return None, None
    category = rng.choice(categories)
    names = _MERCHANT_NAMES.get(category, [])
    merchant_name = rng.choice(names) if names else None
    return category, merchant_name


def _build_description(
    code: TransactionCode,
    merchant_name: str | None,
    account: Account,
) -> str:
    """Build a human-readable transaction description."""
    templates: dict[TransactionCode, str] = {
        TransactionCode.DIRECT_DEPOSIT: "PAYROLL DIRECT DEPOSIT",
        TransactionCode.ATM_WITHDRAWAL: f"ATM WITHDRAWAL - {account.account_number[-4:]}",
        TransactionCode.TRANSFER_IN: f"TRANSFER FROM {account.account_number[-4:]}",
        TransactionCode.TRANSFER_OUT: f"TRANSFER TO {account.account_number[-4:]}",
        TransactionCode.ACH_CREDIT: "ACH CREDIT",
        TransactionCode.ACH_DEBIT: "ACH DEBIT",
        TransactionCode.WIRE_IN: "INCOMING WIRE TRANSFER",
        TransactionCode.WIRE_OUT: "OUTGOING WIRE TRANSFER",
        TransactionCode.INTEREST_POSTING: "INTEREST POSTING",
        TransactionCode.SERVICE_FEE: "MONTHLY SERVICE FEE",
        TransactionCode.BILL_PAY: f"BILL PAY - {merchant_name or 'PAYEE'}",
        TransactionCode.CHECK_PAID: "CHECK PAYMENT",
        TransactionCode.CHECK_DEPOSIT: "CHECK DEPOSIT",
        TransactionCode.MOBILE_DEPOSIT: "MOBILE CHECK DEPOSIT",
        TransactionCode.PURCHASE: f"POS PURCHASE - {merchant_name or 'MERCHANT'}",
    }
    return templates.get(code, str(code))


def _maybe_check_number(code: TransactionCode, rng: Random) -> str | None:
    """Return a check number for check transactions, None otherwise."""
    if code in (TransactionCode.CHECK_PAID, TransactionCode.CHECK_DEPOSIT):
        return str(rng.randint(1000, 9999))
    return None


def _distribute_budget(
    accounts: list[Account],
    total: int,
    budget: dict[str, int],
    rng: Random,
) -> None:
    """Distribute a transaction budget across accounts with slight per-account variance."""
    if not accounts:
        return
    base = total // len(accounts)
    remainder = total - base * len(accounts)
    for acc in accounts:
        budget[acc.account_id] = base
    # Distribute the remainder one transaction at a time to random accounts
    for _ in range(remainder):
        acc = rng.choice(accounts)
        budget[acc.account_id] += 1
