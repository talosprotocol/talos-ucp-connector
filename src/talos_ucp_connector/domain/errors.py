from enum import Enum
from typing import Optional, Dict, Any

class TalosErrorCode(str, Enum):
    """Canonical Talos error codes per ERROR_TAXONOMY.md"""
    TALOS_DENIED = "TALOS_DENIED"
    TALOS_INVALID_CAPABILITY = "TALOS_INVALID_CAPABILITY"
    TALOS_PROTOCOL_MISMATCH = "TALOS_PROTOCOL_MISMATCH"
    TALOS_FRAME_INVALID = "TALOS_FRAME_INVALID"
    TALOS_CRYPTO_ERROR = "TALOS_CRYPTO_ERROR"
    TALOS_INVALID_INPUT = "TALOS_INVALID_INPUT"
    TALOS_TRANSPORT_TIMEOUT = "TALOS_TRANSPORT_TIMEOUT"
    TALOS_TRANSPORT_ERROR = "TALOS_TRANSPORT_ERROR"
    RBAC_DENIED = "RBAC_DENIED"
    AUTH_REVOKED = "AUTH_REVOKED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_INVALID_SIGNATURE = "AUTH_INVALID_SIGNATURE"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL = "INTERNAL"

class UCPError(Exception):
    """Base class for all UCP Connector errors."""
    def __init__(
        self, 
        code: TalosErrorCode, 
        message: str, 
        details: Optional[Dict[str, Any]] = None, 
        request_id: Optional[str] = None,
        cause: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.request_id = request_id
        self.cause = cause
        super().__init__(f"[{self.code}] {self.message}")

    def to_dict(self) -> Dict[str, Any]:
        """Returns the canonical error object shape."""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "request_id": self.request_id,
            "cause": self.cause
        }

class PolicyDeniedError(UCPError):
    def __init__(self, message: str = "UCP_POLICY_DENIED: Merchant not allowlisted", details: Optional[Dict[str, Any]] = None):
        super().__init__(TalosErrorCode.TALOS_DENIED, message, details)

class TransportError(UCPError):
    def __init__(self, message: str, cause: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(TalosErrorCode.TALOS_TRANSPORT_ERROR, message, cause=cause, details=details)

class TimeoutError(UCPError):
    def __init__(self, message: str = "Request timed out", details: Optional[Dict[str, Any]] = None):
        super().__init__(TalosErrorCode.TALOS_TRANSPORT_TIMEOUT, message, details=details)

class InvalidInputError(UCPError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(TalosErrorCode.TALOS_INVALID_INPUT, message, details=details)

class CryptoError(UCPError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(TalosErrorCode.TALOS_CRYPTO_ERROR, message, details=details)
