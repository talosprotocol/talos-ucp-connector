from talos_ucp_connector.domain.errors import (
    TalosErrorCode,
    UCPError,
    PolicyDeniedError,
    TransportError,
    TimeoutError,
    InvalidInputError,
    CryptoError
)

def test_ucp_error_to_dict():
    err = UCPError(
        code=TalosErrorCode.TALOS_DENIED,
        message="Test message",
        details={"foo": "bar"},
        request_id="req-123",
        cause="original cause"
    )
    d = err.to_dict()
    assert d["code"] == "TALOS_DENIED"
    assert d["message"] == "Test message"
    assert d["details"] == {"foo": "bar"}
    assert d["request_id"] == "req-123"
    assert d["cause"] == "original cause"

def test_policy_denied_error():
    err = PolicyDeniedError()
    assert err.code == TalosErrorCode.TALOS_DENIED
    assert "UCP_POLICY_DENIED" in err.message

def test_transport_error():
    err = TransportError("Failed to connect", cause="connection refused")
    assert err.code == TalosErrorCode.TALOS_TRANSPORT_ERROR
    assert err.cause == "connection refused"

def test_timeout_error():
    err = TimeoutError()
    assert err.code == TalosErrorCode.TALOS_TRANSPORT_TIMEOUT

def test_invalid_input_error():
    err = InvalidInputError("Bad JSON")
    assert err.code == TalosErrorCode.TALOS_INVALID_INPUT

def test_crypto_error():
    err = CryptoError("Invalid signature")
    assert err.code == TalosErrorCode.TALOS_CRYPTO_ERROR
