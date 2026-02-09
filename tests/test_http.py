"""
Tests for Outbound HTTP Adapters.
"""
import pytest
from unittest.mock import MagicMock
import httpx
from talos_ucp_connector.adapters.outbound.http import HttpDiscoveryAdapter, HttpMerchantCheckoutAdapter

def test_discovery_adapter():
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"ucp": True}
    mock_client.get.return_value = mock_response
    
    adapter = HttpDiscoveryAdapter(client=mock_client)
    res = adapter.fetch_profile("merchant.com")
    
    assert res == {"ucp": True}
    mock_client.get.assert_called_with("https://merchant.com/.well-known/ucp")

def test_merchant_adapter_headers():
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {}
    mock_client.post.return_value = mock_response
    
    adapter = HttpMerchantCheckoutAdapter(client=mock_client)
    
    adapter.post_checkout(
        "https://api.com/checkout", 
        {"foo": "bar"}, 
        {"UCP-Agent": "talos"}
    )
    
    # Verify Request-Id injection
    call_kwargs = mock_client.post.call_args[1]
    headers = call_kwargs["headers"]
    
    assert "Request-Id" in headers
    assert headers["UCP-Agent"] == "talos"
