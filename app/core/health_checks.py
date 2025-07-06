"""
Comprehensive health check system for service integration monitoring.
Provides detailed status reporting, circuit breakers, and production readiness validation.
"""

import asyncio
import time
import traceback
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger
from app.services.redis_service import redis_service


class HealthStatus(str, Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(str, Enum):
    """Types of services for health monitoring."""
    DATABASE = "database"
    REDIS = "redis"
    EXTERNAL_API = "external_api"
    INTERNAL_SERVICE = "internal_service"
    FILESYSTEM = "filesystem"
    NETWORK = "network"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    service_name: str
    service_type: ServiceType
    status: HealthStatus
    response_time_ms: float
    timestamp: datetime
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking."""
    is_open: bool = False
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_requests: int = 0
    total_failures: int = 0


class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.state = CircuitBreakerState()
        self._half_open_calls = 0
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed through circuit breaker."""
        now = datetime.utcnow()
        
        if not self.state.is_open:
            return True
        
        # Check if recovery timeout has passed
        if (self.state.last_failure_time and 
            now - self.state.last_failure_time > timedelta(seconds=self.recovery_timeout)):
            # Move to half-open state
            self._half_open_calls = 0
            return True
        
        return False
    
    def _record_success(self):
        """Record successful request."""
        self.state.total_requests += 1
        self.state.last_success_time = datetime.utcnow()
        
        if self.state.is_open:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                # Close circuit breaker
                self.state.is_open = False
                self.state.failure_count = 0
                logger.info("circuit_breaker_closed", message="Circuit breaker closed after successful recovery")
    
    def _record_failure(self):
        """Record failed request."""
        self.state.total_requests += 1
        self.state.total_failures += 1
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.utcnow()
        
        if self.state.failure_count >= self.failure_threshold:
            self.state.is_open = True
            logger.warning("circuit_breaker_opened", 
                         failure_count=self.state.failure_count,
                         message=f"Circuit breaker opened after {self.state.failure_count} failures")
    
    @asynccontextmanager
    async def call(self):
        """Context manager for circuit breaker protected calls."""
        if not self._should_allow_request():
            raise Exception("Circuit breaker is open")
        
        try:
            yield
            self._record_success()
        except Exception as e:
            self._record_failure()
            raise e


class RetryManager:
    """Retry mechanism with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    async def execute(
        self, 
        func: Callable[[], Awaitable[Any]], 
        exceptions: tuple = (Exception,)
    ) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func()
            except exceptions as e:
                last_exception = e
                if attempt == self.max_retries:
                    break
                
                delay = min(
                    self.base_delay * (self.backoff_factor ** attempt),
                    self.max_delay
                )
                
                logger.warning(
                    "retry_attempt",
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(e),
                    message=f"Attempt {attempt + 1} failed, retrying in {delay}s"
                )
                await asyncio.sleep(delay)
        
        raise last_exception


class HealthCheckService:
    """Comprehensive health check service with monitoring and circuit breakers."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_manager = RetryManager()
        self.startup_time = datetime.utcnow()
        self.last_health_check = {}
        self._check_cache: Dict[str, HealthCheckResult] = {}
        self._cache_ttl = 30  # seconds
        self._shutting_down = False
    
    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]
    
    async def _timed_check(
        self, 
        check_func: Callable[[], Awaitable[HealthCheckResult]]
    ) -> HealthCheckResult:
        """Execute health check with timing."""
        start_time = time.time()
        try:
            result = await check_func()
            result.response_time_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error("health_check_execution_failed", error=str(e))
            return HealthCheckResult(
                service_name="unknown",
                service_type=ServiceType.INTERNAL_SERVICE,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                timestamp=datetime.utcnow(),
                error=str(e),
                message="Health check execution failed"
            )
    
    def _is_cache_valid(self, service_name: str) -> bool:
        """Check if cached result is still valid."""
        if service_name not in self._check_cache:
            return False
        
        result = self._check_cache[service_name]
        age = (datetime.utcnow() - result.timestamp).total_seconds()
        return age < self._cache_ttl
    
    async def check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance."""
        service_name = "postgresql"
        
        if self._is_cache_valid(service_name):
            return self._check_cache[service_name]
        
        circuit_breaker = self._get_circuit_breaker(service_name)
        
        async def _check():
            async with circuit_breaker.call():
                from app.services.database import database_service
                
                # Test basic connectivity
                db_healthy = await database_service.health_check()
                
                if not db_healthy:
                    raise Exception("Database health check failed")
                
                details = {
                    "connectivity": "healthy",
                    "service": "postgresql"
                }
                
                return HealthCheckResult(
                    service_name=service_name,
                    service_type=ServiceType.DATABASE,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=0,  # Will be set by _timed_check
                    timestamp=datetime.utcnow(),
                    message="Database connection healthy",
                    details=details
                )
        
        try:
            result = await self._timed_check(_check)
            self._check_cache[service_name] = result
            return result
        except Exception as e:
            result = HealthCheckResult(
                service_name=service_name,
                service_type=ServiceType.DATABASE,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                timestamp=datetime.utcnow(),
                error=str(e),
                message="Database connection failed"
            )
            self._check_cache[service_name] = result
            return result
    
    async def check_redis_health(self) -> HealthCheckResult:
        """Check Redis connectivity and performance."""
        service_name = "redis"
        
        if self._is_cache_valid(service_name):
            return self._check_cache[service_name]
        
        circuit_breaker = self._get_circuit_breaker(service_name)
        
        async def _check():
            async with circuit_breaker.call():
                # Get Redis health check
                health_data = await redis_service.health_check()
                
                if health_data["status"] != "healthy":
                    raise Exception(f"Redis health check failed: {health_data}")
                
                details = {
                    "status": health_data["status"],
                    "connection_pool_created": health_data.get("connection_pool_created", False),
                    "stats": health_data.get("stats", {})
                }
                
                return HealthCheckResult(
                    service_name=service_name,
                    service_type=ServiceType.REDIS,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=0,
                    timestamp=datetime.utcnow(),
                    message="Redis connection healthy",
                    details=details
                )
        
        try:
            result = await self._timed_check(_check)
            self._check_cache[service_name] = result
            return result
        except Exception as e:
            result = HealthCheckResult(
                service_name=service_name,
                service_type=ServiceType.REDIS,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                timestamp=datetime.utcnow(),
                error=str(e),
                message="Redis connection failed"
            )
            self._check_cache[service_name] = result
            return result
    
    async def check_system_resources(self) -> HealthCheckResult:
        """Check system resource health."""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil_not_available", 
                         message="psutil not available, skipping system resource check")
            return HealthCheckResult(
                service_name="system_resources",
                service_type=ServiceType.INTERNAL_SERVICE,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                timestamp=datetime.utcnow(),
                message="psutil not available for system monitoring"
            )
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": round((disk.used / disk.total) * 100, 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds()
            }
            
            # Determine status based on thresholds
            status = HealthStatus.HEALTHY
            if cpu_percent > 90 or memory.percent > 90 or disk.used / disk.total > 0.95:
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 75 or memory.percent > 75 or disk.used / disk.total > 0.85:
                status = HealthStatus.DEGRADED
            
            return HealthCheckResult(
                service_name="system_resources",
                service_type=ServiceType.INTERNAL_SERVICE,
                status=status,
                response_time_ms=0,
                timestamp=datetime.utcnow(),
                message=f"System resources {status.value}",
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name="system_resources",
                service_type=ServiceType.INTERNAL_SERVICE,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                timestamp=datetime.utcnow(),
                error=str(e),
                message="System resource check failed"
            )
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status for all services."""
        checks = await asyncio.gather(
            self.check_database_health(),
            self.check_redis_health(),
            self.check_system_resources(),
            return_exceptions=True
        )
        
        # Process results
        results = {}
        overall_status = HealthStatus.HEALTHY
        total_response_time = 0
        
        for check in checks:
            if isinstance(check, Exception):
                logger.error("health_check_exception", error=str(check))
                overall_status = HealthStatus.UNHEALTHY
                continue
            
            results[check.service_name] = {
                "status": check.status,
                "response_time_ms": check.response_time_ms,
                "timestamp": check.timestamp.isoformat(),
                "message": check.message,
                "details": check.details,
                "error": check.error
            }
            
            total_response_time += check.response_time_ms
            
            # Update overall status
            if check.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        # Circuit breaker status
        circuit_status = {}
        for name, cb in self.circuit_breakers.items():
            circuit_status[name] = {
                "is_open": cb.state.is_open,
                "failure_count": cb.state.failure_count,
                "total_requests": cb.state.total_requests,
                "total_failures": cb.state.total_failures,
                "success_rate": (
                    (cb.state.total_requests - cb.state.total_failures) / cb.state.total_requests
                    if cb.state.total_requests > 0 else 1.0
                )
            }
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "total_response_time_ms": total_response_time,
            "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
            "services": results,
            "circuit_breakers": circuit_status,
            "summary": {
                "total_services": len(results),
                "healthy_services": sum(1 for r in results.values() if r["status"] == HealthStatus.HEALTHY),
                "degraded_services": sum(1 for r in results.values() if r["status"] == HealthStatus.DEGRADED),
                "unhealthy_services": sum(1 for r in results.values() if r["status"] == HealthStatus.UNHEALTHY)
            }
        }
    
    async def is_ready(self) -> bool:
        """Check if service is ready to accept traffic."""
        if self._shutting_down:
            return False
            
        db_check = await self.check_database_health()
        redis_check = await self.check_redis_health()
        
        return (db_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED] and
                redis_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED])
    
    async def is_alive(self) -> bool:
        """Basic liveness check."""
        try:
            # Simple checks that service is running
            return not self._shutting_down and (datetime.utcnow() - self.startup_time).total_seconds() > 0
        except Exception:
            return False
    
    def get_dependencies_status(self) -> Dict[str, Any]:
        """Get status of service dependencies."""
        dependencies = {
            "database": {
                "required": True,
                "description": "PostgreSQL database for persistent storage"
            },
            "redis": {
                "required": True,
                "description": "Redis for caching and session management"
            },
            "external_apis": {
                "required": False,
                "description": "External APIs for enhanced functionality"
            }
        }
        
        # Add circuit breaker status for each dependency
        for dep_name in dependencies:
            if dep_name in self.circuit_breakers:
                cb = self.circuit_breakers[dep_name]
                dependencies[dep_name]["circuit_breaker"] = {
                    "is_open": cb.state.is_open,
                    "failure_count": cb.state.failure_count,
                    "last_failure": cb.state.last_failure_time.isoformat() if cb.state.last_failure_time else None
                }
        
        return dependencies


# Global health check service instance
health_service = HealthCheckService()


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: HealthStatus
    timestamp: str
    message: str = ""
    details: Dict[str, Any] = {}


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: HealthStatus
    timestamp: str
    total_response_time_ms: float
    uptime_seconds: float
    services: Dict[str, Any]
    circuit_breakers: Dict[str, Any]
    summary: Dict[str, Any]


class DependenciesResponse(BaseModel):
    """Dependencies status response model."""
    dependencies: Dict[str, Any]
    timestamp: str