from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

# --- INBOUND PORTS (Primary) ---

class CheckoutLifecycleInboundPort(ABC):
    @abstractmethod
    def create_checkout(self, merchant_domain: str, line_items: list, currency: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_checkout(self, merchant_domain: str, session_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_checkout(self, merchant_domain: str, session_id: str, checkout_payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def complete_checkout(self, merchant_domain: str, session_id: str, amount_minor: int, currency: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel_checkout(self, merchant_domain: str, session_id: str) -> Dict[str, Any]:
        pass

class ConfigurationInboundPort(ABC):
    @abstractmethod
    def get_merchant_config(self, merchant_domain: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_merchant_config(self, merchant_domain: str, config: Dict[str, Any]) -> None:
        pass

# --- OUTBOUND PORTS (Secondary) ---

class MerchantCheckoutPort(ABC):
    @abstractmethod
    def post_checkout(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def put_checkout(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_checkout(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        pass

class DiscoveryPort(ABC):
    @abstractmethod
    def fetch_profile(self, merchant_domain: str) -> Dict[str, Any]:
        pass

class RequestSignerPort(ABC):
    @abstractmethod
    def sign(self, envelope: Dict[str, Any], kid: str) -> str:
        pass

class ClockPort(ABC):
    @abstractmethod
    def now(self) -> int:
        pass

class ReplayStorePort(ABC):
    @abstractmethod
    def check_and_store_nonce(self, merchant_id: str, kid: str, jti: str) -> bool:
        """Returns True if nonce is new/valid, False if replayed."""
        pass

class ConfigStorePort(ABC):
    @abstractmethod
    def get_merchant_policy(self, merchant_domain: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_merchant_allowlisted(self, merchant_domain: str) -> bool:
        pass

class AuditPort(ABC):
    @abstractmethod
    def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        pass

class PaymentPort(ABC):
    @abstractmethod
    def get_credentials(self, currency: str, amount_minor: int, merchant_domain: str) -> Dict[str, Any]:
        pass
