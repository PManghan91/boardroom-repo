"""
Monitoring API endpoints for collecting and retrieving application metrics.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from pydantic import BaseModel, Field
import psutil

from app.core.logging import logger
from app.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    ai_operations_total,
    cache_operations_total
)
from app.services.monitoring_service import monitoring_service
from app.core.health_checks import health_service

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# Request/Response Models
class AlertRequest(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime
    session_id: str
    user_id: Optional[str] = None


class ErrorRequest(BaseModel):
    type: str
    message: str
    stack: Optional[str] = None
    url: str
    line: int
    column: int
    timestamp: datetime
    session_id: str
    user_id: Optional[str] = None
    user_agent: str
    path: str


class BusinessMetricRequest(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime
    session_id: str
    user_id: Optional[str] = None


class PerformanceMetricsBatch(BaseModel):
    session_id: str
    metrics: List[Dict[str, Any]]


class ErrorsBatch(BaseModel):
    session_id: str
    errors: List[ErrorRequest]


class EngagementBatch(BaseModel):
    session_id: str
    metrics: List[Dict[str, Any]]


class BusinessMetricsBatch(BaseModel):
    session_id: str
    metrics: List[Dict[str, Any]]


class SystemMetricsResponse(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_latency: float
    timestamp: datetime


class PerformanceMetricsResponse(BaseModel):
    response_time_p95: float
    response_time_p99: float
    response_time_avg: float
    error_rate: float
    throughput: float
    active_connections: int
    timestamp: datetime


class BusinessMetricsResponse(BaseModel):
    meetings_created: int
    decisions_made: int
    ai_interactions: int
    user_engagement: float
    period: str
    timestamp: datetime


@router.post("/alerts")
async def receive_alert(alert: AlertRequest, background_tasks: BackgroundTasks):
    """Receive and process frontend alerts."""
    try:
        # Log the alert
        logger.warning(
            "frontend_alert_received",
            alert_type=alert.type,
            session_id=alert.session_id,
            user_id=alert.user_id,
            data=alert.data,
            timestamp=alert.timestamp.isoformat()
        )
        
        # Process alert in background
        background_tasks.add_task(process_frontend_alert, alert)
        
        return {"status": "received", "timestamp": datetime.utcnow()}
    
    except Exception as e:
        logger.error("alert_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process alert"
        )


@router.post("/errors")
async def receive_error(error: ErrorRequest, background_tasks: BackgroundTasks):
    """Receive and process frontend errors."""
    try:
        # Record error in monitoring service
        await monitoring_service.record_error(
            error_type=error.type,
            error_message=error.message,
            stack_trace=error.stack or "",
            user_id=error.user_id,
            request_path=error.path
        )
        
        # Log the error
        logger.error(
            "frontend_error_received",
            error_type=error.type,
            message=error.message,
            session_id=error.session_id,
            user_id=error.user_id,
            url=error.url,
            path=error.path,
            timestamp=error.timestamp.isoformat()
        )
        
        return {"status": "received", "timestamp": datetime.utcnow()}
    
    except Exception as e:
        logger.error("error_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process error"
        )


@router.post("/business-metrics")
async def receive_business_metric(metric: BusinessMetricRequest):
    """Receive and process business metrics from frontend."""
    try:
        # Process different types of business metrics
        if metric.type == "meeting_created":
            user_type = metric.data.get("userType", "unknown")
            meeting_type = metric.data.get("meetingType", "unknown")
            monitoring_service.record_meeting_created(user_type, meeting_type)
        
        elif metric.type == "decision_made":
            decision_type = metric.data.get("decisionType", "unknown")
            outcome = metric.data.get("outcome", "unknown")
            monitoring_service.record_decision_made(decision_type, outcome)
        
        elif metric.type == "ai_interaction":
            monitoring_service.record_business_metric(
                "ai_interaction",
                1.0,
                "count",
                metric.data
            )
        
        elif metric.type == "user_action":
            monitoring_service.record_business_metric(
                "user_action",
                1.0,
                "count",
                metric.data
            )
        
        elif metric.type == "feature_usage":
            monitoring_service.record_business_metric(
                "feature_usage",
                1.0,
                "count",
                metric.data
            )
        
        logger.info(
            "business_metric_received",
            metric_type=metric.type,
            session_id=metric.session_id,
            user_id=metric.user_id,
            data=metric.data
        )
        
        return {"status": "received", "timestamp": datetime.utcnow()}
    
    except Exception as e:
        logger.error("business_metric_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process business metric"
        )


@router.post("/performance-batch")
async def receive_performance_batch(batch: PerformanceMetricsBatch):
    """Receive batch of performance metrics from frontend."""
    try:
        logger.info(
            "performance_batch_received",
            session_id=batch.session_id,
            metric_count=len(batch.metrics)
        )
        
        # Process each metric in the batch
        for metric in batch.metrics:
            # Store metrics for analysis
            pass
        
        return {"status": "received", "count": len(batch.metrics)}
    
    except Exception as e:
        logger.error("performance_batch_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process performance batch"
        )


@router.post("/errors-batch")
async def receive_errors_batch(batch: ErrorsBatch):
    """Receive batch of errors from frontend."""
    try:
        logger.info(
            "errors_batch_received",
            session_id=batch.session_id,
            error_count=len(batch.errors)
        )
        
        # Process each error in the batch
        for error in batch.errors:
            await monitoring_service.record_error(
                error_type=error.type,
                error_message=error.message,
                stack_trace=error.stack or "",
                user_id=error.user_id,
                request_path=error.path
            )
        
        return {"status": "received", "count": len(batch.errors)}
    
    except Exception as e:
        logger.error("errors_batch_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process errors batch"
        )


@router.post("/engagement-batch")
async def receive_engagement_batch(batch: EngagementBatch):
    """Receive batch of user engagement metrics from frontend."""
    try:
        logger.info(
            "engagement_batch_received",
            session_id=batch.session_id,
            metric_count=len(batch.metrics)
        )
        
        # Process each engagement metric
        for metric in batch.metrics:
            monitoring_service.record_business_metric(
                "user_engagement",
                metric.get("value", 0),
                "score",
                {"session_id": batch.session_id}
            )
        
        return {"status": "received", "count": len(batch.metrics)}
    
    except Exception as e:
        logger.error("engagement_batch_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process engagement batch"
        )


@router.post("/business-metrics-batch")
async def receive_business_metrics_batch(batch: BusinessMetricsBatch):
    """Receive batch of business metrics from frontend."""
    try:
        logger.info(
            "business_metrics_batch_received",
            session_id=batch.session_id,
            metric_count=len(batch.metrics)
        )
        
        # Process each business metric
        for metric in batch.metrics:
            monitoring_service.record_business_metric(
                metric.get("type", "unknown"),
                metric.get("value", 0),
                metric.get("unit", "count"),
                metric.get("tags", {})
            )
        
        return {"status": "received", "count": len(batch.metrics)}
    
    except Exception as e:
        logger.error("business_metrics_batch_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process business metrics batch"
        )


@router.get("/system-metrics", response_model=SystemMetricsResponse)
async def get_system_metrics():
    """Get current system metrics."""
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # Simulate network latency (would be measured in real implementation)
        network_latency = 10.0
        
        return SystemMetricsResponse(
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            disk_usage=disk_percent,
            network_latency=network_latency,
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error("system_metrics_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics"
        )


@router.get("/performance-metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics():
    """Get current application performance metrics."""
    try:
        apm_metrics = await monitoring_service.get_apm_metrics()
        
        return PerformanceMetricsResponse(
            response_time_p95=apm_metrics.response_time_p95,
            response_time_p99=apm_metrics.response_time_p99,
            response_time_avg=apm_metrics.response_time_avg,
            error_rate=apm_metrics.error_rate,
            throughput=apm_metrics.throughput,
            active_connections=apm_metrics.active_connections,
            timestamp=apm_metrics.timestamp
        )
    
    except Exception as e:
        logger.error("performance_metrics_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


@router.get("/business-metrics", response_model=BusinessMetricsResponse)
async def get_business_metrics(hours: int = 24):
    """Get business metrics summary."""
    try:
        summary = await monitoring_service.get_business_metrics_summary(hours)
        
        # Extract key metrics
        meetings_created = summary["summary"].get("meeting_created", {}).get("total", 0)
        decisions_made = summary["summary"].get("decision_made", {}).get("total", 0)
        ai_interactions = summary["summary"].get("ai_interaction", {}).get("total", 0)
        user_engagement = summary["summary"].get("user_engagement", {}).get("average", 0)
        
        return BusinessMetricsResponse(
            meetings_created=int(meetings_created),
            decisions_made=int(decisions_made),
            ai_interactions=int(ai_interactions),
            user_engagement=float(user_engagement),
            period=f"Last {hours} hours",
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error("business_metrics_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business metrics"
        )


@router.get("/error-summary")
async def get_error_summary(hours: int = 24):
    """Get error summary for the specified time period."""
    try:
        summary = await monitoring_service.get_error_summary(hours)
        return summary
    
    except Exception as e:
        logger.error("error_summary_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve error summary"
        )


@router.get("/health")
async def get_health_status():
    """Get comprehensive health status."""
    try:
        health_status = await health_service.get_comprehensive_health()
        return health_status
    
    except Exception as e:
        logger.error("health_status_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve health status"
        )


@router.get("/prometheus-metrics")
async def get_prometheus_metrics():
    """Get Prometheus metrics in text format."""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response
        
        metrics_data = generate_latest()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    
    except Exception as e:
        logger.error("prometheus_metrics_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Prometheus metrics"
        )


@router.post("/start-monitoring")
async def start_monitoring():
    """Start the monitoring service."""
    try:
        await monitoring_service.start_monitoring()
        logger.info("monitoring_service_started", message="Monitoring service started via API")
        return {"status": "started", "timestamp": datetime.utcnow()}
    
    except Exception as e:
        logger.error("start_monitoring_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start monitoring service"
        )


@router.post("/stop-monitoring")
async def stop_monitoring():
    """Stop the monitoring service."""
    try:
        await monitoring_service.stop_monitoring()
        logger.info("monitoring_service_stopped", message="Monitoring service stopped via API")
        return {"status": "stopped", "timestamp": datetime.utcnow()}
    
    except Exception as e:
        logger.error("stop_monitoring_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop monitoring service"
        )


async def process_frontend_alert(alert: AlertRequest):
    """Process frontend alert in background."""
    try:
        # Determine alert severity and take appropriate action
        alert_type = alert.type
        alert_data = alert.data
        
        if alert_type == "memory_usage":
            threshold = alert_data.get("threshold", 0)
            current = alert_data.get("current", 0)
            
            if current > threshold * 1.5:  # Critical threshold
                logger.critical(
                    "critical_memory_alert",
                    current_usage=current,
                    threshold=threshold,
                    session_id=alert.session_id
                )
        
        elif alert_type == "response_time":
            threshold = alert_data.get("threshold", 0)
            current = alert_data.get("current", 0)
            
            if current > threshold * 2:  # Critical threshold
                logger.critical(
                    "critical_response_time_alert",
                    current_time=current,
                    threshold=threshold,
                    session_id=alert.session_id
                )
        
        elif alert_type == "error_rate":
            threshold = alert_data.get("threshold", 0)
            current = alert_data.get("current", 0)
            
            if current > threshold * 3:  # Critical threshold
                logger.critical(
                    "critical_error_rate_alert",
                    current_rate=current,
                    threshold=threshold,
                    session_id=alert.session_id
                )
        
        # Update monitoring metrics
        monitoring_service.record_business_metric(
            f"frontend_alert_{alert_type}",
            1.0,
            "count",
            {"session_id": alert.session_id, "severity": "warning"}
        )
        
    except Exception as e:
        logger.error("frontend_alert_processing_error", error=str(e), alert=alert.dict())


# Background task to initialize monitoring on startup
async def initialize_monitoring():
    """Initialize monitoring service on application startup."""
    try:
        await monitoring_service.start_monitoring()
        logger.info("monitoring_service_initialized", message="Monitoring service initialized on startup")
    except Exception as e:
        logger.error("monitoring_initialization_error", error=str(e))