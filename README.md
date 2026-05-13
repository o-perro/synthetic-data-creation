# Synthetic Banking Data Generator

A Python-based tool for generating realistic synthetic banking data for UAT (User Acceptance Testing). Produces customers (CIF), accounts (Checking, Savings, CD), and transactions — all referentially consistent and ready to load into Snowflake or any relational system.

> **No real customer data is used or required.** All output is fully synthetic.

---

## What It Generates

| Entity | Description | Default Volume |
|--------|-------------|---------------|
| **Customers (CIF)** | Name, DOB, full SSN, contact info, employment, income — geographically consistent addresses | 250 |
| **Accounts** | Checking, Savings, and CD accounts linked to customers | 450 |
| **Transactions** | Debits and credits per account type with realistic patterns | 7,500 |

**Account behavior by type:**
- **Checking** — high-frequency mix of purchases, ATM withdrawals, bill pay, ACH, direct deposit, and more
- **Savings** — low-frequency transfers, ACH, and monthly interest postings
- **CD** — interest postings only (no card or transfer transactions)

> No debit or credit card PAN data is generated — this tool is designed for non-PCI environments.

---

## Quick Start

### Prerequisites
- [uv](https://docs.astral.sh/uv/) — Python package manager (`brew install uv` on Mac)
- Python 3.11 (managed automatically by uv)

### Install
```bash
git clone https://github.com/o-perro/synthetic-data-creation.git
cd synthetic-data-creation
uv sync
```

### Generate data
```bash
# Generate with defaults (250 customers, 450 accounts, 7,500 transactions)
uv run python scripts/generate.py

# Reproducible run — same seed always produces the same dataset
uv run python scripts/generate.py --seed 42

# Custom volume
uv run python scripts/generate.py --seed 42 --customers 100 --accounts 200 --transactions 3000

# Output as CSV instead of JSON
uv run python scripts/generate.py --format csv

# Output both JSON and CSV
uv run python scripts/generate.py --format both

# Write to a specific directory
uv run python scripts/generate.py --output-dir /tmp/uat_data
```

Output files land in `data/outputs/` by default:
```
data/outputs/
├── customers.json   (or .csv)
├── accounts.json
└── transactions.json
```

---

## Jupyter Notebooks

The `notebooks/` directory contains analysis notebooks that walk through each generator and visualize the output distributions. Run these to validate the data looks realistic before loading into Snowflake.

```bash
uv run jupyter lab
```

| Notebook | Description |
|----------|-------------|
| `01_customer_analysis.ipynb` | Customer generator walkthrough — age, employment, income, marital status, geographic spread, and tenure distributions |
| `02_account_analysis.ipynb` | Account generator walkthrough — type mix, accounts per customer, balance and interest rate distributions, CD term breakdown |

> **Kernel:** Select **Python (synthetic-data-creation)** when opening a notebook for the first time.

---

## CLI Reference

```
uv run python scripts/generate.py [OPTIONS]

Options:
  -s, --seed INTEGER          Random seed for reproducible output  [default: 42]
  -c, --customers INTEGER     Number of CIF customer records       [default: 250]
  -a, --accounts INTEGER      Total accounts across all customers  [default: 450]
  -t, --transactions INTEGER  Total transactions across all accounts [default: 7500]
      --history-months INT    Months of transaction history        [default: 12]
  -f, --format [json|csv|both] Output format                      [default: json]
  -o, --output-dir PATH       Output directory                    [default: data/outputs]
      --help                  Show this message and exit
```

**Key rules enforced by the CLI:**
- `--accounts` must be ≥ `--customers` — every customer is guaranteed at least one Checking account
- Use the same `--seed` value to reproduce an identical dataset across runs or team members

---

## Loading into Snowflake

### JSON
```sql
-- Create a stage pointing to your output location, then:
COPY INTO customers
FROM @my_stage/customers.json
FILE_FORMAT = (TYPE = 'JSON');
```

### CSV
```sql
COPY INTO customers
FROM @my_stage/customers.csv
FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"');
```

> CSV output flattens nested fields using double-underscore notation.
> For example, `address.city` becomes `address__city` in the CSV header.

---

## Project Structure

```
synthetic-data-creation/
├── src/
│   ├── generators/
│   │   ├── customer.py       # Faker-based CIF generation
│   │   ├── accounts.py       # Account generation with type distribution
│   │   └── transactions.py   # Rule-based transaction generation (numpy)
│   ├── models/
│   │   ├── customer.py       # Pydantic schema — Customer (CIF)
│   │   ├── account.py        # Pydantic schema — Account
│   │   └── transaction.py    # Pydantic schema — Transaction
│   ├── config/
│   │   └── settings.py       # Volume defaults and bank config (Pydantic BaseSettings)
│   └── utils/
│       └── exporters.py      # JSON and CSV writers
├── scripts/
│   └── generate.py           # CLI entry point — run this
├── tests/
│   └── unit/                 # 31 unit tests, 98% coverage
├── data/
│   └── outputs/              # Generated files land here (gitignored)
├── .python-version           # Pins Python 3.11 for consistent environments
├── pyproject.toml            # Dependencies and tooling config
└── CLAUDE.md                 # Developer notes and architecture decisions
```

---

## How Transaction Generation Works

Transactions are generated using **rule-based distributions** — no real bank data is needed or used.

Each account type has its own pattern:

| Account Type | Monthly Volume | Transaction Mix |
|---|---|---|
| Checking | 15–40 transactions | Purchases, ATM, bill pay, ACH, direct deposit, check, transfers |
| Savings | 2–6 transactions | Transfers in/out, ACH, interest postings |
| CD | 1 per month | Interest postings only |

**Amount distributions** use log-normal sampling (via `numpy`) so that small transactions are more common than large ones — matching real-world spending patterns.

**Interest postings** are computed from the account's balance and APY rather than sampled from a range, so they're proportional to what the account would actually earn.

---

## Extending the Generator

The generator is designed to be a baseline — teams can add fields or behaviors without touching the core pipeline.

**To add a new customer field:**
1. Add the field to [src/models/customer.py](src/models/customer.py)
2. Add the generation logic to [src/generators/customer.py](src/generators/customer.py)
3. Run the quality gates (see below)

**To add a new transaction type:**
1. Add the code to `TransactionCode` in [src/models/transaction.py](src/models/transaction.py)
2. Add it to `TRANSACTION_CODE_TYPE_MAP` (Debit or Credit)
3. Add an amount range to `_AMOUNT_RANGES` in [src/generators/transactions.py](src/generators/transactions.py)
4. Add it to the appropriate account type's code pool (`_CHECKING_CODES`, etc.)

**To change default volumes** without using CLI flags, edit `.env` (copy from `.env.example`):
```bash
cp .env.example .env
# Then edit DEFAULT_CUSTOMERS, DEFAULT_ACCOUNTS, DEFAULT_TRANSACTIONS
```

---

## Development

### Install dev dependencies
```bash
uv sync --extra dev
```

### Quality gates (run before every commit)
```bash
uv run ruff check src/ tests/        # Lint
uv run ruff format --check src/ tests/  # Format
uv run mypy src/                     # Type check
uv run python -m pytest tests/unit/ -v  # Tests
```

### Run all gates in one line
```bash
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/ && uv run python -m pytest tests/unit/ -v
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Rule-based transactions instead of SDV | SDV requires real training data; rule-based gives full control with no data dependency |
| Faker for customer/account data | Industry standard for synthetic PII — realistic names, addresses, emails out of the box |
| Seeded randomness | Same seed = same dataset; critical for regression testing and cross-team consistency |
| Pydantic v2 models | Type-safe schemas at every boundary; easy to extend and validate |
| JSON + CSV output | JSON is the primary format; CSV is provided for Snowflake `COPY INTO` compatibility |
| No card data | Bank is not PCI compliant — no debit/credit PAN, CVV, or card numbers anywhere |

---

## License

This project is intended for internal UAT use. No license for public redistribution.
