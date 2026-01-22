from typing import Dict, Any
from ..adapters.outbound.http import HttpDiscoveryAdapter, HttpCheckoutAdapter
from ..adapters.outbound.payment import SandboxPaymentAdapter
from ..adapters.outbound.policy import ConfigPolicyAdapter
from ..domain.services import CommerceService

class Container:
    """
    Dependency Injection Container (Manual).
    Wires up the Hexagonal Architecture.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Adapters
        self.discovery_adapter = HttpDiscoveryAdapter()
        self.checkout_adapter = HttpCheckoutAdapter()
        self.payment_adapter = SandboxPaymentAdapter()
        self.policy_adapter = ConfigPolicyAdapter(config.get("policy", {}))
        
        # Domain Service
        platform_uri = config.get("platform_profile_uri", "https://talos.network/.well-known/ucp")
        self.commerce_service = CommerceService(
            discovery=self.discovery_adapter,
            checkout=self.checkout_adapter,
            payment=self.payment_adapter,
            policy=self.policy_adapter,
            platform_profile_uri=platform_uri
        )

# Global Container Instance (initialized in main)
# For FastMCP, we can lazy init.
