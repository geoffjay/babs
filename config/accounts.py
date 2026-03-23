"""Multi-account Polymarket setup. Loads accounts from environment variables."""

import os
from dataclasses import dataclass
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Account:
    name: str
    private_key: str
    funder_address: str


def load_accounts() -> Dict[str, Account]:
    """Load all Polymarket accounts from environment variables.

    Expects:
        POLYMARKET_PRIVATE_KEY / POLYMARKET_FUNDER_ADDRESS  -> "primary"
        POLYMARKET_PRIVATE_KEY_2 / POLYMARKET_FUNDER_ADDRESS_2 -> "account_2"
        POLYMARKET_PRIVATE_KEY_3 / POLYMARKET_FUNDER_ADDRESS_3 -> "account_3"
        ...
    """
    accounts: Dict[str, Account] = {}

    # Primary account
    pk = os.getenv("POLYMARKET_PRIVATE_KEY", "")
    fa = os.getenv("POLYMARKET_FUNDER_ADDRESS", "")
    if pk:
        accounts["primary"] = Account(name="primary", private_key=pk, funder_address=fa)

    # Numbered accounts (2-10)
    for i in range(2, 11):
        pk = os.getenv(f"POLYMARKET_PRIVATE_KEY_{i}", "")
        fa = os.getenv(f"POLYMARKET_FUNDER_ADDRESS_{i}", "")
        if pk:
            name = f"account_{i}"
            accounts[name] = Account(name=name, private_key=pk, funder_address=fa)

    return accounts


def get_account_by_name(name: str) -> Optional[Account]:
    """Look up a single account by name."""
    accounts = load_accounts()
    return accounts.get(name)
