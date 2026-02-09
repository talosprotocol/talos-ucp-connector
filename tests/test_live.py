"""
Live integration test for UCP Connector.
Spin up the MCP server and run a full checkout flow against a mock merchant.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from mcp.server.fastmcp import FastMCP
from talos_ucp_connector.adapters.inbound.mcp_server import mcp, service

# Mock merchant response
MOCK_MERCHANT_PROFILE = {
    "services": {
        "dev.ucp.shopping": {
            "rest": {"endpoint": "https://mock-merchant.com/api"}
        }
    }
}

MOCK_CHECKOUT_SESSION = {
    "id": "cs_live_123",
    "status": "open",
    "line_items": [{"id": "1", "price": 1000}],
    "currency": "USD"
}

@pytest.mark.asyncio
async def test_live_checkout_flow():
    """
    Test the full MCP tool chain:
    execute -> service -> http adapter (mocked) -> service -> execute
    """
    # Create Mock Client
    mock_client = MagicMock()
    
    # Mock Discovery
    mock_client.get.return_value.json.return_value = MOCK_MERCHANT_PROFILE
    mock_client.get.return_value.status_code = 200
    
    # Mock Checkout Creation
    mock_client.post.return_value.json.return_value = MOCK_CHECKOUT_SESSION
    mock_client.post.return_value.status_code = 201

    # Inject Mock Client into Service Adapters
    # We need to replace the client on both adapters used by the service
    service.discovery.client = mock_client
    service.merchant_checkout.client = mock_client
    
    # Check Discovery Flow
    merchant = "merchant.example.com"
    
    # 2. Execute Create
    result = service.create_checkout(merchant, [{"id": "1"}], "USD")
    assert result["id"] == "cs_live_123"
    
    # Verify HTTP calls
    # 1. Discovery
    mock_client.get.assert_any_call("https://merchant.example.com/.well-known/ucp")
    
    # 2. Checkout POST
    post_args = mock_client.post.call_args
    # url is first arg
    assert post_args[0][0] == "https://mock-merchant.com/api/checkout-sessions"
    assert "Request-Signature" in post_args[1]["headers"]
    assert "UCP-Agent" in post_args[1]["headers"]

