import base64
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
import rfc8785
from ...ports.spi import RequestSignerPort

class RequestSigner(RequestSignerPort):
    """
    Implements UCP-compliant Request signing (Option A).
    Uses ES256 and detached JCS-canonicalized envelope.
    """
    def __init__(self, private_key_pem: str):
        self.private_key = serialization.load_pem_private_key(
            private_key_pem.encode('ascii'), 
            password=None
        )

    def _base64url_encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')

    def sign(self, envelope: Dict[str, Any], kid: str) -> str:
        """
        Generates a detached JWS signature for the envelope.
        """
        # 1. Prepare JWS Header
        header = {"alg": "ES256", "kid": kid, "typ": "JOSE"}
        header_bytes = rfc8785.dumps(header)
        header_b64 = self._base64url_encode(header_bytes)
        
        # 2. Prepare Payload (JCS Canonicalized Envelope)
        envelope_bytes = rfc8785.dumps(envelope)
        envelope_b64 = self._base64url_encode(envelope_bytes)
        
        # 3. Create Signing Input
        signing_input = f"{header_b64}.{envelope_b64}".encode('ascii')
        
        # 4. Sign via ECDSA P-256 / SHA-256
        raw_sig = self.private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        
        # 5. Convert DERSIG (ASN.1) to Raw 64 Bytes (r | s) for JWS
        r, s = decode_dss_signature(raw_sig)
        sig_bytes = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
        sig_b64 = self._base64url_encode(sig_bytes)
        
        return f"{header_b64}..{sig_b64}"
