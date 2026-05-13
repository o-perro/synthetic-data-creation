"""Unit tests for customer, account, and transaction generators."""

from src.generators.accounts import generate_accounts
from src.generators.customer import generate_customers
from src.generators.transactions import generate_transactions
from src.models.account import AccountType
from src.models.transaction import TRANSACTION_CODE_TYPE_MAP, TransactionCode, TransactionType

# ---------------------------------------------------------------------------
# Customer generator
# ---------------------------------------------------------------------------


class TestGenerateCustomers:
    def test_returns_correct_count(self) -> None:
        customers = generate_customers(count=10, seed=42)
        assert len(customers) == 10

    def test_unique_customer_ids(self) -> None:
        customers = generate_customers(count=50, seed=42)
        ids = [c.customer_id for c in customers]
        assert len(ids) == len(set(ids))

    def test_customer_id_format(self) -> None:
        customers = generate_customers(count=5, seed=42)
        for c in customers:
            assert c.customer_id.startswith("CIF-")
            assert len(c.customer_id) == 10  # "CIF-" + 6 digits

    def test_ssn_last4_is_digits(self) -> None:
        customers = generate_customers(count=20, seed=42)
        for c in customers:
            assert c.ssn_last4.isdigit()
            assert len(c.ssn_last4) == 4

    def test_reproducible_with_same_seed(self) -> None:
        batch_a = generate_customers(count=10, seed=99)
        batch_b = generate_customers(count=10, seed=99)
        assert [c.customer_id for c in batch_a] == [c.customer_id for c in batch_b]
        assert [c.first_name for c in batch_a] == [c.first_name for c in batch_b]

    def test_different_seeds_produce_different_data(self) -> None:
        batch_a = generate_customers(count=10, seed=1)
        batch_b = generate_customers(count=10, seed=2)
        # It's astronomically unlikely that all first names match with different seeds
        assert [c.first_name for c in batch_a] != [c.first_name for c in batch_b]

    def test_annual_income_non_negative(self) -> None:
        customers = generate_customers(count=50, seed=42)
        for c in customers:
            assert c.annual_income >= 0


# ---------------------------------------------------------------------------
# Account generator
# ---------------------------------------------------------------------------


class TestGenerateAccounts:
    def setup_method(self) -> None:
        self.customers = generate_customers(count=20, seed=42)

    def test_every_customer_has_at_least_one_checking(self) -> None:
        accounts = generate_accounts(self.customers, total_accounts=40, seed=42)
        customer_ids_with_checking = {
            a.customer_id for a in accounts if a.account_type == AccountType.CHECKING
        }
        all_customer_ids = {c.customer_id for c in self.customers}
        assert all_customer_ids == customer_ids_with_checking

    def test_total_account_count_at_least_customers(self) -> None:
        accounts = generate_accounts(self.customers, total_accounts=40, seed=42)
        assert len(accounts) >= len(self.customers)

    def test_unique_account_ids(self) -> None:
        accounts = generate_accounts(self.customers, total_accounts=40, seed=42)
        ids = [a.account_id for a in accounts]
        assert len(ids) == len(set(ids))

    def test_cd_accounts_have_term_and_maturity(self) -> None:
        accounts = generate_accounts(self.customers, total_accounts=60, seed=42)
        cd_accounts = [a for a in accounts if a.account_type == AccountType.CD]
        for acc in cd_accounts:
            assert acc.cd_term_months is not None
            assert acc.cd_maturity_date is not None
            assert acc.cd_maturity_date > acc.open_date

    def test_non_cd_accounts_have_no_cd_fields(self) -> None:
        accounts = generate_accounts(self.customers, total_accounts=60, seed=42)
        non_cd = [a for a in accounts if a.account_type != AccountType.CD]
        for acc in non_cd:
            assert acc.cd_term_months is None
            assert acc.cd_maturity_date is None

    def test_all_customer_ids_reference_valid_customers(self) -> None:
        accounts = generate_accounts(self.customers, total_accounts=40, seed=42)
        valid_ids = {c.customer_id for c in self.customers}
        for acc in accounts:
            assert acc.customer_id in valid_ids

    def test_balance_non_negative(self) -> None:
        accounts = generate_accounts(self.customers, total_accounts=40, seed=42)
        for acc in accounts:
            assert acc.balance >= 0


# ---------------------------------------------------------------------------
# Transaction generator
# ---------------------------------------------------------------------------


class TestGenerateTransactions:
    def setup_method(self) -> None:
        customers = generate_customers(count=10, seed=42)
        self.accounts = generate_accounts(customers, total_accounts=20, seed=42)

    def test_returns_transactions(self) -> None:
        txns = generate_transactions(self.accounts, total_transactions=200, seed=42)
        assert len(txns) > 0

    def test_unique_transaction_ids(self) -> None:
        txns = generate_transactions(self.accounts, total_transactions=200, seed=42)
        ids = [t.transaction_id for t in txns]
        assert len(ids) == len(set(ids))

    def test_all_account_ids_are_valid(self) -> None:
        valid_ids = {a.account_id for a in self.accounts}
        txns = generate_transactions(self.accounts, total_transactions=200, seed=42)
        for t in txns:
            assert t.account_id in valid_ids

    def test_customer_id_matches_account(self) -> None:
        account_to_customer = {a.account_id: a.customer_id for a in self.accounts}
        txns = generate_transactions(self.accounts, total_transactions=200, seed=42)
        for t in txns:
            assert t.customer_id == account_to_customer[t.account_id]

    def test_amounts_are_positive(self) -> None:
        txns = generate_transactions(self.accounts, total_transactions=200, seed=42)
        for t in txns:
            assert t.amount > 0

    def test_transaction_type_matches_code(self) -> None:
        txns = generate_transactions(self.accounts, total_transactions=200, seed=42)
        for t in txns:
            expected_type = TRANSACTION_CODE_TYPE_MAP[t.transaction_code]
            assert t.transaction_type == expected_type

    def test_cd_accounts_only_have_interest_postings(self) -> None:
        cd_account_ids = {a.account_id for a in self.accounts if a.account_type == AccountType.CD}
        txns = generate_transactions(self.accounts, total_transactions=200, seed=42)
        cd_txns = [t for t in txns if t.account_id in cd_account_ids]
        for t in cd_txns:
            assert t.transaction_code == TransactionCode.INTEREST_POSTING

    def test_interest_postings_are_credits(self) -> None:
        txns = generate_transactions(self.accounts, total_transactions=200, seed=42)
        interest_txns = [t for t in txns if t.transaction_code == TransactionCode.INTEREST_POSTING]
        for t in interest_txns:
            assert t.transaction_type == TransactionType.CREDIT

    def test_reproducible_with_same_seed(self) -> None:
        txns_a = generate_transactions(self.accounts, total_transactions=100, seed=7)
        txns_b = generate_transactions(self.accounts, total_transactions=100, seed=7)
        assert [t.transaction_id for t in txns_a] == [t.transaction_id for t in txns_b]
        assert [t.amount for t in txns_a] == [t.amount for t in txns_b]
