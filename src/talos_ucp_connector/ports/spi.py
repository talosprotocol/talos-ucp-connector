from abc import ABC, abstractmethod
from typing import Dict, Any, List, Set, Optional

class DiscoveryPort(ABC):
    @abstractmethod
    def fetch_profile(self, merchant_domain: str) -> Dict[str, Any]:
        pass

class CheckoutPort(ABC):
    @abstractmethod
    def create_session(self, merchant_domain: str, line_items: list, currency: str, headers: Dict[str, str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def complete_session(self, merchant_domain: str, session_id: str, payment_data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        pass

class PaymentPort(ABC):
    @abstractmethod
    def get_credentials(self, currency: str, amount_minor: int, merchant_domain: str) -> Dict[str, Any]:
        pass

class PolicyPort(ABC):
    @abstractmethod
    def validate_merchant(self, merchant_domain: str) -> None:
        pass

    @abstractmethod
    def validate_transaction(self, amount_minor: int, currency: str) -> None:
        pass
