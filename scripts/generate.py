"""
CLI entry point for the synthetic banking data generator.

Usage examples:
    uv run python scripts/generate.py --help
    uv run python scripts/generate.py --seed 42 --customers 250
    uv run python scripts/generate.py --seed 42 --format csv --output-dir /tmp/bank_data
    uv run python scripts/generate.py --customers 100 --accounts 200 --transactions 3000
"""

import logging
from enum import StrEnum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from src.config.settings import settings
from src.generators.accounts import generate_accounts
from src.generators.customer import generate_customers
from src.generators.transactions import generate_transactions
from src.utils.exporters import write_csv, write_json

# Configure logging so teams can see progress without noise
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="generate-data",
    help="Generate synthetic banking data for UAT (customers, accounts, transactions).",
    add_completion=False,
)
console = Console()


class OutputFormat(StrEnum):
    JSON = "json"
    CSV = "csv"
    BOTH = "both"


@app.command()
def generate(
    seed: int = typer.Option(
        settings.default_seed,
        "--seed",
        "-s",
        help="Random seed. Use the same seed to reproduce identical datasets.",
    ),
    customers: int = typer.Option(
        settings.default_customers,
        "--customers",
        "-c",
        min=1,
        help="Number of customers (CIF records) to generate.",
    ),
    accounts: int = typer.Option(
        settings.default_accounts,
        "--accounts",
        "-a",
        min=1,
        help="Total number of accounts across all customers.",
    ),
    transactions: int = typer.Option(
        settings.default_transactions,
        "--transactions",
        "-t",
        min=1,
        help="Total number of transactions across all accounts.",
    ),
    history_months: int = typer.Option(
        12,
        "--history-months",
        help="How many months of transaction history to generate.",
    ),
    output_format: OutputFormat = typer.Option(  # noqa: B008
        OutputFormat.JSON,
        "--format",
        "-f",
        help="Output format: json, csv, or both.",
    ),
    output_dir: Path = typer.Option(  # noqa: B008
        settings.output_dir,
        "--output-dir",
        "-o",
        help="Directory to write output files. Created if it does not exist.",
    ),
) -> None:
    """Generate synthetic banking data and write it to the output directory."""
    console.rule("[bold blue]Synthetic Banking Data Generator")
    console.print(f"  Seed:          {seed}")
    console.print(f"  Customers:     {customers:,}")
    console.print(f"  Accounts:      {accounts:,}")
    console.print(f"  Transactions:  {transactions:,}")
    console.print(f"  History:       {history_months} months")
    console.print(f"  Format:        {output_format}")
    console.print(f"  Output dir:    {output_dir}")
    console.print()

    # Validate that accounts >= customers (every customer needs at least 1 account)
    if accounts < customers:
        console.print(
            f"[red]Error:[/red] --accounts ({accounts}) must be >= --customers ({customers})."
            " Every customer gets at least one Checking account."
        )
        raise typer.Exit(code=1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Generation pipeline ---
    with console.status("[bold green]Generating customers..."):
        customer_list = generate_customers(count=customers, seed=seed)

    with console.status("[bold green]Generating accounts..."):
        account_list = generate_accounts(
            customers=customer_list,
            total_accounts=accounts,
            seed=seed,
        )

    with console.status("[bold green]Generating transactions..."):
        transaction_list = generate_transactions(
            accounts=account_list,
            total_transactions=transactions,
            seed=seed,
            history_months=history_months,
        )

    # --- Export ---
    _export(customer_list, account_list, transaction_list, output_dir, output_format)

    # --- Summary table ---
    table = Table(title="Generation Summary", show_header=True, header_style="bold cyan")
    table.add_column("Entity", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Output", style="dim")

    formats = (
        [OutputFormat.JSON, OutputFormat.CSV]
        if output_format == OutputFormat.BOTH
        else [output_format]
    )
    file_ext = "/".join(f for f in formats)

    table.add_row("Customers", f"{len(customer_list):,}", f"customers.{file_ext}")
    table.add_row("Accounts", f"{len(account_list):,}", f"accounts.{file_ext}")
    table.add_row("Transactions", f"{len(transaction_list):,}", f"transactions.{file_ext}")

    console.print(table)
    console.print(f"\n[green]Done![/green] Files written to: {output_dir.resolve()}")


def _export(
    customer_list: list,
    account_list: list,
    transaction_list: list,
    output_dir: Path,
    output_format: OutputFormat,
) -> None:
    """Write all entities to disk in the requested format(s)."""
    do_json = output_format in (OutputFormat.JSON, OutputFormat.BOTH)
    do_csv = output_format in (OutputFormat.CSV, OutputFormat.BOTH)

    if do_json:
        with console.status("[bold green]Writing JSON files..."):
            write_json(customer_list, output_dir / "customers.json")
            write_json(account_list, output_dir / "accounts.json")
            write_json(transaction_list, output_dir / "transactions.json")

    if do_csv:
        with console.status("[bold green]Writing CSV files..."):
            write_csv(customer_list, output_dir / "customers.csv")
            write_csv(account_list, output_dir / "accounts.csv")
            write_csv(transaction_list, output_dir / "transactions.csv")


if __name__ == "__main__":
    app()
