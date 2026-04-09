import logging
from typing import Dict, Any
from talos_ucp_connector.adapters.outbound.http import HttpDiscoveryAdapter, HttpMerchantCheckoutAdapter
from talos_ucp_connector.adapters.outbound.payment import SandboxPaymentAdapter
from talos_ucp_connector.adapters.infrastructure.security import RequestSigner
from talos_ucp_connector.adapters.infrastructure.state import SystemClock, InMemoryReplayStore
from talos_ucp_connector.adapters.infrastructure.persistence import ConfigStoreAdapter, AuditAdapter
from talos_ucp_connector.domain.services import CommerceService

logger = logging.getLogger(__name__)

class Container:
    """
    Dependency Injection Container (Manual).
    Wires up the Hexagonal Architecture.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 1. Infrastructure / Common
        self.clock = SystemClock()
        self.replay_store = InMemoryReplayStore()
        self.audit = AuditAdapter()
        self.config_store = ConfigStoreAdapter(config)
        
        # 2. Security
        # Load ES256 Private Key from config/env
        # In production, this MUST be loaded from a HSM or Secret Manager
        private_key = config.get("security", {}).get("private_key")
        if not private_key:
             # Do not provide a hardcoded fallback in the source code.
             # If missing, it must be provided via .env or configuration files.
             logger.error("No private key provided in UCP Connector config. Signing will fail.")
             private_key = ""
             
        self.signer = RequestSigner(private_key)
        self.signing_kid = config.get("security", {}).get("kid", "talos-dev-key")

        # 3. Outbound Adapters
        self.discovery_adapter = HttpDiscoveryAdapter()
        self.merchant_checkout = HttpMerchantCheckoutAdapter()
        self.payment_adapter = SandboxPaymentAdapter()
        
        # 4. Domain Service (The Hexagon)
        self.service = CommerceService(
            merchant_checkout=self.merchant_checkout,
            discovery=self.discovery_adapter,
            signer=self.signer,
            clock=self.clock,
            replay_store=self.replay_store,
            config_store=self.config_store,
            audit=self.audit,
            payment=self.payment_adapter,
            platform_profile_uri=config.get("platform_profile_uri", "talos-gateway"),
            signing_kid=self.signing_kid
        )
