from pydantic import BaseModel
from typing import Dict, Any

class LineItem(BaseModel):
    name: str
    amount_minor: int
    quantity: int = 1

class CheckoutSession(BaseModel):
    session_id: str
    merchant: str
    amount_minor: int
    currency: str
    status: str

class MerchantProfile(BaseModel):
    version: str
    services: Dict[str, Any]
