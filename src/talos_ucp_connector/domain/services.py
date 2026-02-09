import uuid
from typing import Dict, Any, Optional, List
from talos_ucp_connector.ports.spi import (
    CheckoutLifecycleInboundPort, 
    ConfigurationInboundPort,
    MerchantCheckoutPort,
    DiscoveryPort,
    RequestSignerPort,
    ClockPort,
    ReplayStorePort,
    ConfigStorePort,
    AuditPort,
    PaymentPort
)
from talos_ucp_connector.domain.helpers import SigningHelper

class CommerceService(CheckoutLifecycleInboundPort, ConfigurationInboundPort):
    """
    Core Domain Service. 
    Orchestrates UCP flows using strict hexagonal ports.
    """
    def __init__(self, 
                 merchant_checkout: MerchantCheckoutPort,
                 discovery: DiscoveryPort,
                 signer: RequestSignerPort,
                 clock: ClockPort,
                 replay_store: ReplayStorePort,
                 config_store: ConfigStorePort,
                 audit: AuditPort,
                 payment: PaymentPort,
                 platform_profile_uri: str,
                 signing_kid: str):
        self.merchant_checkout = merchant_checkout
        self.discovery = discovery
        self.signer = signer
        self.clock = clock
        self.replay_store = replay_store
        self.config_store = config_store
        self.audit = audit
        self.payment = payment
        self.platform_profile_uri = platform_profile_uri
        self.signing_kid = signing_kid
        
        # In-memory discovery cache (Merchant domain -> REST endpoint)
        self._endpoint_cache: Dict[str, str] = {}

    def _get_base_url(self, merchant_domain: str) -> str:
        """Normative discovery of the merchant's UCP endpoint."""
        if merchant_domain in self._endpoint_cache:
            return self._endpoint_cache[merchant_domain]
            
        profile = self.discovery.fetch_profile(merchant_domain)
        # Assuming rest.endpoint is in the profile per spec
        endpoint = profile.get("services", {}).get("dev.ucp.shopping", {}).get("rest", {}).get("endpoint")
        if not endpoint:
            # Fallback for dev if not in profile, but in prod we should fail
            endpoint = f"https://{merchant_domain}/api/shopping/v1"
        
        self._endpoint_cache[merchant_domain] = endpoint
        return endpoint

    def _execute_signed_request(self, 
                                merchant_domain: str, 
                                method: str, 
                                path: str, 
                                query_params: Dict[str, str], 
                                body: Optional[Dict[str, Any]], 
                                idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Orchestrates the construction, signing, and execution of a UCP request."""
        base_url = self._get_base_url(merchant_domain)
        full_url = f"{base_url}{path}"
        if query_params:
            full_url += f"?{SigningHelper.canonicalize_query(query_params)}"

        # 1. Prepare global headers
        jti = str(uuid.uuid4())
        iat = self.clock.now()
        
        headers = {
            "UCP-Agent": f'profile="{self.platform_profile_uri}"',
            "Content-Type": "application/json",
            "Talos-Signature-Meta": f'iat={iat},jti="{jti}"'
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        
        envelope = SigningHelper.create_envelope(
            method=method,
            path=path,
            query_params=query_params,
            headers=headers,
            body=body,
            iat=iat,
            jti=jti
        )
        
        signature = self.signer.sign(envelope, self.signing_kid)
        headers["Request-Signature"] = signature

        # 3. Emit Audit Intent
        self.audit.emit_event("UCP_REQUEST_INTENT", {
            "method": method,
            "url": full_url,
            "request_id": headers.get("Request-Id", "unknown"),
            "jti": jti
        })

        # 4. Execute via Outbound Port
        try:
            if method == "POST":
                resp = self.merchant_checkout.post_checkout(full_url, body or {}, headers)
            elif method == "PUT":
                resp = self.merchant_checkout.put_checkout(full_url, body or {}, headers)
            elif method == "GET":
                resp = self.merchant_checkout.get_checkout(full_url, headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            self.audit.emit_event("UCP_REQUEST_SUCCESS", {"url": full_url})
            return resp
        except Exception as e:
            self.audit.emit_event("UCP_REQUEST_FAILURE", {"url": full_url, "error": str(e)})
            # TODO: Map to UCP Error Taxonomy
            raise e

    # --- CheckoutLifecycleInboundPort ---

    def create_checkout(self, merchant_domain: str, line_items: list, currency: str) -> Dict[str, Any]:
        if not self.config_store.is_merchant_allowlisted(merchant_domain):
            raise ValueError("UCP_POLICY_DENIED: Merchant not allowlisted")
            
        payload = {"line_items": line_items, "currency": currency, "mode": "payment"}
        return self._execute_signed_request(
            merchant_domain, "POST", "/checkout-sessions", {}, payload, str(uuid.uuid4())
        )

    def get_checkout(self, merchant_domain: str, session_id: str) -> Dict[str, Any]:
        return self._execute_signed_request(
            merchant_domain, "GET", f"/checkout-sessions/{session_id}", {}, None
        )

    def update_checkout(self, merchant_domain: str, session_id: str, checkout_payload: Dict[str, Any]) -> Dict[str, Any]:
        # Note: PUT per spec
        return self._execute_signed_request(
            merchant_domain, "PUT", f"/checkout-sessions/{session_id}", {}, checkout_payload, str(uuid.uuid4())
        )

    def complete_checkout(self, merchant_domain: str, session_id: str, amount_minor: int, currency: str) -> Dict[str, Any]:
        # 1. Payment Credentials
        payment_data = self.payment.get_credentials(currency, amount_minor, merchant_domain)
        
        # 2. Complete POST
        payload = {"payment_data": payment_data}
        return self._execute_signed_request(
            merchant_domain, "POST", f"/checkout-sessions/{session_id}/complete", {}, payload, str(uuid.uuid4())
        )

    def cancel_checkout(self, merchant_domain: str, session_id: str) -> Dict[str, Any]:
        return self._execute_signed_request(
            merchant_domain, "POST", f"/checkout-sessions/{session_id}/cancel", {}, None, str(uuid.uuid4())
        )

    # --- ConfigurationInboundPort ---

    def get_merchant_config(self, merchant_domain: str) -> Dict[str, Any]:
        return self.config_store.get_merchant_policy(merchant_domain)

    def update_merchant_config(self, merchant_domain: str, config: Dict[str, Any]) -> None:
        # In this prototype, we just emit audit and assume persistence in adapter
        self.audit.emit_event("CONFIG_UPDATE", {"merchant": merchant_domain, "config": config})
