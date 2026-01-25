import time
from typing import Dict, Set
from ...ports.spi import ClockPort, ReplayStorePort

class SystemClock(ClockPort):
    def now(self) -> int:
        return int(time.time())

class InMemoryReplayStore(ReplayStorePort):
    def __init__(self, ttl_seconds: int = 600):
        # Maps (merchant_id, kid, jti) -> expiry_time
        self.nonces: Dict[tuple, float] = {}
        self.ttl = ttl_seconds

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self.nonces.items() if v < now]
        for k in expired:
            del self.nonces[k]

    def check_and_store_nonce(self, merchant_id: str, kid: str, jti: str) -> bool:
        self._cleanup()
        key = (merchant_id, kid, jti)
        if key in self.nonces:
            return False
        
        self.nonces[key] = time.time() + self.ttl
        return True
