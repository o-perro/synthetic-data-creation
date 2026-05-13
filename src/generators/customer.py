"""Customer (CIF) data generator using Faker."""

import logging
from datetime import date, timedelta
from random import Random

from faker import Faker

from src.models.customer import (
    Address,
    Customer,
    EmploymentStatus,
    MaritalStatus,
)

logger = logging.getLogger(__name__)


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

        # Age range 18–85; skew slightly younger to reflect active banking population
        age_days = rng.randint(18 * 365, 85 * 365)
        dob = date.today() - timedelta(days=age_days)

        # Employment status influences income range
        employment = rng.choice(list(EmploymentStatus))
        annual_income = _income_for_employment(employment, rng)

        # customer_since: anywhere from 1 to 20 years ago
        years_as_customer = rng.randint(1, 20)
        customer_since = date.today() - timedelta(days=years_as_customer * 365)

        customer = Customer(
            customer_id=cif_id,
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            date_of_birth=dob,
            ssn_last4=f"{rng.randint(0, 9999):04d}",
            email=faker.email(),
            phone=faker.numerify("###-###-####"),
            address=Address(
                street=faker.street_address(),
                city=faker.city(),
                state=faker.state_abbr(),
                zip_code=faker.zipcode()[:5],
            ),
            marital_status=rng.choice(list(MaritalStatus)),
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
    # Round to nearest $500 for realism
    raw = rng.uniform(low, high)
    return round(raw / 500) * 500
