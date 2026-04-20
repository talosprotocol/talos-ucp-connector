import pytest
import httpx
from unittest.mock import MagicMock, patch
from talos_ucp_connector.adapters.outbound.http import HttpDiscoveryAdapter
from talos_ucp_connector.domain.services import CommerceService
from talos_ucp_connector.domain.errors import TransportError, UCPError, TalosErrorCode

def test_http_discovery_adapter_ssrf_protection():
    adapter = HttpDiscoveryAdapter()
    
    # Test with a private IP (127.0.0.1)
    with patch("socket.gethostbyname") as mock_gethost:
        mock_gethost.return_value = "127.0.0.1"
        with pytest.raises(TransportError) as excinfo:
            adapter.fetch_profile("localhost")
        assert "Potential SSRF detected" in str(excinfo.value)

    # Test with another private range (10.0.0.5)
    with patch("socket.gethostbyname") as mock_gethost:
        mock_gethost.return_value = "10.0.0.5"
        with pytest.raises(TransportError) as excinfo:
            adapter.fetch_profile("internal.system")
        assert "Potential SSRF detected" in str(excinfo.value)

    # Test with a public IP (example.com)
    with patch("socket.gethostbyname") as mock_gethost:
        mock_gethost.return_value = "93.184.216.34"
        with patch.object(adapter.client, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            mock_get.return_value.json.return_value = {"ok": True}
            profile = adapter.fetch_profile("example.com")
            assert profile == {"ok": True}

def test_commerce_service_error_mapping():
    # Mock dependencies
    merchant_checkout = MagicMock()
    discovery = MagicMock()
    signer = MagicMock()
    clock = MagicMock()
    replay_store = MagicMock()
    config_store = MagicMock()
    audit = MagicMock()
    payment = MagicMock()
    
    service = CommerceService(
        merchant_checkout=merchant_checkout,
        discovery=discovery,
        signer=signer,
        clock=clock,
        replay_store=replay_store,
        config_store=config_store,
        audit=audit,
        payment=payment,
        platform_profile_uri="https://talos.network/profile",
        signing_kid="key-1"
    )
    
    # Helper to create HTTPStatusError
    def raise_http_error(status_code):
        response = httpx.Response(status_code, request=httpx.Request("POST", "https://merchant.com"))
        raise httpx.HTTPStatusError("Error", request=response.request, response=response)

    # Mock discovery to return a base URL
    discovery.fetch_profile.return_value = {
        "services": {"dev.ucp.shopping": {"rest": {"endpoint": "https://merchant.com/api"}}}
    }
    # Mock allowlist
    config_store.is_merchant_allowlisted.return_value = True
    # Mock clock
    clock.now.return_value = 1234567890
    # Mock signer
    signer.sign.return_value = "mock-signature"
    
    # 1. Test 402 Payment Required -> INSUFFICIENT_FUNDS
    merchant_checkout.post_checkout.side_effect = lambda *args, **kwargs: raise_http_error(402)
    with pytest.raises(UCPError) as excinfo:
        service.create_checkout("merchant.com", [], "USD")
    assert excinfo.value.code == TalosErrorCode.INTERNAL
    assert "INSUFFICIENT_FUNDS" in excinfo.value.message

    # 2. Test 409 Conflict -> IDEMPOTENCY_VIOLATION
    merchant_checkout.post_checkout.side_effect = lambda *args, **kwargs: raise_http_error(409)
    with pytest.raises(UCPError) as excinfo:
        service.create_checkout("merchant.com", [], "USD")
    assert excinfo.value.code == TalosErrorCode.TALOS_INVALID_INPUT
    assert "IDEMPOTENCY_VIOLATION" in excinfo.value.message

    # 3. Test 503 Service Unavailable -> MERCHANT_UNAVAILABLE
    merchant_checkout.post_checkout.side_effect = lambda *args, **kwargs: raise_http_error(503)
    with pytest.raises(UCPError) as excinfo:
        service.create_checkout("merchant.com", [], "USD")
    assert excinfo.value.code == TalosErrorCode.TALOS_TRANSPORT_ERROR
    assert "MERCHANT_UNAVAILABLE" in excinfo.value.message
