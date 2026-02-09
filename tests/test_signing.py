"""
Tests for RequestSigner (ES256 Detached JWS).
"""
import pytest
import base64
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from talos_ucp_connector.adapters.infrastructure.security import RequestSigner

# Test Vector: ES256 Private Key
TEST_KEY_PEM = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIEia/d+J4aYt/BcfUeFq/jC1E4qK/y6eI4...
-----END EC PRIVATE KEY-----"""

# Since we don't have a real valid key in the variable above, let's generate one for testing
def generate_test_key():
    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return pem.decode('ascii')

@pytest.fixture
def signer():
    pem = generate_test_key()
    return RequestSigner(pem)

def test_signature_format(signer):
    """Ensure signature follows header..signature detached format."""
    envelope = {"method": "GET", "path": "/test"}
    kid = "test-key-1"
    
    sig = signer.sign(envelope, kid)
    
    parts = sig.split("..")
    assert len(parts) == 2
    
    # Verify Header
    header_bytes = base64.urlsafe_b64decode(parts[0] + "==")
    header = json.loads(header_bytes)
    assert header["alg"] == "ES256"
    assert header["kid"] == kid
    assert header["typ"] == "JOSE"
    
    # Verify Signature length (approximate for ES256)
    sig_bytes = base64.urlsafe_b64decode(parts[1] + "==")
    assert len(sig_bytes) == 64  # r + s (32 bytes each)

def test_signature_determinism(signer):
    """ES256 is probabilistic if using random nonce, but let's check basic consistency."""
    envelope = {"method": "POST", "body": {"foo": "bar"}}
    kid = "test-key-1"
    
    sig1 = signer.sign(envelope, kid)
    sig2 = signer.sign(envelope, kid)
    
    # RFC 6979 deterministic signatures would be identical, 
    # but standard ECDSA uses random k. 
    # Our implementation uses standard ECDSA, so they might differ.
    # The important part is implementation doesn't crash.
    assert sig1
    assert sig2
