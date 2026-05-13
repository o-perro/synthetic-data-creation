"""Application settings loaded from environment variables or .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Volume targets and output configuration.
    All values can be overridden via environment variables or CLI flags.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Output location — relative to project root
    output_dir: Path = Path("data/outputs")

    # Default seed for reproducible runs; 0 means unseeded (random each time)
    default_seed: int = 42

    # Default population sizes
    default_customers: int = 250
    default_accounts: int = 450
    default_transactions: int = 7500

    # Routing number used across all generated accounts (fictional ABA)
    bank_routing_number: str = "999000001"

    # Bank name embedded in transaction descriptions
    bank_name: str = "First Synthetic Bank"


# Module-level singleton — import this instead of instantiating directly
settings = Settings()
