import json
import uuid
import time
import base64
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
import rfc8785
import http_sfv

def canonicalize_query(params: Dict[str, str]) -> str:
    """Canonical query string: sorted by (name, value) lexicographically."""
    sorted_params = sorted(params.items())
    import urllib.parse
    return urllib.parse.urlencode(sorted_params)

def canonicalize_ucp_agent(agent_str: str) -> str:
    """Parse as RFC 8941 Dictionary and re-serialize."""
    dict_val = http_sfv.Dictionary()
    dict_val.parse(agent_str.encode('ascii'))
    return str(dict_val)

def create_signing_envelope(
    method: str,
    path: str,
    query_params: Dict[str, str],
    headers: Dict[str, str],
    body: Optional[Dict[str, Any]],
    iat: int,
    jti: str
) -> Dict[str, Any]:
    """Constructs the canonical signing envelope."""
    query_string = canonicalize_query(query_params)
    processed_headers = {k.lower(): v for k, v in headers.items()}
    if 'ucp-agent' in processed_headers:
        processed_headers['ucp-agent'] = canonicalize_ucp_agent(processed_headers['ucp-agent'])
    
    envelope = {
        "method": method.upper(),
        "path": path,
        "query": query_string,
        "headers": processed_headers,
        "body": body if body is not None else None,
        "meta": {
            "iat": iat,
            "jti": jti
        }
    }
    return envelope

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')

def sign_option_a(envelope: Dict[str, Any], private_key_pem: str, kid: str) -> str:
    """
    Option A: Detached JWS <protected>..<sig>
    Signing Level: JWS Compact Signature Input = BASE64URL(UTF8(JCS(header))) + "." + BASE64URL(JCS(envelope))
    """
    header = {"alg": "ES256", "kid": kid, "typ": "JOSE"}
    header_bytes = rfc8785.dumps(header)
    header_b64 = base64url_encode(header_bytes)
    
    envelope_bytes = rfc8785.dumps(envelope)
    envelope_b64 = base64url_encode(envelope_bytes)
    
    signing_input = f"{header_b64}.{envelope_b64}".encode('ascii')
    
    # Load key
    key = serialization.load_pem_private_key(private_key_pem.encode('ascii'), password=None)
    raw_sig = key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    
    # ECDSA signature is (r, s) in ASN.1. JWS wants raw 64 bytes (R | S)
    r, s = decode_dss_signature(raw_sig)
    # Each is 32 bytes for P-256
    sig_bytes = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
    sig_b64 = base64url_encode(sig_bytes)
    
    return f"{header_b64}..{sig_b64}"

def verify_option_a(detached_jws: str, envelope: Dict[str, Any], public_key_pem: str) -> bool:
    """Verifies a detached JWS against an envelope."""
    parts = detached_jws.split('.')
    if len(parts) != 3 or parts[1] != "":
        return False
    
    header_b64 = parts[0]
    sig_b64 = parts[2]
    
    # Reconstruct signing input
    envelope_bytes = rfc8785.dumps(envelope)
    envelope_b64 = base64url_encode(envelope_bytes)
    signing_input = f"{header_b64}.{envelope_b64}".encode('ascii')
    
    # Decode signature from raw 64 bytes to (r, s) for cryptography
    def base64url_decode(s: str) -> bytes:
        padding = '=' * (4 - (len(s) % 4))
        return base64.urlsafe_b64decode(s + padding)

    sig_raw = base64url_decode(sig_b64)
    r = int.from_bytes(sig_raw[:32], 'big')
    s = int.from_bytes(sig_raw[32:], 'big')
    asn1_sig = encode_dss_signature(r, s)
    
    # Load key
    key = serialization.load_pem_public_key(public_key_pem.encode('ascii'))
    
    try:
        key.verify(asn1_sig, signing_input, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception as e:
        print(f"Verification FAILED: {e}")
        return False

# --- PROOF EXECUTION ---

# 1. Setup Keys
private_key = ec.generate_private_key(ec.SECP256R1())
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('ascii')

public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('ascii')

# 2. Mock Request
mock_envelope = create_signing_envelope(
    method="POST",
    path="/checkout-sessions",
    query_params={"debug": "true", "version": "1"},
    headers={
        "UCP-Agent": 'profile="talos-gateway"',
        "Request-Id": str(uuid.uuid4())
    },
    body={"amount": 1000, "currency": "USD"},
    iat=int(time.time()),
    jti=str(uuid.uuid4())
)

print("\n--- Canonical Envelope (JSON) ---")
print(json.dumps(mock_envelope, indent=2))

# 3. Sign
signature = sign_option_a(mock_envelope, private_pem, "talos-dev-key")
print("\n--- Detached JWS (Option A) ---")
print(signature)

# 4. Verify
is_valid = verify_option_a(signature, mock_envelope, public_pem)
print(f"\n--- Verification Result: {'PASSED' if is_valid else 'FAILED'} ---")

# 5. Tamper Test
tampered_envelope = mock_envelope.copy()
tampered_envelope["path"] = "/malicious-endpoint"
is_tamper_detected = not verify_option_a(signature, tampered_envelope, public_pem)
print(f"--- Tamper Test (Path Mutation): {'DETECTED' if is_tamper_detected else 'FAILED'} ---")

# 6. GET Request with Null Body Proof
get_envelope = create_signing_envelope(
    method="GET",
    path="/checkout-sessions/cs_123",
    query_params={},
    headers={"UCP-Agent": 'profile="talos-gateway"'},
    body=None,
    iat=int(time.time()),
    jti=str(uuid.uuid4())
)
print("\n--- GET Envelope (Null Body) ---")
print(json.dumps(get_envelope, indent=2))
get_sig = sign_option_a(get_envelope, private_pem, "talos-dev-key")
print(f"GET Verification: {'PASSED' if verify_option_a(get_sig, get_envelope, public_pem) else 'FAILED'}")
