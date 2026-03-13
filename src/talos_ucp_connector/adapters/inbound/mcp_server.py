from typing import Optional

from mcp.server.fastmcp import FastMCP
import os
from talos_ucp_connector.bootstrap.container import Container

# Initialize MCP Server
mcp = FastMCP("talos-ucp-connector")

# Configuration (In production, load from env/consul/k8s)
CONFIG = {
    "merchants": {
        "merchant.example.com": {
            "policy": {"max_spend": 5000}
        }
    },
    "platform_profile_uri": "talos-gateway-v1",
    "security": {
        "kid": "talos-dev-key-1"
    }
}

# Bootstrapping
container = Container(CONFIG)
service = container.service


@mcp.tool()
async def ucp_checkout_create(
    merchant_domain: str,
    line_items: list,
    currency: str,
    extensions: Optional[dict] = None
):
    """
    Creates a new UCP checkout session.
    """
    try:
        return service.create_checkout(merchant_domain, line_items, currency, extensions)
    except Exception as e:
        return {"error": str(e), "code": "UCP_CREATE_FAILED"}


@mcp.tool()
async def ucp_checkout_get(merchant_domain: str, session_id: str):
    """
    Retrieves an existing UCP checkout session.
    """
    try:
        return service.get_checkout(merchant_domain, session_id)
    except Exception as e:
        return {"error": str(e), "code": "UCP_GET_FAILED"}


@mcp.tool()
async def ucp_checkout_update(
    merchant_domain: str,
    session_id: str,
    checkout_payload: dict,
    extensions: Optional[dict] = None
):
    """
    Updates an existing UCP checkout session (PUT semantic).
    """
    try:
        return service.update_checkout(merchant_domain, session_id, checkout_payload, extensions)
    except Exception as e:
        return {"error": str(e), "code": "UCP_UPDATE_FAILED"}


@mcp.tool()
async def ucp_checkout_complete(
    merchant_domain: str,
    session_id: str,
    amount_minor: int,
    currency: str
):
    """
    Completes a UCP checkout session by providing platform credentials.
    """
    try:
        return service.complete_checkout(merchant_domain, session_id, amount_minor, currency)
    except Exception as e:
        return {"error": str(e), "code": "UCP_COMPLETE_FAILED"}


@mcp.tool()
async def ucp_checkout_cancel(merchant_domain: str, session_id: str):
    """
    Cancels an active UCP checkout session.
    """
    try:
        return service.cancel_checkout(merchant_domain, session_id)
    except Exception as e:
        return {"error": str(e), "code": "UCP_CANCEL_FAILED"}


@mcp.tool()
async def ucp_order_get(merchant_domain: str, order_id: str):
    """
    Retrieves a UCP order by ID.
    """
    try:
        return service.get_order(merchant_domain, order_id)
    except Exception as e:
        return {"error": str(e), "code": "UCP_ORDER_GET_FAILED"}


@mcp.tool()
async def ucp_order_list(merchant_domain: str, limit: int = 100):
    """
    Lists recent UCP orders for the merchant.
    """
    try:
        return service.list_orders(merchant_domain, limit)
    except Exception as e:
        return {"error": str(e), "code": "UCP_ORDER_LIST_FAILED"}


@mcp.tool()
async def ucp_identity_link(merchant_domain: str, principal_id: str, ucp_buyer_id: str):
    """
    Links a Talos principal to a UCP merchant buyer identity.
    """
    try:
        return service.link_identity(merchant_domain, principal_id, ucp_buyer_id)
    except Exception as e:
        return {"error": str(e), "code": "UCP_IDENTITY_LINK_FAILED"}


@mcp.tool()
async def ucp_discover(merchant_did: str):
    """
    Fetches the /.well-known/ucp manifest to discover merchant capabilities.
    """
    try:
        return service.discover_merchant(merchant_did)
    except Exception as e:
        return {"error": str(e), "code": "UCP_DISCOVER_FAILED"}


def main():
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        port = int(os.getenv("PORT", "8084"))
        mcp.settings.port = port
        mcp.settings.host = "0.0.0.0"
        mcp.run(transport="sse")
    else:
        mcp.run()

if __name__ == "__main__":
    main()
