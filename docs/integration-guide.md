# UCP Integration Guide for Google Antigravity

This guide details how to integrate the Universal Commerce Protocol (UCP) into autonomous agent workflows using the Talos SDK.

## 1. Prerequisites

- **Talos SDK**: Ensure `talos-sdk-py` (v1.2.0+) or `talos-sdk-ts` (v4.0.0+) is installed.
- **Identity**: Agent must possess a valid DID and Ed25519 identity keypair.
- **MCP Connection**: The `talos-ucp-connector` must be running and accessible via the Talos AI Gateway.

## 2. Agent Capability Setup

To interact with UCP endpoints, the agent requires a scoped capability token. The Supervisor must sign a token granting commerce privileges.

**Required Scope:** `ucp:checkout:write`

```python
# Python SDK Example
from talos_sdk import Wallet, Capability

# Request capability for commerce
capability = await client.request_capability(
    scope="ucp:checkout:write",
    resource="ucp://merchant-network",
    ttl=3600
)
# Supervisor signs capability via Ed25519
```

## 3. Checkout Flow

The UCP checkout process follows a stateful lifecycle: `Create` → `Update` → `Sign/Complete`.

### Step A: Create Checkout

Initialize a session with a specific merchant DID.

```python
checkout = await ucp.create_checkout(
    merchant_did="did:web:store.example.com",
    currency="USD"
)
print(checkout.id)  # e.g., "chk_12345"
```

### Step B: Update Cart

Add items to the pending transaction.

```python
await ucp.update_checkout(
    checkout_id="chk_12345",
    items=[{"sku": "cloud-gpu-h100", "qty": 1}]
)
```

### Step C: Complete with Signing

The final step requires a cryptographic signature from the agent's Identity Key to ensure non-repudiation.

```python
# Sign the checkout manifest
signature = wallet.sign(checkout.manifest_hash)

# Submit proof of transaction
receipt = await ucp.complete_checkout(
    checkout_id="chk_12345",
    signature=signature,
    payment_credential="<opaque-token>"  # Handled via Wallet Provider
)
```

## 4. Audit Trail

Every UCP action generates a Merkle leaf in the `talos-audit-service`.

- **Retrieval**: Query via `GET /audit/v1/events?tag=ucp&transaction_id=chk_12345`
- **Verification**: Ensure the returned Merkle proof anchors to a valid root hash published on the dashboard

## 5. Error Handling

UCP errors map to standard HTTP codes but include detailed sub-codes in the body.

| Error Code | Meaning | Mitigation |
|------------|---------|------------|
| `UCP_AUTH_INVALID` | Capability token expired or wrong scope | Request new token via `talos-governance-agent` |
| `UCP_MERCHANT_POLICY` | Request violates merchant T&C | Agent must renegotiate or modify cart items |
| `UCP_BUDGET_EXCEEDED` | Payment exceeds authorized limit | Supervisor intervention required |

## 6. Security Model

### Signing

All UCP requests are signed using **Ed25519** to maintain consistency with the Talos identity layer. The signing envelope includes:

- Method, path, query parameters
- Headers (`UCP-Agent`, `Request-Id`, `Idempotency-Key`)
- Body (JCS-canonicalized per RFC 8785)
- Timestamp (`iat`) and nonce (`jti`)

### Policy Enforcement

Before any UCP request, the connector validates:

1. **Merchant Allowlist**: Is the target merchant in the approved list?
2. **Spend Limits**: Does the transaction amount exceed `max_spend_minor`?
3. **Currency Restrictions**: Is the currency in `allowed_currencies`?

## References

1. [UCP Protocol Specification](https://ucp.network)
2. [Talos Governance Agent](../../governance-agent/README.md)
3. [Talos Audit Service](../audit/README.md)
