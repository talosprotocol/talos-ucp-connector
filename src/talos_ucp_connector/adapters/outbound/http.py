import httpx
import uuid
import ssl
import socket
import ipaddress
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from talos_ucp_connector.ports.spi import DiscoveryPort, MerchantCheckoutPort, RequestSignerPort
from talos_ucp_connector.domain.errors import TransportError

def _validate_ssrf(url_or_domain: str) -> None:
    """
    Prevents Server-Side Request Forgery (SSRF) by blocking private IP ranges.
    Normative check before any outbound request.
    """
    if "://" in url_or_domain:
        parsed = urlparse(url_or_domain)
        hostname = parsed.hostname
    else:
        hostname = url_or_domain

    if not hostname:
        return

    try:
        # Resolve hostname to IP address
        ip_address = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_address)

        # Private ranges as specified in requirements
        private_ranges = [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("127.0.0.0/8"),
        ]

        for network in private_ranges:
            if ip in network:
                raise TransportError("Potential SSRF detected: Private IP range blocked")
    except socket.gaierror:
        # Resolution failure is handled by the HTTP client later
        pass

class HttpDiscoveryAdapter(DiscoveryPort):
    def __init__(self, client: Optional[httpx.Client] = None):
        # Enforce TLS 1.3
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        self.client = client or httpx.Client(timeout=10.0, verify=context)

    def fetch_profile(self, merchant_domain: str) -> Dict[str, Any]:
        _validate_ssrf(merchant_domain)
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
        _validate_ssrf(url)
        req_headers = self._prepare_headers(headers)
        resp = self.client.post(url, json=payload, headers=req_headers)
        resp.raise_for_status()
        return resp.json()

    def put_checkout(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        _validate_ssrf(url)
        req_headers = self._prepare_headers(headers)
        resp = self.client.put(url, json=payload, headers=req_headers)
        resp.raise_for_status()
        return resp.json()

    def get_checkout(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        _validate_ssrf(url)
        req_headers = self._prepare_headers(headers)
        resp = self.client.get(url, headers=req_headers)
        resp.raise_for_status()
        return resp.json()

    def get_order(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        _validate_ssrf(url)
        req_headers = self._prepare_headers(headers)
        resp = self.client.get(url, headers=req_headers)
        resp.raise_for_status()
        return resp.json()

    def list_orders(self, url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        _validate_ssrf(url)
        req_headers = self._prepare_headers(headers)
        resp = self.client.get(url, headers=req_headers)
        resp.raise_for_status()
        # SPEC: UCP List endpoints return a dictionary with "items" key or a direct list
        data = resp.json()
        return data.get("items", []) if isinstance(data, dict) else data
