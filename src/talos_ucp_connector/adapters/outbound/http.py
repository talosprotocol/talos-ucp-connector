import httpx
import uuid
from typing import Dict, Any, List
from ...ports.spi import DiscoveryPort, CheckoutPort
from ..infrastructure.network import OutboundNetworkGuard

class HttpDiscoveryAdapter(DiscoveryPort):
    def __init__(self, client: httpx.Client = None):
        self.client = client or httpx.Client(timeout=10.0)

    def fetch_profile(self, merchant_domain: str) -> Dict[str, Any]:
        url = f"https://{merchant_domain}/.well-known/ucp"
        OutboundNetworkGuard.validate_url(url)
        resp = self.client.get(url)
        resp.raise_for_status()
        return resp.json()

class HttpCheckoutAdapter(CheckoutPort):
    def __init__(self, client: httpx.Client = None):
        self.client = client or httpx.Client(timeout=30.0)

    def _get_base_url(self, merchant_domain: str) -> str:
        return f"https://{merchant_domain}/api/shopping/v1"

    def create_session(self, merchant_domain: str, line_items: list, currency: str, headers: Dict[str, str]) -> Dict[str, Any]:
        endpoint = self._get_base_url(merchant_domain) + "/checkout-sessions"
        OutboundNetworkGuard.validate_url(endpoint)
        
        payload = {"line_items": line_items, "currency": currency, "mode": "payment"}
        req_headers = headers.copy()
        req_headers["Idempotency-Key"] = str(uuid.uuid4())
        
        resp = self.client.post(endpoint, json=payload, headers=req_headers)
        resp.raise_for_status()
        return resp.json()

    def complete_session(self, merchant_domain: str, session_id: str, payment_data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        endpoint = self._get_base_url(merchant_domain) + f"/checkout-sessions/{session_id}/complete"
        OutboundNetworkGuard.validate_url(endpoint)
        
        payload = {"payment_data": payment_data}
        req_headers = headers.copy()
        req_headers["Idempotency-Key"] = str(uuid.uuid4())
        
        resp = self.client.post(endpoint, json=payload, headers=req_headers)
        resp.raise_for_status()
        return resp.json()
