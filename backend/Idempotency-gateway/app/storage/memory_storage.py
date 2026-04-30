from typing import Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta

class MemoryStorage:
    """Simple in-memory storage for idempotency keys"""
    
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self.ttl_seconds = 86400  # 24 hours
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response for an idempotency key"""
        if key in self._storage:
            data = self._storage[key]
            # Check if expired
            if datetime.now() > data["expires_at"]:
                del self._storage[key]
                return None
            return data["response"]
        return None
    
    async def set(self, key: str, response: Dict[str, Any]) -> None:
        """Store response for an idempotency key"""
        self._storage[key] = {
            "response": response,
            "expires_at": datetime.now() + timedelta(seconds=self.ttl_seconds)
        }
    
    async def get_lock(self, key: str) -> asyncio.Lock:
        """Get a lock for concurrent request handling"""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]