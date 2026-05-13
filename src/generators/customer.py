"""Customer (CIF) data generator using Faker and uszipcode."""

import logging
from datetime import date, timedelta
from random import Random

import zipcodes
from faker import Faker

from src.models.customer import (
    Address,
    Customer,
    EmploymentStatus,
    MaritalStatus,
)

logger = logging.getLogger(__name__)

# Build zip code pool once at module level from the bundled zipcodes dataset.
# We filter to STANDARD type only — exclude PO Box and unique zip codes which
# would produce addresses that look odd on a customer record.
_ZIP_POOL: list[dict[str, str]] = [
    z for z in zipcodes.list_all() if z["zip_code_type"] == "STANDARD"
]

# Typed enum lists — rng.choice() returns str for StrEnum without explicit annotations
_EMPLOYMENT_STATUSES: list[EmploymentStatus] = list(EmploymentStatus)
_MARITAL_STATUSES: list[MaritalStatus] = list(MaritalStatus)


def generate_customers(count: int, seed: int, start_index: int = 1) -> list[Customer]:
    """
    Generate a list of synthetic banking customers.

    Args:
        count: Number of customers to generate.
        seed: Random seed for reproducibility.
        start_index: Starting integer for CIF ID sequencing.

    Returns:
        List of Customer records with unique customer_ids.
    """
    faker = Faker("en_US")
    Faker.seed(seed)
    rng = Random(seed)

    customers: list[Customer] = []

    for i in range(count):
        cif_id = f"CIF-{start_index + i:06d}"

        # Age range 18–85; uniform distribution across active banking population
        age_days = rng.randint(18 * 365, 85 * 365)
        dob = date.today() - timedelta(days=age_days)

        # Employment status is picked first so income range reflects it
        employment: EmploymentStatus = rng.choice(_EMPLOYMENT_STATUSES)
        annual_income = _income_for_employment(employment, rng)

        # customer_since: anywhere from 1 to 20 years ago
        years_as_customer = rng.randint(1, 20)
        customer_since = date.today() - timedelta(days=years_as_customer * 365)

        # Pull a real zip entry so city, state, and zip are geographically consistent
        zip_entry = rng.choice(_ZIP_POOL)

        customer = Customer(
            customer_id=cif_id,
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            date_of_birth=dob,
            ssn=faker.ssn(),
            email=faker.email(),
            phone=faker.numerify("###-###-####"),
            address=Address(
                street=faker.street_address(),
                city=zip_entry["city"],
                state=zip_entry["state"],
                zip_code=zip_entry["zip_code"],
            ),
            marital_status=rng.choice(_MARITAL_STATUSES),
            employment_status=employment,
            annual_income=annual_income,
            customer_since=customer_since,
        )
        customers.append(customer)

    logger.info("Generated %d customers (seed=%d)", count, seed)
    return customers


def _income_for_employment(status: EmploymentStatus, rng: Random) -> float:
    """Return a plausible annual income given employment status."""
    ranges: dict[EmploymentStatus, tuple[int, int]] = {
        EmploymentStatus.EMPLOYED: (30_000, 175_000),
        EmploymentStatus.SELF_EMPLOYED: (25_000, 200_000),
        EmploymentStatus.RETIRED: (15_000, 80_000),
        EmploymentStatus.UNEMPLOYED: (0, 15_000),
        EmploymentStatus.STUDENT: (0, 20_000),
    }
    low, high = ranges[status]
    # Round to nearest $500 — looks like a self-reported figure, not a raw float
    raw = rng.uniform(low, high)
    return round(raw / 500) * 500
