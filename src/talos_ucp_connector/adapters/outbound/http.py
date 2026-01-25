import httpx
import uuid
import ssl
from typing import Dict, Any, List, Optional
from ...ports.spi import DiscoveryPort, MerchantCheckoutPort, RequestSignerPort

class HttpDiscoveryAdapter(DiscoveryPort):
    def __init__(self, client: Optional[httpx.Client] = None):
        # Enforce TLS 1.3
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        self.client = client or httpx.Client(timeout=10.0, verify=context)

    def fetch_profile(self, merchant_domain: str) -> Dict[str, Any]:
        url = f"https://{merchant_domain}/.well-known/ucp"
        resp = self.client.get(url)
        resp.raise_for_status()
        return resp.json()

class HttpMerchantCheckoutAdapter(MerchantCheckoutPort):
    def __init__(self, client: Optional[httpx.Client] = None):
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        self.client = client or httpx.Client(timeout=30.0, verify=context)

    def _prepare_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        req_headers = headers.copy()
        req_headers["Request-Id"] = str(uuid.uuid4())
        # UCP-Agent is usually added by the service/domain layer calling this
        return req_headers

    def post_checkout(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        req_headers = self._prepare_headers(headers)
        resp = self.client.post(url, json=payload, headers=req_headers)
        resp.raise_for_status()
        return resp.json()

    def put_checkout(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        req_headers = self._prepare_headers(headers)
        resp = self.client.put(url, json=payload, headers=req_headers)
        resp.raise_for_status()
        return resp.json()

    def get_checkout(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        req_headers = self._prepare_headers(headers)
        resp = self.client.get(url, headers=req_headers)
        resp.raise_for_status()
        return resp.json()
