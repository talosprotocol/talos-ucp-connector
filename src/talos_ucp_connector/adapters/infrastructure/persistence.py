import json
from typing import Dict, Any
from ...ports.spi import ConfigStorePort, AuditPort

class ConfigStoreAdapter(ConfigStorePort):
    def __init__(self, config: Dict[str, Any]):
        # In a real app, this would be a DB or Config Service
        self.config = config
        self.merchants = config.get("merchants", {})

    def get_merchant_policy(self, merchant_domain: str) -> Dict[str, Any]:
        merchant = self.merchants.get(merchant_domain, {})
        return merchant.get("policy", {})

    def is_merchant_allowlisted(self, merchant_domain: str) -> bool:
        return merchant_domain in self.merchants

class AuditAdapter(AuditPort):
    def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        # For prototype, we log to stdout/file. In production, this goes to Audit Service.
        event = {
            "type": event_type,
            "data": data
        }
        print(f"[AUDIT] {json.dumps(event)}")
