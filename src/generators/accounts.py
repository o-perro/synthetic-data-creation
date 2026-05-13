"""Account data generator (Checking, Savings, CD)."""

import logging
from datetime import date, timedelta
from random import Random

from src.config.settings import settings
from src.models.account import Account, AccountStatus, AccountType, CDTerm
from src.models.customer import Customer

logger = logging.getLogger(__name__)

# Approximate APY ranges per account type — realistic but fictional
_INTEREST_RATES: dict[AccountType, tuple[float, float]] = {
    AccountType.CHECKING: (0.0001, 0.005),  # 0.01%–0.5% (most checking pays little)
    AccountType.SAVINGS: (0.01, 0.055),  # 1%–5.5% HYSA range
    AccountType.CD: (0.03, 0.058),  # 3%–5.8% typical CD range
}

# Probability weights for each account type across the portfolio
_ACCOUNT_TYPE_WEIGHTS = [
    (AccountType.CHECKING, 0.45),
    (AccountType.SAVINGS, 0.35),
    (AccountType.CD, 0.20),
]


def generate_accounts(
    customers: list[Customer],
    total_accounts: int,
    seed: int,
) -> list[Account]:
    """
    Generate accounts distributed across the provided customers.

    Each customer gets at least one Checking account to ensure every CIF
    has an active transactional account. Remaining accounts are distributed
    randomly across customers weighted by realistic type probabilities.

    Args:
        customers: The customer population to attach accounts to.
        total_accounts: Target number of accounts to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of Account records with referential integrity to customers.
    """
    rng = Random(seed)
    accounts: list[Account] = []
    account_counter = 1

    # Guarantee every customer has a Checking account first
    for customer in customers:
        acc = _build_account(
            account_counter,
            customer,
            AccountType.CHECKING,
            rng,
        )
        accounts.append(acc)
        account_counter += 1

    # Distribute remaining accounts randomly across customers
    remaining = total_accounts - len(customers)
    for _ in range(max(0, remaining)):
        customer = rng.choice(customers)
        account_type = _weighted_choice(
            [t for t, _ in _ACCOUNT_TYPE_WEIGHTS],
            [w for _, w in _ACCOUNT_TYPE_WEIGHTS],
            rng,
        )
        acc = _build_account(account_counter, customer, account_type, rng)
        accounts.append(acc)
        account_counter += 1

    logger.info(
        "Generated %d accounts for %d customers (seed=%d)", len(accounts), len(customers), seed
    )
    return accounts


def _build_account(
    index: int,
    customer: Customer,
    account_type: AccountType,
    rng: Random,
) -> Account:
    """Construct a single Account record."""
    account_id = f"ACT-{index:06d}"
    account_number = str(rng.randint(10_000_000_00, 99_999_999_99))

    rate_low, rate_high = _INTEREST_RATES[account_type]
    interest_rate = round(rng.uniform(rate_low, rate_high), 4)

    # Open date: anywhere between the customer's join date and today
    days_since_join = (date.today() - customer.customer_since).days
    days_offset = rng.randint(0, max(0, days_since_join))
    open_date = customer.customer_since + timedelta(days=days_offset)

    balance = _starting_balance(account_type, rng)

    # CD-specific fields
    cd_term_months: int | None = None
    cd_maturity_date: date | None = None
    if account_type == AccountType.CD:
        cd_term_months = int(rng.choice([t.value for t in CDTerm]))
        cd_maturity_date = open_date + timedelta(days=cd_term_months * 30)

    return Account(
        account_id=account_id,
        customer_id=customer.customer_id,
        account_type=account_type,
        account_number=account_number,
        routing_number=settings.bank_routing_number,
        status=AccountStatus.ACTIVE,
        open_date=open_date,
        balance=balance,
        interest_rate=interest_rate,
        cd_term_months=cd_term_months,
        cd_maturity_date=cd_maturity_date,
    )


def _starting_balance(account_type: AccountType, rng: Random) -> float:
    """Return a plausible opening balance per account type."""
    ranges: dict[AccountType, tuple[float, float]] = {
        AccountType.CHECKING: (250.0, 15_000.0),
        AccountType.SAVINGS: (500.0, 50_000.0),
        AccountType.CD: (1_000.0, 100_000.0),
    }
    low, high = ranges[account_type]
    # Round to cents
    return round(rng.uniform(low, high), 2)


def _weighted_choice(options: list[AccountType], weights: list[float], rng: Random) -> AccountType:
    """Select one option using weighted probabilities without numpy dependency."""
    total = sum(weights)
    r = rng.uniform(0, total)
    cumulative = 0.0
    for option, weight in zip(options, weights, strict=True):
        cumulative += weight
        if r <= cumulative:
            return option
    return options[-1]
