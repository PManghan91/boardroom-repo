"""
Graceful shutdown manager for production readiness.
Handles service lifecycle, cleanup procedures, and health state transitions.
"""

import asyncio
import signal
import sys
from typing import List, Callable, Awaitable, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from app.core.logging import logger
from app.core.health_checks import health_service, HealthStatus


class ShutdownManager:
    """
    Manages graceful shutdown procedures and service lifecycle.
    
    Provides coordinated shutdown with cleanup handlers,
    health state management, and timeout controls.
    """
    
    def __init__(self, shutdown_timeout: int = 30):
        self.shutdown_timeout = shutdown_timeout
        self.shutdown_handlers: List[Callable[[], Awaitable[None]]] = []
        self.is_shutting_down = False
        self.shutdown_start_time: Optional[datetime] = None
        self._shutdown_event = asyncio.Event()
        
    def register_shutdown_handler(self, handler: Callable[[], Awaitable[None]]):
        """Register a shutdown handler to be called during graceful shutdown."""
        self.shutdown_handlers.append(handler)
        logger.info("shutdown_handler_registered", handler_name=handler.__name__)
    
    async def _signal_handler(self, signum: int, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info("shutdown_signal_received", 
                   signal=signal_name,
                   message=f"Received {signal_name} signal, initiating graceful shutdown")
        await self.initiate_shutdown()
    
    async def initiate_shutdown(self):
        """Initiate graceful shutdown sequence."""
        if self.is_shutting_down:
            logger.warning("shutdown_already_in_progress")
            return
        
        self.is_shutting_down = True
        self.shutdown_start_time = datetime.utcnow()
        
        logger.info("graceful_shutdown_started")
        
        try:
            # Update health status to indicate shutdown
            health_service._shutting_down = True
            
            # Execute shutdown handlers with timeout
            await asyncio.wait_for(
                self._execute_shutdown_handlers(),
                timeout=self.shutdown_timeout
            )
            
            logger.info("graceful_shutdown_completed")
            
        except asyncio.TimeoutError:
            logger.error("shutdown_timeout_exceeded", 
                        timeout=self.shutdown_timeout,
                        message=f"Shutdown timeout exceeded ({self.shutdown_timeout}s), forcing shutdown")
        except Exception as e:
            logger.error("shutdown_error", error=str(e))
        finally:
            self._shutdown_event.set()
    
    async def _execute_shutdown_handlers(self):
        """Execute all registered shutdown handlers."""
        for handler in self.shutdown_handlers:
            try:
                logger.info("executing_shutdown_handler", handler_name=handler.__name__)
                await handler()
                logger.info("shutdown_handler_completed", handler_name=handler.__name__)
            except Exception as e:
                logger.error("shutdown_handler_failed", 
                           handler_name=handler.__name__,
                           error=str(e))
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        if sys.platform != "win32":
            # Unix-like systems
            signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(self._signal_handler(s, f)))
            signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self._signal_handler(s, f)))
            logger.info("signal_handlers_registered", signals=["SIGTERM", "SIGINT"])
        else:
            # Windows
            signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self._signal_handler(s, f)))
            logger.info("signal_handlers_registered", signals=["SIGINT"])
    
    @asynccontextmanager
    async def lifecycle_manager(self):
        """Context manager for application lifecycle."""
        try:
            logger.info("application_startup_initiated")
            self.setup_signal_handlers()
            
            # Startup validation
            await self._validate_startup()
            
            logger.info("application_startup_completed")
            yield
            
        except Exception as e:
            logger.error("application_startup_failed", error=str(e))
            raise
        finally:
            if not self.is_shutting_down:
                await self.initiate_shutdown()
    
    async def _validate_startup(self):
        """Validate service startup requirements."""
        logger.info("validating_startup_requirements")
        
        # Check if service is ready
        max_retries = 10
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                is_ready = await health_service.is_ready()
                if is_ready:
                    logger.info("startup_validation_passed")
                    return
                
                logger.warning("startup_validation_retry", 
                             attempt=attempt + 1,
                             max_retries=max_retries,
                             retry_delay=retry_delay,
                             message=f"Startup validation attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s")
                await asyncio.sleep(retry_delay)
                
            except Exception as e:
                logger.error("startup_validation_error", error=str(e))
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay)
        
        raise Exception("Startup validation failed after maximum retries")


# Global instances
shutdown_manager = ShutdownManager()


# Default shutdown handlers
async def cleanup_database_connections():
    """Cleanup database connections during shutdown."""
    try:
        logger.info("cleaning_up_database_connections")
        # Database cleanup logic would go here
        from app.services.database import database_service
        # Add any necessary database cleanup
        await asyncio.sleep(0.1)  # Simulate cleanup time
        logger.info("database_connections_cleaned_up")
    except Exception as e:
        logger.error("database_cleanup_failed", error=str(e))


async def cleanup_redis_connections():
    """Cleanup Redis connections during shutdown."""
    try:
        logger.info("cleaning_up_redis_connections")
        from app.services.redis_service import redis_service
        await redis_service.close()
        logger.info("redis_connections_cleaned_up")
    except Exception as e:
        logger.error("redis_cleanup_failed", error=str(e))


async def flush_metrics_and_logs():
    """Flush metrics and logs during shutdown."""
    try:
        logger.info("flushing_metrics_and_logs")
        # Metrics and logs flush logic would go here
        await asyncio.sleep(0.1)  # Simulate flush time
        logger.info("metrics_and_logs_flushed")
    except Exception as e:
        logger.error("metrics_logs_flush_failed", error=str(e))


# Register default shutdown handlers
shutdown_manager.register_shutdown_handler(cleanup_database_connections)
shutdown_manager.register_shutdown_handler(cleanup_redis_connections)
shutdown_manager.register_shutdown_handler(flush_metrics_and_logs)