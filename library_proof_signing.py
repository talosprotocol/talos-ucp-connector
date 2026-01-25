import json
import base64
from typing import Dict, Any, Optional, cast
import rfc8785
import http_sfv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives import serialization

# --- CANONICALIZATION ENGINE ---

class UcpCanonicalizer:
    @staticmethod
    def canonicalize_jcs(data: Dict[str, Any]) -> bytes:
        """RFC 8785: JSON Canonicalization Scheme (JCS)."""
        return rfc8785.dumps(data)

    @staticmethod
    def canonicalize_sfv_dict(sfv_str: str) -> str:
        """RFC 8941: Structured Field Values Dictionary serialization."""
        dict_val = http_sfv.Dictionary()
        dict_val.parse(sfv_str.encode('ascii'))
        return str(dict_val)

# --- SIGNING ENGINE (RULE A: DETACHED JWS) ---

class RequestSigner:
    def __init__(self, private_key_pem: str):
        self.private_key = serialization.load_pem_private_key(
            private_key_pem.encode('ascii'),
            password=None
        )

    def sign_request(self, 
                     method: str, 
                     path: str, 
                     query: str, 
                     headers: Dict[str, str], 
                     body: Optional[Dict[str, Any]], 
                     kid: str) -> str:
        
        # 1. Normalize Headers (subset for signing scope)
        signed_headers = {
            "ucp-agent": UcpCanonicalizer.canonicalize_sfv_dict(headers.get("UCP-Agent", "")),
            "request-id": headers.get("Request-Id", "")
        }
        if "Idempotency-Key" in headers:
            signed_headers["idempotency-key"] = headers["Idempotency-Key"]

        # 2. Construct Envelope
        envelope = {
            "method": method.upper(),
            "path": path,
            "query": query, # Pre-canonicalized by caller
            "headers": signed_headers,
            "body": body if body is not None else None,
            "meta": {
                "iat": headers.get("X-UCP-Iat"), # Assuming meta sent in headers for proof
                "jti": headers.get("X-UCP-Jti")
            }
        }

        # 3. JCS Canonicalization
        payload_bytes = UcpCanonicalizer.canonicalize_jcs(envelope)
        
        # 4. Create JWS Protected Header
        jws_header = {
            "alg": "ES256",
            "kid": kid,
            "typ": "JOSE"
        }
        header_b64 = base64.urlsafe_b64encode(json.dumps(jws_header).encode('utf-8')).decode('ascii').rstrip('=')
        
        # 5. Signing Input (Detached: Header . B64(Payload))
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('ascii').rstrip('=')
        signing_input = f"{header_b64}.{payload_b64}".encode('ascii')

        # 6. Generate Signature
        if isinstance(self.private_key, ec.EllipticCurvePrivateKey):
            signature = self.private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        else:
            raise TypeError("Only EC ES256 keys supported for UCP Option A proof")
            
        sig_b64 = base64.urlsafe_b64encode(signature).decode('ascii').rstrip('=')

        # 7. Return Detached JWS format: Header..Signature
        return f"{header_b64}..{sig_b64}"

# --- VERIFICATION PROOF ---

def verify_ucp_signature(sig_header: str, envelope: Dict[str, Any], public_key_pem: str) -> bool:
    try:
        parts = sig_header.split('.')
        if len(parts) != 3 or parts[1] != "":
            return False
        
        header_b64, _, sig_b64 = parts
        
        # Reconstruct signing input
        payload_bytes = UcpCanonicalizer.canonicalize_jcs(envelope)
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('ascii').rstrip('=')
        signing_input = f"{header_b64}.{payload_b64}".encode('ascii')
        
        # Load Key
        public_key = serialization.load_pem_public_key(public_key_pem.encode('ascii'))
        signature = base64.urlsafe_b64decode(sig_b64 + '==')

        if isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(signature, signing_input, ec.ECDSA(hashes.SHA256()))
            return True
        return False
    except Exception as e:
        print(f"Verification Error: {e}")
        return False

# --- LIVE TEST CASE ---

if __name__ == "__main__":
    # Mock Key Pair
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('ascii')
    
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('ascii')

    signer = RequestSigner(private_pem)
    
    mock_headers = {
        "UCP-Agent": 'profile="talos-gateway-v1", vendor="Talos"',
        "Request-Id": "550e8400-e29b-41d4-a716-446655440000",
        "X-UCP-Iat": "1706176800",
        "X-UCP-Jti": "nonce-999"
    }
    
    # Test signing a GET request (Rule A)
    sig = signer.sign_request("GET", "/checkout-sessions/cs_123", "", mock_headers, None, "talos-dev-key")
    print(f"Generated Signature: {sig}")

    # Reconstruct envelope for verification
    envelope = {
        "method": "GET",
        "path": "/checkout-sessions/cs_123",
        "query": "",
        "headers": {
            "ucp-agent": UcpCanonicalizer.canonicalize_sfv_dict(mock_headers["UCP-Agent"]),
            "request-id": mock_headers["Request-Id"]
        },
        "body": None,
        "meta": {"iat": "1706176800", "jti": "nonce-999"}
    }
    
    is_valid = verify_ucp_signature(sig, envelope, public_pem)
    print(f"Verification Result: {'PASSED' if is_valid else 'FAILED'}")

    # Tamper Test: Change path
    envelope["path"] = "/checkout-sessions/STOLEN"
    is_valid_tampered = verify_ucp_signature(sig, envelope, public_pem)
    print(f"Tamper Test (Path Mutation): {'DETECTED' if not is_valid_tampered else 'FAILED'}")
