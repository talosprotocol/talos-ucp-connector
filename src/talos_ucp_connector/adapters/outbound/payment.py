from typing import Dict, Any
from talos_ucp_connector.ports.spi import PaymentPort

class SandboxPaymentAdapter(PaymentPort):
    def get_credentials(self, currency: str, amount_minor: int, merchant_domain: str) -> Dict[str, Any]:
        return {
            "type": "sandbox_token",
            "token": "tok_hexagonal_sandbox",
            "currency": currency
        }
