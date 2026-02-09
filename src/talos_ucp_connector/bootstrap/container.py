from typing import Dict, Any
from talos_ucp_connector.adapters.outbound.http import HttpDiscoveryAdapter, HttpMerchantCheckoutAdapter
from talos_ucp_connector.adapters.outbound.payment import SandboxPaymentAdapter
from talos_ucp_connector.adapters.infrastructure.security import RequestSigner
from talos_ucp_connector.adapters.infrastructure.state import SystemClock, InMemoryReplayStore
from talos_ucp_connector.adapters.infrastructure.persistence import ConfigStoreAdapter, AuditAdapter
from talos_ucp_connector.domain.services import CommerceService

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
        # Placeholder ES256 Private Key for Dev
        # In production, this would be loaded from a HSM or Secret Manager
        DEV_KEY = config.get("security", {}).get("private_key", """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIKdHtBu5u+k1s3nea01zCZAPqm932PGK8rG3AbHjFtD7oAoGCCqGSM49
AwEHoUQDQgAE9FsHcO9ApZ7CIg0ae0v8eCpTJn9yFLlWo/ckdc2DWJpqG6+Ab3IN
73lHwsaq2p1/RD6o9eICHlVFVU/DZ+5KzQ==
-----END EC PRIVATE KEY-----""")
        self.signer = RequestSigner(DEV_KEY)
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
