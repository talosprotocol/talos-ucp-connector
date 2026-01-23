# Talos UCP Connector

Allows Talos Agents to transact on the [Universal Commerce Protocol (UCP)](https://ucp.network).

## Architecture

This service follows **Hexagonal Architecture** (Ports & Adapters):

- **Domain**: Pure business logic (`src/talos_ucp_connector/domain`). Independent of frameworks.
- **Ports**: Abstract interfaces (`src/talos_ucp_connector/ports`).
- **Adapters**:
  - **Inbound**: FastMCP Server (`adapters/inbound/mcp_server.py`).
  - **Outbound**: HTTP, Payment, Policy (`adapters/outbound`).
- **Bootstrap**: Dependency Injection (`bootstrap/container.py`).

## Usage

### Run with MCP

```bash
uv run talos-ucp
# or
pip install .
talos-ucp
```

### Configuration

Set the following environment variables (or rely on defaults for dev):

- `PLATFORM_PROFILE_URI`: Your connector's public profile URI.

### Policy

Configure `allowed_merchants` and `max_spend` in `container.py` (or inject via config loader).

## References
1. [Talos Wiki](https://github.com/talosprotocol/talos/wiki)
