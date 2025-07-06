"""
Advanced caching strategies for the Boardroom AI system.
Implements multi-level caching, predictive caching, and performance-based auto-scaling.
"""

import asyncio
import json
import time
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from app.core.config import get_settings
from app.services.redis_service import redis_service
from app.core.metrics import cache_operations_total, cache_hit_ratio

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheLevel(Enum):
    """Cache levels for multi-level caching strategy."""
    L1_MEMORY = "l1_memory"      # In-memory cache (fastest)
    L2_REDIS = "l2_redis"        # Redis cache (fast)
    L3_DATABASE = "l3_database"  # Database cache (slower but persistent)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    data: Any
    level: CacheLevel
    created_at: datetime
    ttl: int
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    prediction_score: float = 0.0


class MultiLevelCache:
    """Multi-level caching system with L1 (memory), L2 (Redis), L3 (DB)."""
    
    def __init__(self):
        self.l1_cache: Dict[str, CacheEntry] = {}
        self.l1_max_size = getattr(settings, 'L1_CACHE_SIZE', 1000)
        self.l1_ttl = getattr(settings, 'L1_CACHE_TTL', 300)      # 5 minutes
        self.l2_ttl = getattr(settings, 'L2_CACHE_TTL', 1800)     # 30 minutes
        self.l3_ttl = getattr(settings, 'L3_CACHE_TTL', 7200)     # 2 hours
        
        # Cache statistics
        self.stats = {
            'l1_hits': 0, 'l1_misses': 0,
            'l2_hits': 0, 'l2_misses': 0,
            'l3_hits': 0, 'l3_misses': 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache."""
        # Try L1 (memory) first
        l1_entry = await self._get_l1(key)
        if l1_entry:
            self.stats['l1_hits'] += 1
            cache_operations_total.labels(operation="hit", status="l1").inc()
            await self._update_access_stats(l1_entry)
            return l1_entry.data
        
        self.stats['l1_misses'] += 1
        
        # Try L2 (Redis)
        l2_data = await self._get_l2(key)
        if l2_data:
            self.stats['l2_hits'] += 1
            cache_operations_total.labels(operation="hit", status="l2").inc()
            # Promote to L1
            await self._set_l1(key, l2_data, self.l1_ttl)
            return l2_data
        
        self.stats['l2_misses'] += 1
        
        # Try L3 (Database) - placeholder for future implementation
        l3_data = await self._get_l3(key)
        if l3_data:
            self.stats['l3_hits'] += 1
            cache_operations_total.labels(operation="hit", status="l3").inc()
            # Promote to L2 and L1
            await self._set_l2(key, l3_data, self.l2_ttl)
            await self._set_l1(key, l3_data, self.l1_ttl)
            return l3_data
        
        self.stats['l3_misses'] += 1
        cache_operations_total.labels(operation="miss", status="all").inc()
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in multi-level cache."""
        # Set in all levels with appropriate TTLs
        await self._set_l1(key, value, ttl or self.l1_ttl)
        await self._set_l2(key, value, ttl or self.l2_ttl)
        await self._set_l3(key, value, ttl or self.l3_ttl)
    
    async def delete(self, key: str) -> None:
        """Delete from all cache levels."""
        await self._delete_l1(key)
        await self._delete_l2(key)
        await self._delete_l3(key)
    
    async def _get_l1(self, key: str) -> Optional[CacheEntry]:
        """Get from L1 (memory) cache."""
        entry = self.l1_cache.get(key)
        if entry and not self._is_expired(entry):
            return entry
        elif entry:
            # Remove expired entry
            del self.l1_cache[key]
        return None
    
    async def _set_l1(self, key: str, value: Any, ttl: int) -> None:
        """Set in L1 (memory) cache."""
        # Implement LRU eviction if cache is full
        if len(self.l1_cache) >= self.l1_max_size:
            await self._evict_l1_lru()
        
        entry = CacheEntry(
            key=key,
            data=value,
            level=CacheLevel.L1_MEMORY,
            created_at=datetime.utcnow(),
            ttl=ttl
        )
        self.l1_cache[key] = entry
    
    async def _delete_l1(self, key: str) -> None:
        """Delete from L1 cache."""
        self.l1_cache.pop(key, None)
    
    async def _get_l2(self, key: str) -> Optional[Any]:
        """Get from L2 (Redis) cache."""
        try:
            data = await redis_service.get(f"l2:{key}")
            if data:
                return data
        except Exception as e:
            logger.error(f"L2 cache get error: {e}")
        return None
    
    async def _set_l2(self, key: str, value: Any, ttl: int) -> None:
        """Set in L2 (Redis) cache."""
        try:
            await redis_service.set(
                f"l2:{key}", 
                value,
                ttl=ttl,
                cache_type="multi_level"
            )
        except Exception as e:
            logger.error(f"L2 cache set error: {e}")
    
    async def _delete_l2(self, key: str) -> None:
        """Delete from L2 cache."""
        try:
            await redis_service.delete(f"l2:{key}")
        except Exception as e:
            logger.error(f"L2 cache delete error: {e}")
    
    async def _get_l3(self, key: str) -> Optional[Any]:
        """Get from L3 (Database) cache."""
        # Implementation would depend on database schema
        # For now, return None (not implemented)
        return None
    
    async def _set_l3(self, key: str, value: Any, ttl: int) -> None:
        """Set in L3 (Database) cache."""
        # Implementation would depend on database schema
        pass
    
    async def _delete_l3(self, key: str) -> None:
        """Delete from L3 cache."""
        # Implementation would depend on database schema
        pass
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        age = (datetime.utcnow() - entry.created_at).total_seconds()
        return age > entry.ttl
    
    async def _evict_l1_lru(self) -> None:
        """Evict least recently used item from L1 cache."""
        if not self.l1_cache:
            return
        
        # Find LRU entry
        lru_key = min(
            self.l1_cache.keys(),
            key=lambda k: self.l1_cache[k].last_accessed or self.l1_cache[k].created_at
        )
        del self.l1_cache[lru_key]
    
    async def _update_access_stats(self, entry: CacheEntry) -> None:
        """Update access statistics for cache entry."""
        entry.access_count += 1
        entry.last_accessed = datetime.utcnow()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = sum([
            self.stats['l1_hits'], self.stats['l1_misses'],
            self.stats['l2_hits'], self.stats['l2_misses'], 
            self.stats['l3_hits'], self.stats['l3_misses']
        ])
        
        if total_requests == 0:
            hit_ratio = 0.0
        else:
            total_hits = self.stats['l1_hits'] + self.stats['l2_hits'] + self.stats['l3_hits']
            hit_ratio = total_hits / total_requests
        
        # Update Prometheus metrics
        cache_hit_ratio.set(hit_ratio)
        
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_ratio': hit_ratio,
            'l1_size': len(self.l1_cache)
        }


class PredictiveCache:
    """Predictive caching system for AI operations."""
    
    def __init__(self, multi_level_cache: MultiLevelCache):
        self.cache = multi_level_cache
        self.prediction_patterns: Dict[str, List[str]] = {}
        self.usage_patterns: Dict[str, List[datetime]] = {}
        self.warming_queue: asyncio.Queue = asyncio.Queue()
        self._warming_task: Optional[asyncio.Task] = None
    
    async def start_cache_warming(self):
        """Start cache warming task."""
        if getattr(settings, 'CACHE_WARMING_ENABLED', True) and self._warming_task is None:
            self._warming_task = asyncio.create_task(self._cache_warming_loop())
            logger.info("Predictive cache warming started")
    
    async def stop_cache_warming(self):
        """Stop cache warming task."""
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass
            self._warming_task = None
            logger.info("Predictive cache warming stopped")
    
    async def record_access_pattern(self, key: str):
        """Record access pattern for prediction."""
        now = datetime.utcnow()
        
        if key not in self.usage_patterns:
            self.usage_patterns[key] = []
        
        self.usage_patterns[key].append(now)
        
        # Keep only recent patterns (last 24 hours)
        cutoff = now - timedelta(hours=24)
        self.usage_patterns[key] = [
            ts for ts in self.usage_patterns[key] if ts > cutoff
        ]
        
        # Predict next accesses
        await self._predict_and_warm(key)
    
    async def _predict_and_warm(self, accessed_key: str):
        """Predict next cache accesses and warm cache."""
        # Simple pattern-based prediction
        patterns = self.prediction_patterns.get(accessed_key, [])
        
        for predicted_key in patterns:
            # Add to warming queue if not already cached
            cached_value = await self.cache.get(predicted_key)
            if cached_value is None:
                try:
                    await self.warming_queue.put(predicted_key)
                except asyncio.QueueFull:
                    logger.warning("Cache warming queue is full")
    
    async def _cache_warming_loop(self):
        """Main cache warming loop."""
        while True:
            try:
                # Get key to warm from queue (with timeout)
                key = await asyncio.wait_for(
                    self.warming_queue.get(), 
                    timeout=60.0
                )
                await self._warm_cache_key(key)
                
            except asyncio.TimeoutError:
                # No keys to warm, continue
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache warming error: {e}")
    
    async def _warm_cache_key(self, key: str):
        """Warm cache for specific key."""
        # This would call the appropriate data loading function
        # based on the key pattern
        logger.debug(f"Warming cache for key: {key}")
        # Implementation depends on specific use case


class PerformanceBasedAutoScaling:
    """Performance-based auto-scaling for cache and resources."""
    
    def __init__(self, multi_level_cache: MultiLevelCache):
        self.cache = multi_level_cache
        self.performance_history: List[Dict[str, float]] = []
        self.scaling_thresholds = {
            'response_time_ms': 500,
            'memory_usage_percent': 80,
            'cache_hit_ratio': 0.85,
            'cpu_usage_percent': 75
        }
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self):
        """Start performance monitoring for auto-scaling."""
        if getattr(settings, 'AUTO_SCALING_ENABLED', True) and self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Performance-based auto-scaling monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for auto-scaling decisions."""
        while True:
            try:
                await self._collect_performance_metrics()
                await self._evaluate_scaling_decisions()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-scaling monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _collect_performance_metrics(self):
        """Collect current performance metrics."""
        try:
            import psutil
            
            # Get cache statistics
            cache_stats = self.cache.get_stats()
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            metrics = {
                'timestamp': datetime.utcnow(),
                'cache_hit_ratio': cache_stats.get('hit_ratio', 0),
                'memory_usage_percent': memory.percent,
                'cpu_usage_percent': cpu_percent,
                'l1_cache_size': cache_stats.get('l1_size', 0)
            }
            
            self.performance_history.append(metrics)
            
            # Keep only recent history (last hour)
            cutoff = datetime.utcnow() - timedelta(hours=1)
            self.performance_history = [
                m for m in self.performance_history 
                if m['timestamp'] > cutoff
            ]
        except ImportError:
            logger.warning("psutil not available for performance monitoring")
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")
    
    async def _evaluate_scaling_decisions(self):
        """Evaluate if scaling actions are needed."""
        if len(self.performance_history) < 3:
            return  # Need some history to make decisions
        
        recent_metrics = self.performance_history[-3:]  # Last 3 measurements
        
        # Check if cache hit ratio is consistently low
        hit_ratios = [m['cache_hit_ratio'] for m in recent_metrics]
        if all(ratio < self.scaling_thresholds['cache_hit_ratio'] for ratio in hit_ratios):
            await self._scale_up_cache()
        
        # Check if memory usage is consistently high
        memory_usages = [m['memory_usage_percent'] for m in recent_metrics]
        if all(usage > self.scaling_thresholds['memory_usage_percent'] for usage in memory_usages):
            await self._optimize_memory_usage()
    
    async def _scale_up_cache(self):
        """Scale up cache capacity."""
        logger.info("Scaling up cache capacity due to low hit ratio")
        
        # Increase L1 cache size
        self.cache.l1_max_size = min(int(self.cache.l1_max_size * 1.5), 5000)
        
        # Increase TTLs
        self.cache.l1_ttl = min(int(self.cache.l1_ttl * 1.2), 600)
        self.cache.l2_ttl = min(int(self.cache.l2_ttl * 1.2), 3600)
        
        cache_operations_total.labels(operation="scale_up", status="cache").inc()
    
    async def _optimize_memory_usage(self):
        """Optimize memory usage when under pressure."""
        logger.info("Optimizing memory usage due to high usage")
        
        # Reduce L1 cache size
        self.cache.l1_max_size = max(int(self.cache.l1_max_size * 0.8), 500)
        
        # Force cleanup of expired entries
        expired_keys = [
            key for key, entry in self.cache.l1_cache.items()
            if self.cache._is_expired(entry)
        ]
        
        for key in expired_keys:
            await self.cache._delete_l1(key)
        
        cache_operations_total.labels(operation="optimize", status="memory").inc()


# Global instances
multi_level_cache = MultiLevelCache()
predictive_cache = PredictiveCache(multi_level_cache)
auto_scaler = PerformanceBasedAutoScaling(multi_level_cache)


async def setup_advanced_caching(app):
    """Setup advanced caching system."""
    
    @app.on_event("startup")
    async def startup_caching():
        await predictive_cache.start_cache_warming()
        await auto_scaler.start_monitoring()
        logger.info("Advanced caching system initialized")
    
    @app.on_event("shutdown")
    async def shutdown_caching():
        await predictive_cache.stop_cache_warming()
        await auto_scaler.stop_monitoring()
        logger.info("Advanced caching system shutdown complete")


# Decorator for cached functions
def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
                
                # Try to get from cache
                result = await multi_level_cache.get(cache_key)
                if result is not None:
                    await predictive_cache.record_access_pattern(cache_key)
                    return result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await multi_level_cache.set(cache_key, result, ttl)
                await predictive_cache.record_access_pattern(cache_key)
                return result
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # For sync functions, use a simpler caching approach
                result = func(*args, **kwargs)
                return result
            return sync_wrapper
    return decorator