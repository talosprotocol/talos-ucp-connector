from typing import Dict, Any
from ...ports.spi import PolicyPort

class ConfigPolicyAdapter(PolicyPort):
    def __init__(self, config: Dict[str, Any]):
        self.allowed_merchants = set(config.get("allowed_merchants", []))
        self.allowed_currencies = set(config.get("allowed_currencies", ["USD"]))
        self.max_spend_minor = config.get("max_spend_minor", 0)

    def validate_merchant(self, merchant_domain: str) -> None:
        if self.allowed_merchants and merchant_domain not in self.allowed_merchants:
            raise ValueError(f"Merchant {merchant_domain} not allowed by policy.")

    def validate_transaction(self, amount_minor: int, currency: str) -> None:
        if currency not in self.allowed_currencies:
            raise ValueError(f"Currency {currency} not allowed.")
        if amount_minor > self.max_spend_minor:
            raise ValueError(f"Amount {amount_minor} exceeds limit {self.max_spend_minor}.")
