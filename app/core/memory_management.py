"""
Memory management and resource optimization for the Boardroom AI system.
Implements memory monitoring, garbage collection optimization, and resource cleanup.
"""

import gc
import psutil
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import get_settings
from app.core.metrics import cache_memory_usage_bytes

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryMonitor:
    """Monitor and track memory usage across the application."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.memory_threshold = getattr(settings, 'MEMORY_THRESHOLD_MB', 512) * 1024 * 1024  # Convert to bytes
        self.monitoring_interval = 30  # seconds
        self.memory_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self):
        """Start continuous memory monitoring."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitor_loop())
            logger.info("Memory monitoring started")
    
    async def stop_monitoring(self):
        """Stop memory monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Memory monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                await self._collect_memory_stats()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _collect_memory_stats(self):
        """Collect current memory statistics."""
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            stats = {
                'timestamp': datetime.utcnow(),
                'rss': memory_info.rss,  # Resident Set Size
                'vms': memory_info.vms,  # Virtual Memory Size
                'percent': memory_percent,
                'available': psutil.virtual_memory().available,
                'gc_counts': gc.get_count()
            }
            
            # Add to history
            self.memory_history.append(stats)
            if len(self.memory_history) > self.max_history_size:
                self.memory_history.pop(0)
            
            # Update Prometheus metrics
            cache_memory_usage_bytes.set(memory_info.rss)
            
            # Check for memory pressure
            if memory_info.rss > self.memory_threshold:
                await self._handle_memory_pressure(stats)
            
            logger.debug(f"Memory stats: RSS={memory_info.rss/1024/1024:.1f}MB, Percent={memory_percent:.1f}%")
            
        except Exception as e:
            logger.error(f"Error collecting memory stats: {e}")
    
    async def _handle_memory_pressure(self, stats: Dict[str, Any]):
        """Handle high memory usage situations."""
        logger.warning(f"Memory pressure detected: {stats['percent']:.1f}% usage")
        
        # Trigger garbage collection
        collected = gc.collect()
        logger.info(f"Forced garbage collection freed {collected} objects")
        
        # Clear caches if available
        await self._clear_application_caches()
        
        # Record memory pressure event (if metrics available)
        try:
            from app.core.metrics import cache_operations_total
            cache_operations_total.labels(operation="memory_pressure", status="triggered").inc()
        except ImportError:
            pass
    
    async def _clear_application_caches(self):
        """Clear application-level caches to free memory."""
        try:
            # Clear Redis cache if needed
            from app.services.redis_service import redis_service
            if hasattr(redis_service, 'clear_memory_cache'):
                await redis_service.clear_memory_cache()
            
            # Clear AI state manager caches
            try:
                from app.services.ai_state_manager import ai_state_manager
                if hasattr(ai_state_manager, 'clear_cache'):
                    await ai_state_manager.clear_cache()
            except ImportError:
                pass
                
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics."""
        try:
            memory_info = self.process.memory_info()
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': self.process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / 1024 / 1024,
                'gc_counts': gc.get_count()
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {}


class ResourceManager:
    """Manage application resources and cleanup."""
    
    def __init__(self):
        self.cleanup_handlers: List[Callable] = []
        self.periodic_cleanup_interval = 300  # 5 minutes
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def register_cleanup_handler(self, handler: Callable):
        """Register a cleanup handler."""
        self.cleanup_handlers.append(handler)
    
    async def start_periodic_cleanup(self):
        """Start periodic resource cleanup."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Periodic resource cleanup started")
    
    async def stop_periodic_cleanup(self):
        """Stop periodic cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Periodic resource cleanup stopped")
    
    async def _cleanup_loop(self):
        """Main cleanup loop."""
        while True:
            try:
                await self.cleanup_resources()
                await asyncio.sleep(self.periodic_cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")
                await asyncio.sleep(self.periodic_cleanup_interval)
    
    async def cleanup_resources(self):
        """Run all registered cleanup handlers."""
        logger.debug("Running resource cleanup")
        
        for handler in self.cleanup_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Cleanup handler error: {e}")
        
        # Force garbage collection after cleanup
        collected = gc.collect()
        logger.debug(f"Cleanup garbage collection freed {collected} objects")


class AIMemoryOptimizer:
    """Optimize memory usage for AI operations."""
    
    def __init__(self):
        self.model_cache_size = getattr(settings, 'MODEL_CACHE_SIZE', 3)
        self.conversation_history_limit = getattr(settings, 'MAX_CONVERSATION_HISTORY', 50)
        self.state_cache_ttl = 1800  # 30 minutes
    
    @asynccontextmanager
    async def optimized_ai_context(self):
        """Context manager for optimized AI operations."""
        # Pre-operation cleanup
        await self._pre_operation_cleanup()
        
        try:
            yield
        finally:
            # Post-operation cleanup
            await self._post_operation_cleanup()
    
    async def _pre_operation_cleanup(self):
        """Cleanup before AI operations."""
        # Clear old conversation states
        await self._cleanup_conversation_states()
        
        # Optimize model cache
        await self._optimize_model_cache()
    
    async def _post_operation_cleanup(self):
        """Cleanup after AI operations."""
        # Force garbage collection for AI objects
        gc.collect()
        
        # Clear temporary AI data
        await self._clear_temporary_ai_data()
    
    async def _cleanup_conversation_states(self):
        """Clean up old conversation states."""
        try:
            from app.services.ai_state_manager import ai_state_manager
            if hasattr(ai_state_manager, 'cleanup_old_states'):
                await ai_state_manager.cleanup_old_states(max_age_minutes=30)
        except ImportError:
            logger.debug("AI state manager not available for cleanup")
        except Exception as e:
            logger.error(f"Error cleaning conversation states: {e}")
    
    async def _optimize_model_cache(self):
        """Optimize AI model cache."""
        # Implementation depends on specific AI framework used
        # This is a placeholder for future AI model cache optimization
        pass
    
    async def _clear_temporary_ai_data(self):
        """Clear temporary AI operation data."""
        # Clear any temporary files or data structures
        # This is a placeholder for future temporary data cleanup
        pass


# Global instances
memory_monitor = MemoryMonitor()
resource_manager = ResourceManager()
ai_memory_optimizer = AIMemoryOptimizer()


async def setup_memory_management(app: FastAPI):
    """Setup memory management for the application."""
    
    # Register cleanup handlers
    resource_manager.register_cleanup_handler(lambda: gc.collect())
    
    # Add startup event
    @app.on_event("startup")
    async def startup_memory_management():
        await memory_monitor.start_monitoring()
        await resource_manager.start_periodic_cleanup()
        logger.info("Memory management initialized")
    
    # Add shutdown event
    @app.on_event("shutdown")
    async def shutdown_memory_management():
        await memory_monitor.stop_monitoring()
        await resource_manager.stop_periodic_cleanup()
        await resource_manager.cleanup_resources()
        logger.info("Memory management shutdown complete")


# Decorator for memory-optimized functions
def memory_optimized(func):
    """Decorator to optimize memory usage for functions."""
    if asyncio.iscoroutinefunction(func):
        async def async_wrapper(*args, **kwargs):
            async with ai_memory_optimizer.optimized_ai_context():
                return await func(*args, **kwargs)
        return async_wrapper
    else:
        def sync_wrapper(*args, **kwargs):
            # Pre-execution cleanup
            gc.collect()
            try:
                return func(*args, **kwargs)
            finally:
                # Post-execution cleanup
                gc.collect()
        return sync_wrapper