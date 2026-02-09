"""
Tests for CommerceService domain logic.
"""
import pytest
from unittest.mock import MagicMock, ANY
from talos_ucp_connector.domain.services import CommerceService
from talos_ucp_connector.ports.spi import (
    MerchantCheckoutPort, DiscoveryPort, RequestSignerPort,
    ClockPort, ReplayStorePort, ConfigStorePort, AuditPort, PaymentPort
)

@pytest.fixture
def mock_ports():
    return {
        "merchant_checkout": MagicMock(spec=MerchantCheckoutPort),
        "discovery": MagicMock(spec=DiscoveryPort),
        "signer": MagicMock(spec=RequestSignerPort),
        "clock": MagicMock(spec=ClockPort),
        "replay_store": MagicMock(spec=ReplayStorePort),
        "config_store": MagicMock(spec=ConfigStorePort),
        "audit": MagicMock(spec=AuditPort),
        "payment": MagicMock(spec=PaymentPort),
    }

@pytest.fixture
def service(mock_ports):
    # Setup default mocks
    mock_ports["discovery"].fetch_profile.return_value = {
        "services": {
            "dev.ucp.shopping": {
                "rest": {"endpoint": "https://api.merchant.com"}
            }
        }
    }
    mock_ports["config_store"].is_merchant_allowlisted.return_value = True
    mock_ports["clock"].now.return_value = "2023-01-01T00:00:00Z"
    mock_ports["signer"].sign.return_value = "header..sig"
    
    return CommerceService(
        **mock_ports,
        platform_profile_uri="https://talos.example.com",
        signing_kid="test-key"
    )

def test_create_checkout_flow(service, mock_ports):
    """Test standard checkout creation flow."""
    # Setup
    mock_ports["merchant_checkout"].post_checkout.return_value = {"id": "cs_123"}
    
    # Execute
    result = service.create_checkout(
        "merchant.com", 
        [{"id": "1", "price": 100}], 
        "USD"
    )
    
    # Verify
    assert result == {"id": "cs_123"}
    
    # Check Discovery
    mock_ports["discovery"].fetch_profile.assert_called_with("merchant.com")
    
    # Check Auditing
    mock_ports["audit"].emit_event.assert_any_call("UCP_REQUEST_INTENT", ANY)
    mock_ports["audit"].emit_event.assert_any_call("UCP_REQUEST_SUCCESS", ANY)
    
    # Check Signing
    mock_ports["signer"].sign.assert_called()
    
    # Check Outbound Call
    mock_ports["merchant_checkout"].post_checkout.assert_called_with(
        "https://api.merchant.com/checkout-sessions",
        {"line_items": [{"id": "1", "price": 100}], "currency": "USD", "mode": "payment"},
        ANY  # Headers
    )

def test_policy_denial(service, mock_ports):
    """Test fail-closed behavior for non-allowlisted merchants."""
    mock_ports["config_store"].is_merchant_allowlisted.return_value = False
    
    with pytest.raises(ValueError, match="UCP_POLICY_DENIED"):
        service.create_checkout("evil.com", [], "USD")

def test_complete_checkout(service, mock_ports):
    """Test completion flow with payment credential acquisition."""
    mock_ports["payment"].get_credentials.return_value = {"token": "opaque_123"}
    mock_ports["merchant_checkout"].post_checkout.return_value = {"status": "complete"}
    
    service.complete_checkout("merchant.com", "cs_123", 1000, "USD")
    
    mock_ports["payment"].get_credentials.assert_called_with("USD", 1000, "merchant.com")
    mock_ports["merchant_checkout"].post_checkout.assert_called_with(
        "https://api.merchant.com/checkout-sessions/cs_123/complete",
        {"payment_data": {"token": "opaque_123"}},
        ANY
    )
