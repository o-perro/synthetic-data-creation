# synthetic-data-creation — Project Notes

## Purpose
Generates synthetic banking data for UAT (User Acceptance Testing). Produces customers (CIF), accounts (Checking, Savings, CD), and transactions. Output targets Snowflake via JSON or CSV.

## Quick Start
```bash
uv sync --extra dev
uv run python scripts/generate.py --help
uv run python scripts/generate.py --seed 42 --customers 250 --format json
```

## Architecture

### Entity Hierarchy
```
Customer (CIF)
  └── Account (Checking | Savings | CD)
        └── Transaction
```

Every account belongs to exactly one customer. Every transaction belongs to exactly one account. Referential integrity is enforced at generation time — never assume it from the output files alone.

### Key modules
| Module | Responsibility |
|--------|---------------|
| `src/models/` | Pydantic v2 schemas — the single source of truth for every field |
| `src/generators/customer.py` | Faker-based CIF generation |
| `src/generators/accounts.py` | Account generation with realistic account number formats |
| `src/generators/transactions.py` | Rule-based transaction generation (numpy distributions) |
| `src/config/settings.py` | Pydantic BaseSettings — volume config, seed, output path |
| `src/utils/exporters.py` | JSON and CSV writers, Snowflake-compatible |
| `scripts/generate.py` | Typer CLI entry point — what teams run |

### Transaction generation approach
Transactions are rule-based (not SDV) because no real bank data is available. Each account type has its own pattern:
- **Checking:** High frequency, mixed debits (purchases, ATM, bill pay) and credits (payroll, transfers)
- **Savings:** Low frequency, mostly transfers in/out and interest postings
- **CD:** Interest postings only (monthly or quarterly depending on term)

Amount distributions use `numpy` — realistic ranges per transaction type, not uniform random.

## Extending the Generator
Teams can extend by:
1. Adding fields to the Pydantic models in `src/models/`
2. Adding generation logic in the corresponding `src/generators/` file
3. Re-running the quality gates (`ruff`, `mypy`) before committing

## Quality Gates (always run before committing)
```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run python -m pytest tests/unit/ -v
```

## Output
Generated files land in `data/outputs/` (gitignored — too large for version control).

Snowflake load pattern:
```sql
-- JSON
COPY INTO my_table FROM @my_stage/customers.json FILE_FORMAT = (TYPE = 'JSON');

-- CSV
COPY INTO my_table FROM @my_stage/customers.csv FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1);
```

## Design Decisions
- **No SDV:** SDV requires real data as a training input. Without it, rule-based generation gives more control and is the right approach for UAT.
- **No card data:** Bank is not PCI compliant — no debit/credit PAN, CVV, or card numbers anywhere in the output.
- **Seeded runs:** Pass `--seed` to reproduce the exact same dataset. Useful for regression testing.
