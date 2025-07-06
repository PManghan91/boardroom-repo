"""
Health check API endpoints for service integration monitoring.
Provides comprehensive health status, readiness probes, and dependency monitoring.
"""

from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from app.core.health_checks import (
    health_service,
    HealthCheckResponse,
    DetailedHealthResponse,
    DependenciesResponse,
    HealthStatus
)
from app.core.logging import logger

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthCheckResponse, summary="Basic Health Check")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns overall service health status with minimal details.
    Fast response suitable for load balancer health checks.
    """
    try:
        # Quick health check without detailed analysis
        is_alive = await health_service.is_alive()
        
        if is_alive:
            return HealthCheckResponse(
                status=HealthStatus.HEALTHY,
                timestamp=datetime.utcnow().isoformat(),
                message="Service is healthy",
                details={"uptime_seconds": (datetime.utcnow() - health_service.startup_time).total_seconds()}
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=HealthCheckResponse(
                    status=HealthStatus.UNHEALTHY,
                    timestamp=datetime.utcnow().isoformat(),
                    message="Service is not alive",
                    details={}
                ).dict()
            )
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthCheckResponse(
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.utcnow().isoformat(),
                message="Health check failed",
                details={"error": str(e)}
            ).dict()
        )


@router.get("/ready", response_model=HealthCheckResponse, summary="Readiness Probe")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    
    Checks if service is ready to accept traffic.
    Validates critical dependencies (database, Redis) are available.
    """
    try:
        is_ready = await health_service.is_ready()
        
        if is_ready:
            return HealthCheckResponse(
                status=HealthStatus.HEALTHY,
                timestamp=datetime.utcnow().isoformat(),
                message="Service is ready",
                details={"ready": True}
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=HealthCheckResponse(
                    status=HealthStatus.UNHEALTHY,
                    timestamp=datetime.utcnow().isoformat(),
                    message="Service is not ready",
                    details={"ready": False}
                ).dict()
            )
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthCheckResponse(
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.utcnow().isoformat(),
                message="Readiness check failed",
                details={"error": str(e), "ready": False}
            ).dict()
        )


@router.get("/live", response_model=HealthCheckResponse, summary="Liveness Probe")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    
    Basic check to determine if the service is alive and should not be restarted.
    Minimal processing to avoid false positives during high load.
    """
    try:
        is_alive = await health_service.is_alive()
        
        if is_alive:
            return HealthCheckResponse(
                status=HealthStatus.HEALTHY,
                timestamp=datetime.utcnow().isoformat(),
                message="Service is alive",
                details={"alive": True}
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=HealthCheckResponse(
                    status=HealthStatus.UNHEALTHY,
                    timestamp=datetime.utcnow().isoformat(),
                    message="Service is not alive",
                    details={"alive": False}
                ).dict()
            )
    except Exception as e:
        logger.error("liveness_check_failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthCheckResponse(
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.utcnow().isoformat(),
                message="Liveness check failed",
                details={"error": str(e), "alive": False}
            ).dict()
        )


@router.get("/detailed", response_model=DetailedHealthResponse, summary="Detailed Health Status")
async def detailed_health_check():
    """
    Comprehensive health check with detailed service status.
    
    Provides detailed information about all services, circuit breakers,
    performance metrics, and system resources. Suitable for monitoring
    and administrative purposes.
    """
    try:
        health_data = await health_service.get_comprehensive_health()
        
        # Determine HTTP status code based on overall health
        http_status = status.HTTP_200_OK
        if health_data["status"] == HealthStatus.UNHEALTHY:
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_data["status"] == HealthStatus.DEGRADED:
            http_status = status.HTTP_200_OK  # Still serving traffic but degraded
        
        response = DetailedHealthResponse(**health_data)
        
        return JSONResponse(
            status_code=http_status,
            content=response.dict()
        )
        
    except Exception as e:
        logger.error("detailed_health_check_failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": HealthStatus.UNHEALTHY,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "message": "Detailed health check failed"
            }
        )


@router.get("/dependencies", response_model=DependenciesResponse, summary="Service Dependencies")
async def dependencies_status():
    """
    Service dependencies status endpoint.
    
    Provides information about service dependencies, their requirements,
    and current status including circuit breaker states.
    """
    try:
        dependencies = health_service.get_dependencies_status()
        
        return DependenciesResponse(
            dependencies=dependencies,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("dependencies_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dependencies check failed: {str(e)}"
        )


@router.get("/circuit-breakers", summary="Circuit Breaker Status")
async def circuit_breaker_status():
    """
    Circuit breaker status for all protected services.
    
    Provides detailed information about circuit breaker states,
    failure counts, and success rates for monitoring and debugging.
    """
    try:
        circuit_status = {}
        
        for name, cb in health_service.circuit_breakers.items():
            circuit_status[name] = {
                "is_open": cb.state.is_open,
                "failure_count": cb.state.failure_count,
                "total_requests": cb.state.total_requests,
                "total_failures": cb.state.total_failures,
                "success_rate": (
                    (cb.state.total_requests - cb.state.total_failures) / cb.state.total_requests
                    if cb.state.total_requests > 0 else 1.0
                ),
                "last_failure_time": cb.state.last_failure_time.isoformat() if cb.state.last_failure_time else None,
                "last_success_time": cb.state.last_success_time.isoformat() if cb.state.last_success_time else None,
                "configuration": {
                    "failure_threshold": cb.failure_threshold,
                    "recovery_timeout": cb.recovery_timeout,
                    "half_open_max_calls": cb.half_open_max_calls
                }
            }
        
        return {
            "circuit_breakers": circuit_status,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_breakers": len(circuit_status),
                "open_breakers": sum(1 for cb in circuit_status.values() if cb["is_open"]),
                "healthy_breakers": sum(1 for cb in circuit_status.values() if not cb["is_open"])
            }
        }
        
    except Exception as e:
        logger.error("circuit_breaker_status_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Circuit breaker status check failed: {str(e)}"
        )


@router.post("/reset-circuit-breaker/{service_name}", summary="Reset Circuit Breaker")
async def reset_circuit_breaker(service_name: str):
    """
    Reset circuit breaker for a specific service.
    
    Administrative endpoint to manually reset a circuit breaker,
    useful for recovery operations and testing.
    """
    try:
        if service_name not in health_service.circuit_breakers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Circuit breaker for service '{service_name}' not found"
            )
        
        cb = health_service.circuit_breakers[service_name]
        cb.state.is_open = False
        cb.state.failure_count = 0
        cb._half_open_calls = 0
        
        logger.info("circuit_breaker_manually_reset", 
                   service_name=service_name,
                   message=f"Circuit breaker for service '{service_name}' manually reset")
        
        return {
            "message": f"Circuit breaker for service '{service_name}' reset successfully",
            "service_name": service_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("circuit_breaker_reset_failed", 
                    service_name=service_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker: {str(e)}"
        )


@router.get("/metrics", summary="Health Check Metrics")
async def health_metrics():
    """
    Health check metrics for monitoring integration.
    
    Provides metrics in a format suitable for Prometheus/Grafana integration.
    """
    try:
        health_data = await health_service.get_comprehensive_health()
        
        # Format metrics for monitoring systems
        metrics = {
            "service_health_status": {
                service: 1 if data["status"] == HealthStatus.HEALTHY else 0
                for service, data in health_data["services"].items()
            },
            "service_response_time_ms": {
                service: data["response_time_ms"]
                for service, data in health_data["services"].items()
            },
            "circuit_breaker_open": {
                name: 1 if cb["is_open"] else 0
                for name, cb in health_data["circuit_breakers"].items()
            },
            "circuit_breaker_success_rate": {
                name: cb["success_rate"]
                for name, cb in health_data["circuit_breakers"].items()
            },
            "total_uptime_seconds": health_data["uptime_seconds"],
            "total_response_time_ms": health_data["total_response_time_ms"],
            "healthy_services_count": health_data["summary"]["healthy_services"],
            "degraded_services_count": health_data["summary"]["degraded_services"],
            "unhealthy_services_count": health_data["summary"]["unhealthy_services"]
        }
        
        return {
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "format": "prometheus_compatible"
        }
        
    except Exception as e:
        logger.error("health_metrics_generation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health metrics generation failed: {str(e)}"
        )