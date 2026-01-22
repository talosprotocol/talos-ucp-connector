from mcp.server.fastmcp import FastMCP # type: ignore
from ...bootstrap.container import Container
from ...domain.models import LineItem

# Initialize FastMCP (Infrastructure)
mcp = FastMCP("talos-ucp-connector")

# Initialize Container (Composition Root)
# In production, load config from env/yaml
CONFIG = {
    "policy": {
        "allowed_merchants": ["demo.ucp.dev", "shop.example.com"],
        "allowed_currencies": ["USD"],
        "max_spend_minor": 10000
    },
    "platform_profile_uri": "https://talos.network/.well-known/ucp"
}
container = Container(CONFIG)
service = container.commerce_service

@mcp.tool()
async def ucp_discover(merchant_domain: str):
    """
    Discovers UCP capabilities.
    """
    try:
        return service.discover_and_negotiate(merchant_domain)
    except Exception as e:
        return {"error": str(e), "merchant": merchant_domain}

@mcp.tool()
async def ucp_checkout_create(merchant_domain: str, line_items: list, currency: str):
    """
    Creates a new checkout session.
    """
    # Note: line_items passed as list, conversion to domain models inside adapter or service
    # here we assume list of dicts.
    try:
        return service.create_checkout(merchant_domain, line_items, currency)
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def ucp_checkout_complete(merchant_domain: str, session_id: str, amount_minor: int, currency: str):
    """
    Completes a checkout session.
    """
    try:
        return service.complete_checkout(merchant_domain, session_id, amount_minor, currency)
    except Exception as e:
        return {"error": str(e)}

def main():
    mcp.run()
