from typing import Dict, Set, Any, List
from ..ports.spi import DiscoveryPort, CheckoutPort, PaymentPort, PolicyPort

class CommerceService:
    """
    Core Domain Service. 
    Orchestrates UCP flows using injected ports.
    """
    def __init__(self, 
                 discovery: DiscoveryPort,
                 checkout: CheckoutPort,
                 payment: PaymentPort,
                 policy: PolicyPort,
                 platform_profile_uri: str):
        self.discovery = discovery
        self.checkout = checkout
        self.payment = payment
        self.policy = policy
        self.platform_profile_uri = platform_profile_uri
        self._capabilities_cache: Dict[str, Set[str]] = {}

    def _get_headers(self) -> Dict[str, str]:
        return {"UCP-Agent": f'profile="{self.platform_profile_uri}"'}

    def discover_and_negotiate(self, merchant_domain: str) -> Dict[str, Any]:
        # 1. Policy Check
        self.policy.validate_merchant(merchant_domain)

        # 2. Discovery
        if merchant_domain in self._capabilities_cache:
            caps = self._capabilities_cache[merchant_domain]
        else:
            profile = self.discovery.fetch_profile(merchant_domain)
            # Domain Logic: Intersection
            platform_caps = {"dev.ucp.shopping"}
            merchant_caps = set(profile.get("services", {}).keys())
            caps = platform_caps.intersection(merchant_caps)
            self._capabilities_cache[merchant_domain] = caps

        return {
            "merchant": merchant_domain,
            "negotiated_capabilities": list(caps),
            "status": "active" if caps else "no-overlap"
        }

    def create_checkout(self, merchant_domain: str, line_items: List[Any], currency: str) -> Dict[str, Any]:
        self.policy.validate_merchant(merchant_domain)
        # Note: could check max_spend here if line items were typed better
        
        return self.checkout.create_session(
            merchant_domain, 
            line_items, 
            currency, 
            self._get_headers()
        )

    def complete_checkout(self, merchant_domain: str, session_id: str, amount_minor: int, currency: str) -> Dict[str, Any]:
        self.policy.validate_merchant(merchant_domain)
        self.policy.validate_transaction(amount_minor, currency)

        payment_data = self.payment.get_credentials(currency, amount_minor, merchant_domain)
        
        return self.checkout.complete_session(
            merchant_domain, 
            session_id, 
            payment_data, 
            self._get_headers()
        )
