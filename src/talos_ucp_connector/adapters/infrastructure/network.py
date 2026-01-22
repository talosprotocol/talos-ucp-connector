import ipaddress
import socket
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SecurityViolation(Exception):
    pass

class OutboundNetworkGuard:
    """
    Enforces strict network security policies for outbound calls.
    Protects against SSRF, private network access, and insecure protocols.
    """

    @staticmethod
    def validate_url(url: str):
        """
        Validates a URL against UCP security, constraints.
        Raises SecurityViolation if invalid.
        """
        parsed = urlparse(url)
        
        # 1. Enforce HTTPS
        if parsed.scheme != "https":
            raise SecurityViolation(f"Insecure scheme: {parsed.scheme}. HTTPS required.")

        hostname = parsed.hostname
        if not hostname:
            raise SecurityViolation("Missing hostname")

        # 2. Prevent IP Literals (Policy choice: enforce DNS names for merchants)
        try:
            ipaddress.ip_address(hostname)
            # If it parses as IP, we check if it's private, then reject anyway if we want strict DNS policy
            # But let's verify it's not private if we were to allow it.
            # Ideally UCP merchants should have domains.
            # For now, allow public IPs but prefer domains.
            OutboundNetworkGuard._validate_ip_str(hostname)
        except ValueError:
            # It's a domain name. Resolve it to check for DNS rebinding / private IP resolution
            OutboundNetworkGuard._resolve_and_check(hostname)

    @staticmethod
    def _validate_ip_str(ip_str: str):
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
             raise SecurityViolation(f"Target IP {ip_str} is private/local. Access denied.")

    @staticmethod
    def _resolve_and_check(hostname: str):
        try:
            # Simple resolution check. 
            # Note: A robust Anti-Rebinding usually requires the HTTP client to use the resolved IP 
            # directly rather than resolving here and then letting the client resolve again (TOCTOU).
            # For Phase 1, we do this check as a "Best Effort" gate, 
            # but ideally we configure the HTTP transport to use a specific Resolver.
            ips = socket.getaddrinfo(hostname, None)
            for item in ips:
                # sockaddr is index 4. For IP protocols, index 0 of sockaddr is the IP string.
                sockaddr = item[4]
                ip_addr = str(sockaddr[0]) 
                OutboundNetworkGuard._validate_ip_str(ip_addr)
        except socket.gaierror:
            # If we can't resolve it, it might be unreachable, but not necessarily insecure yet.
            # Letting it proceed might fail later.
            pass
