# Talos UCP Connector

**Repo Role**: MCP server enabling Talos agents to transact on the [Universal Commerce Protocol (UCP)](https://ucp.network).

## Overview

The UCP Connector provides secure, policy-enforced commerce capabilities for autonomous agents. It implements the checkout lifecycle from the UCP Shopping specification while integrating with:

- **Talos Identity**: Agent DIDs for non-repudiation
- **Talos Governance**: Capability tokens for authorization
- **Talos Audit**: Merkle-proofed transaction logs

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Talos Agent                                  │
│             (Requests checkout via MCP tool calls)                  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     talos-ucp-connector                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Inbound Adapter                              │ │
│  │                 mcp_server.py (FastMCP)                        │ │
│  │   ucp_checkout_create | get | update | complete | cancel       │ │
│  └────────────────────────────┬───────────────────────────────────┘ │
│                               │                                      │
│  ┌────────────────────────────▼───────────────────────────────────┐ │
│  │                    Domain Layer                                 │ │
│  │     CommerceService (services.py)                              │ │
│  │  • Discovery caching   • Signed request orchestration          │ │
│  │  • Policy enforcement  • Audit event emission                  │ │
│  └────────────────────────────┬───────────────────────────────────┘ │
│                               │                                      │
│  ┌────────────────────────────▼───────────────────────────────────┐ │
│  │                   Outbound Adapters                             │ │
│  │  HTTP Client │ Discovery │ Signer │ Payment │ Config │ Audit   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      UCP Merchant                                    │
│            /.well-known/ucp + /checkout-sessions API                │
└─────────────────────────────────────────────────────────────────────┘
```

## MCP Tool Reference

| Tool | Description | Parameters |
|------|-------------|------------|
| `ucp_checkout_create` | Create new checkout session | `merchant_domain`, `line_items`, `currency` |
| `ucp_checkout_get` | Retrieve session details | `merchant_domain`, `session_id` |
| `ucp_checkout_update` | Modify cart/session (PUT) | `merchant_domain`, `session_id`, `checkout_payload` |
| `ucp_checkout_complete` | Finalize with payment | `merchant_domain`, `session_id`, `amount_minor`, `currency` |
| `ucp_checkout_cancel` | Cancel active session | `merchant_domain`, `session_id` |

### Example: Create Checkout

```python
# Via MCP (agent perspective)
result = await mcp_client.call_tool(
    "ucp_checkout_create",
    merchant_domain="store.example.com",
    line_items=[{"name": "GPU Instance", "price_minor": 10000, "qty": 1}],
    currency="USD"
)
# Returns: {"id": "cs_abc123", "status": "open", ...}
```

## Security Model

### Signing (Ed25519)

All outbound requests include a `Request-Signature` header containing a detached JWS:

1. **Envelope Construction**: Method, path, headers, body (JCS-canonicalized)
2. **Signature**: Ed25519 over base64url(header) + "." + base64url(payload)
3. **Format**: `<header>..<signature>` (detached payload per RFC 7797)

### Policy Enforcement

Before any merchant request, the connector validates:

| Constraint | Config Key | Behavior |
|------------|------------|----------|
| Merchant Allowlist | `allowed_merchants` | Fail closed if not listed |
| Spend Limit | `max_spend_minor` | Reject if amount exceeds limit |
| Currency | `allowed_currencies` | Reject if currency not permitted |

### Audit Events

Every operation emits to `talos-audit-service`:

- `UCP_REQUEST_INTENT`: Before sending (includes `jti`, `url`)
- `UCP_REQUEST_SUCCESS`: On 2xx response
- `UCP_REQUEST_FAILURE`: On error (includes error details)

Sensitive data (payment credentials, PII) is **redacted** before logging.

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PLATFORM_PROFILE_URI` | Yes | Public URI of connector's UCP profile |
| `SIGNING_KID` | Yes | Key ID for Request-Signature |
| `ALLOWED_MERCHANTS` | No | Comma-separated allowlist (default: none) |
| `MAX_SPEND_MINOR` | No | Integer spend limit in minor units |

### Example Configuration

```python
# In container.py or via environment
CONFIG = {
    "platform_profile_uri": "https://talos.example.com/.well-known/ucp",
    "signing_kid": "talos-prod-key-1",
    "merchants": {
        "store.example.com": {"max_spend": 100000}
    }
}
```

## Deployment

### Mode A: Hosted (Recommended)

Deploy in Talos infrastructure with public HTTPS:

- Required for merchant discovery of platform profile
- Required for webhook delivery (Phase 4+)

```bash
uv run talos-ucp
# Listens on MCP transport (stdio/SSE)
```

### Mode B: Local (Development Only)

For testing without webhooks:

```bash
pip install -e .
talos-ucp
```

## Development

To run the tests, ensure you have a standard Python environment with `pip` available.

```bash
# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

### Type Checking
```bash
mypy src/
```

### Verify Signing
```bash
python library_proof_signing.py
```

## Open Decisions (v1)

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| Hosting | Talos Infra (Public) | Merchants must fetch platform profile |
| Key Type | **Ed25519** | Consistency with Talos identity layer |
| Search Scope | Checkout-only | v1 focuses on transaction execution |

## References

1. [UCP Protocol Specification](https://ucp.network)
2. [Integration Guide](docs/integration-guide.md)
3. [Implementation Plan](../../implementation_plan_ucp.md)
4. [Talos Protocol](../../PROTOCOL.md)

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
