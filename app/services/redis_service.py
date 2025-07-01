"""Redis service for caching and session management.

This module provides a comprehensive Redis service implementation with connection pooling,
health monitoring, cache statistics tracking, and graceful fallback capabilities.
"""

import json
import pickle
import hashlib
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from collections import deque
import asyncio

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ExternalServiceException


class CacheStats:
    """Cache statistics tracking."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.start_time = time.time()
        
    def hit(self):
        self.hits += 1
        
    def miss(self):
        self.misses += 1
        
    def set(self):
        self.sets += 1
        
    def delete(self):
        self.deletes += 1
        
    def error(self):
        self.errors += 1
        
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
        
    @property
    def total_operations(self) -> int:
        """Total cache operations."""
        return self.hits + self.misses + self.sets + self.deletes
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        uptime = time.time() - self.start_time
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate": self.hit_rate,
            "total_operations": self.total_operations,
            "uptime_seconds": uptime
        }


class RedisService:
    """Comprehensive Redis service with connection pooling and health monitoring."""
    
    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[Redis] = None
        self.stats = CacheStats()
        self.health_status = "unknown"
        self.last_health_check = 0
        self.connection_errors = deque(maxlen=100)  # Track recent errors
        
        # TTL defaults for different data types
        self.default_ttl = {
            "database_queries": 300,      # 5 minutes
            "ai_operations": 1800,        # 30 minutes
            "auth_tokens": 3600,          # 1 hour
            "api_responses": 600,         # 10 minutes
            "user_sessions": 7200,        # 2 hours
            "conversation_state": 3600,   # 1 hour
        }
        
    async def initialize(self) -> bool:
        """Initialize Redis connection pool."""
        try:
            # Create connection pool
            self.pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=getattr(settings, 'REDIS_MAX_CONNECTIONS', 10),
                socket_timeout=getattr(settings, 'REDIS_SOCKET_TIMEOUT', 5),
                socket_connect_timeout=getattr(settings, 'REDIS_SOCKET_CONNECT_TIMEOUT', 5),
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            self.client = Redis(connection_pool=self.pool)
            
            # Test connection
            await self.client.ping()
            self.health_status = "healthy"
            
            logger.info("redis_service_initialized", 
                       url=settings.REDIS_URL,
                       max_connections=getattr(settings, 'REDIS_MAX_CONNECTIONS', 10))
            return True
            
        except Exception as e:
            self.health_status = "unhealthy"
            self.connection_errors.append({
                "timestamp": time.time(),
                "error": str(e)
            })
            logger.error("redis_initialization_failed", error=str(e), exc_info=True)
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check."""
        now = time.time()
        
        # Only check every 30 seconds to avoid overhead
        if now - self.last_health_check < 30:
            return {
                "status": self.health_status,
                "last_check": self.last_health_check,
                "cached_result": True
            }
        
        try:
            if not self.client:
                await self.initialize()
            
            if self.client:
                # Test basic operations
                test_key = "health_check_test"
                await self.client.set(test_key, "test", ex=10)
                result = await self.client.get(test_key)
                await self.client.delete(test_key)
                
                if result == b"test":
                    self.health_status = "healthy"
                else:
                    self.health_status = "degraded"
            else:
                self.health_status = "unhealthy"
                
        except Exception as e:
            self.health_status = "unhealthy"
            self.connection_errors.append({
                "timestamp": time.time(),
                "error": str(e)
            })
            logger.error("redis_health_check_failed", error=str(e))
        
        self.last_health_check = now
        
        return {
            "status": self.health_status,
            "last_check": self.last_health_check,
            "connection_pool_created": self.pool is not None,
            "recent_errors": list(self.connection_errors)[-5:],  # Last 5 errors
            "stats": self.stats.to_dict()
        }
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage with performance optimization."""
        try:
            # Try JSON first for simple types (faster, human-readable)
            if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            pass
        
        # Fall back to pickle for complex objects
        try:
            return pickle.dumps(value)
        except Exception as e:
            logger.error("serialization_failed", error=str(e), value_type=type(value))
            raise ExternalServiceException(f"Failed to serialize value: {e}")
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from Redis with automatic format detection."""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        
        # Fall back to pickle
        try:
            return pickle.loads(data)
        except Exception as e:
            logger.error("deserialization_failed", error=str(e))
            raise ExternalServiceException(f"Failed to deserialize value: {e}")
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key from prefix and arguments."""
        # Create a string representation of all arguments
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        
        # Create hash for long keys to avoid Redis key length limits
        key_string = ":".join(key_parts)
        if len(key_string) > 200:  # Redis recommended max key length
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:hash:{key_hash}"
        
        return key_string
    
    async def get(self, key: str) -> Any:
        """Get value from cache."""
        if not self.client or self.health_status == "unhealthy":
            self.stats.miss()
            return None
        
        try:
            data = await self.client.get(key)
            if data is None:
                self.stats.miss()
                return None
            
            self.stats.hit()
            return self._deserialize_value(data)
            
        except Exception as e:
            self.stats.error()
            logger.error("redis_get_failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, 
                  cache_type: str = "default") -> bool:
        """Set value in cache with TTL."""
        if not self.client or self.health_status == "unhealthy":
            return False
        
        try:
            # Use cache-type specific TTL if not provided
            if ttl is None:
                ttl = self.default_ttl.get(cache_type, 300)
            
            data = self._serialize_value(value)
            await self.client.set(key, data, ex=ttl)
            self.stats.set()
            return True
            
        except Exception as e:
            self.stats.error()
            logger.error("redis_set_failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.client or self.health_status == "unhealthy":
            return False
        
        try:
            result = await self.client.delete(key)
            self.stats.delete()
            return result > 0
            
        except Exception as e:
            self.stats.error()
            logger.error("redis_delete_failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.client or self.health_status == "unhealthy":
            return False
        
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error("redis_exists_failed", key=key, error=str(e))
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        if not self.client or self.health_status == "unhealthy":
            return 0
        
        try:
            keys = await self.client.keys(pattern)
            if keys:
                deleted = await self.client.delete(*keys)
                self.stats.deletes += deleted
                return deleted
            return 0
            
        except Exception as e:
            self.stats.error()
            logger.error("redis_invalidate_pattern_failed", pattern=pattern, error=str(e))
            return 0
    
    async def get_ttl(self, key: str) -> int:
        """Get TTL for key (-1 if no expiry, -2 if key doesn't exist)."""
        if not self.client:
            return -2
        
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error("redis_ttl_failed", key=key, error=str(e))
            return -2
    
    # Cache decorator methods
    def cache_result(self, cache_type: str = "default", ttl: Optional[int] = None):
        """Decorator to cache function results."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                cache_key = self._generate_cache_key(
                    f"func:{func.__name__}", *args, **kwargs
                )
                
                # Try to get from cache first
                cached = await self.get(cache_key)
                if cached is not None:
                    return cached
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl, cache_type)
                return result
            
            return wrapper
        return decorator
    
    async def close(self):
        """Close Redis connections."""
        try:
            if self.client:
                await self.client.close()
            if self.pool:
                await self.pool.disconnect()
            logger.info("redis_service_closed")
        except Exception as e:
            logger.error("redis_close_failed", error=str(e))


# Global Redis service instance
redis_service = RedisService()


async def get_redis_service() -> RedisService:
    """Get Redis service instance, initializing if needed."""
    if not redis_service.client:
        await redis_service.initialize()
    return redis_service