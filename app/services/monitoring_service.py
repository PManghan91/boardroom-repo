"""
Comprehensive monitoring service for the Boardroom application.
Provides APM, infrastructure monitoring, error tracking, and business metrics.
"""

import asyncio
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import psutil
import logging

from prometheus_client import Counter, Histogram, Gauge, Info, Enum
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import (
    http_requests_total, 
    http_request_duration_seconds,
    ai_operations_total,
    ai_operation_duration_seconds,
    cache_operations_total,
    cache_hit_ratio
)
from app.services.redis_service import redis_service


@dataclass
class APMMetrics:
    """Application Performance Monitoring metrics."""
    response_time_p95: float
    response_time_p99: float
    response_time_avg: float
    error_rate: float
    throughput: float
    active_connections: int
    cpu_usage: float
    memory_usage: float
    timestamp: datetime


@dataclass
class ErrorPattern:
    """Error pattern tracking."""
    error_type: str
    count: int
    first_seen: datetime
    last_seen: datetime
    affected_users: set
    error_messages: List[str]
    stack_traces: List[str]


@dataclass
class BusinessMetric:
    """Business metrics tracking."""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]


class MonitoringService:
    """Comprehensive monitoring service for production applications."""
    
    def __init__(self):
        self.startup_time = datetime.utcnow()
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.business_metrics: Dict[str, List[BusinessMetric]] = defaultdict(list)
        self.apm_history: deque = deque(maxlen=1000)
        self.alert_thresholds = {
            "error_rate": 0.05,  # 5%
            "response_time_p95": 2000,  # 2 seconds
            "cpu_usage": 80.0,  # 80%
            "memory_usage": 85.0,  # 85%
            "disk_usage": 90.0,  # 90%
        }
        
        # Prometheus metrics
        self.setup_prometheus_metrics()
        
        # Background tasks
        self._monitoring_tasks = []
        
    def setup_prometheus_metrics(self):
        """Setup additional Prometheus metrics for monitoring."""
        # Application metrics
        self.app_info = Info('app_info', 'Application information')
        self.app_info.info({
            'version': settings.VERSION if hasattr(settings, 'VERSION') else '0.0.3',
            'environment': settings.ENVIRONMENT,
            'startup_time': self.startup_time.isoformat()
        })
        
        # Error tracking metrics
        self.error_patterns_total = Counter(
            'error_patterns_total',
            'Total number of error patterns detected',
            ['error_type', 'severity']
        )
        
        # Business metrics
        self.meetings_created_total = Counter(
            'meetings_created_total',
            'Total number of meetings created',
            ['user_type', 'meeting_type']
        )
        
        self.decisions_made_total = Counter(
            'decisions_made_total',
            'Total number of decisions made',
            ['decision_type', 'outcome']
        )
        
        self.user_engagement_score = Gauge(
            'user_engagement_score',
            'User engagement score',
            ['user_id', 'session_id']
        )
        
        self.meeting_effectiveness_score = Gauge(
            'meeting_effectiveness_score',
            'Meeting effectiveness score',
            ['meeting_id', 'meeting_type']
        )
        
        # Infrastructure metrics
        self.database_pool_active = Gauge(
            'database_pool_active',
            'Active database connections in pool'
        )
        
        self.database_pool_idle = Gauge(
            'database_pool_idle',
            'Idle database connections in pool'
        )
        
        self.redis_memory_usage = Gauge(
            'redis_memory_usage_bytes',
            'Redis memory usage in bytes'
        )
        
        self.redis_connected_clients = Gauge(
            'redis_connected_clients',
            'Number of connected Redis clients'
        )
        
        # System metrics
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage'
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage'
        )
        
        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage'
        )
        
        # Real-time metrics
        self.active_websocket_connections = Gauge(
            'active_websocket_connections',
            'Number of active WebSocket connections'
        )
        
        self.realtime_events_total = Counter(
            'realtime_events_total',
            'Total number of real-time events',
            ['event_type', 'channel']
        )
        
    async def start_monitoring(self):
        """Start background monitoring tasks."""
        self._monitoring_tasks = [
            asyncio.create_task(self._monitor_system_metrics()),
            asyncio.create_task(self._monitor_database_metrics()),
            asyncio.create_task(self._monitor_redis_metrics()),
            asyncio.create_task(self._monitor_error_patterns()),
            asyncio.create_task(self._monitor_business_metrics()),
        ]
        
        logger.info("monitoring_started", 
                   task_count=len(self._monitoring_tasks),
                   message="Monitoring service started")
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks."""
        for task in self._monitoring_tasks:
            task.cancel()
        
        await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        logger.info("monitoring_stopped", message="Monitoring service stopped")
    
    async def _monitor_system_metrics(self):
        """Monitor system-level metrics."""
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.system_cpu_usage.set(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.system_memory_usage.set(memory.percent)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.system_disk_usage.set(disk_percent)
                
                # Check thresholds and trigger alerts
                await self._check_system_thresholds(cpu_percent, memory.percent, disk_percent)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error("system_monitoring_error", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _monitor_database_metrics(self):
        """Monitor database metrics."""
        while True:
            try:
                from app.services.database import database_service
                
                # Get connection pool stats
                pool_stats = await database_service.get_pool_stats()
                
                if pool_stats:
                    self.database_pool_active.set(pool_stats.get('active', 0))
                    self.database_pool_idle.set(pool_stats.get('idle', 0))
                
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                logger.error("database_monitoring_error", error=str(e))
                await asyncio.sleep(60)
    
    async def _monitor_redis_metrics(self):
        """Monitor Redis metrics."""
        while True:
            try:
                info = await redis_service.get_info()
                
                if info:
                    self.redis_memory_usage.set(info.get('used_memory', 0))
                    self.redis_connected_clients.set(info.get('connected_clients', 0))
                
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                logger.error("redis_monitoring_error", error=str(e))
                await asyncio.sleep(60)
    
    async def _monitor_error_patterns(self):
        """Monitor and analyze error patterns."""
        while True:
            try:
                # Analyze error patterns and detect anomalies
                for error_type, pattern in self.error_patterns.items():
                    if self._is_error_pattern_critical(pattern):
                        await self._trigger_error_alert(error_type, pattern)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error("error_pattern_monitoring_error", error=str(e))
                await asyncio.sleep(120)
    
    async def _monitor_business_metrics(self):
        """Monitor business metrics and KPIs."""
        while True:
            try:
                # Calculate business metrics
                await self._calculate_user_engagement()
                await self._calculate_meeting_effectiveness()
                await self._calculate_decision_velocity()
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error("business_metrics_monitoring_error", error=str(e))
                await asyncio.sleep(600)
    
    async def record_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: str,
        user_id: Optional[str] = None,
        request_path: Optional[str] = None
    ):
        """Record error for pattern analysis."""
        now = datetime.utcnow()
        
        if error_type not in self.error_patterns:
            self.error_patterns[error_type] = ErrorPattern(
                error_type=error_type,
                count=0,
                first_seen=now,
                last_seen=now,
                affected_users=set(),
                error_messages=[],
                stack_traces=[]
            )
        
        pattern = self.error_patterns[error_type]
        pattern.count += 1
        pattern.last_seen = now
        
        if user_id:
            pattern.affected_users.add(user_id)
        
        if error_message not in pattern.error_messages:
            pattern.error_messages.append(error_message)
        
        if stack_trace not in pattern.stack_traces:
            pattern.stack_traces.append(stack_trace)
        
        # Update Prometheus metrics
        severity = self._classify_error_severity(error_type, error_message)
        self.error_patterns_total.labels(error_type=error_type, severity=severity).inc()
        
        logger.error(
            "error_recorded",
            error_type=error_type,
            error_message=error_message,
            user_id=user_id,
            request_path=request_path,
            pattern_count=pattern.count,
            affected_users=len(pattern.affected_users)
        )
    
    def record_business_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "count",
        tags: Optional[Dict[str, str]] = None
    ):
        """Record business metric."""
        metric = BusinessMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        
        self.business_metrics[metric_name].append(metric)
        
        # Keep only last 1000 metrics per type
        if len(self.business_metrics[metric_name]) > 1000:
            self.business_metrics[metric_name] = self.business_metrics[metric_name][-1000:]
        
        logger.info(
            "business_metric_recorded",
            metric_name=metric_name,
            value=value,
            unit=unit,
            tags=tags
        )
    
    def record_meeting_created(self, user_type: str, meeting_type: str):
        """Record meeting creation."""
        self.meetings_created_total.labels(
            user_type=user_type,
            meeting_type=meeting_type
        ).inc()
        
        self.record_business_metric(
            "meeting_created",
            1.0,
            "count",
            {"user_type": user_type, "meeting_type": meeting_type}
        )
    
    def record_decision_made(self, decision_type: str, outcome: str):
        """Record decision made."""
        self.decisions_made_total.labels(
            decision_type=decision_type,
            outcome=outcome
        ).inc()
        
        self.record_business_metric(
            "decision_made",
            1.0,
            "count",
            {"decision_type": decision_type, "outcome": outcome}
        )
    
    def record_user_engagement(self, user_id: str, session_id: str, score: float):
        """Record user engagement score."""
        self.user_engagement_score.labels(
            user_id=user_id,
            session_id=session_id
        ).set(score)
        
        self.record_business_metric(
            "user_engagement",
            score,
            "score",
            {"user_id": user_id, "session_id": session_id}
        )
    
    def record_meeting_effectiveness(self, meeting_id: str, meeting_type: str, score: float):
        """Record meeting effectiveness score."""
        self.meeting_effectiveness_score.labels(
            meeting_id=meeting_id,
            meeting_type=meeting_type
        ).set(score)
        
        self.record_business_metric(
            "meeting_effectiveness",
            score,
            "score",
            {"meeting_id": meeting_id, "meeting_type": meeting_type}
        )
    
    def record_websocket_connection(self, connected: bool):
        """Record WebSocket connection change."""
        if connected:
            self.active_websocket_connections.inc()
        else:
            self.active_websocket_connections.dec()
    
    def record_realtime_event(self, event_type: str, channel: str):
        """Record real-time event."""
        self.realtime_events_total.labels(
            event_type=event_type,
            channel=channel
        ).inc()
    
    async def get_apm_metrics(self) -> APMMetrics:
        """Get current APM metrics."""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # Calculate response time metrics from recent requests
            response_times = []
            error_count = 0
            total_requests = 0
            
            # This would be calculated from request history
            # For now, we'll use dummy values that would be calculated from actual metrics
            response_time_p95 = 500.0  # milliseconds
            response_time_p99 = 1000.0  # milliseconds
            response_time_avg = 250.0   # milliseconds
            error_rate = 0.02  # 2%
            throughput = 100.0  # requests per second
            
            # Active connections (would be tracked by connection pool)
            active_connections = 10
            
            return APMMetrics(
                response_time_p95=response_time_p95,
                response_time_p99=response_time_p99,
                response_time_avg=response_time_avg,
                error_rate=error_rate,
                throughput=throughput,
                active_connections=active_connections,
                cpu_usage=cpu_percent,
                memory_usage=memory.percent,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error("apm_metrics_error", error=str(e))
            raise
    
    async def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        active_patterns = {}
        total_errors = 0
        affected_users = set()
        
        for error_type, pattern in self.error_patterns.items():
            if pattern.last_seen >= cutoff:
                active_patterns[error_type] = {
                    "count": pattern.count,
                    "first_seen": pattern.first_seen.isoformat(),
                    "last_seen": pattern.last_seen.isoformat(),
                    "affected_users": len(pattern.affected_users),
                    "recent_messages": pattern.error_messages[-5:],  # Last 5 messages
                    "severity": self._classify_error_severity(error_type, pattern.error_messages[-1] if pattern.error_messages else "")
                }
                total_errors += pattern.count
                affected_users.update(pattern.affected_users)
        
        return {
            "summary": {
                "total_error_patterns": len(active_patterns),
                "total_errors": total_errors,
                "affected_users": len(affected_users),
                "time_period_hours": hours
            },
            "patterns": active_patterns,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_business_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get business metrics summary."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        summary = {}
        for metric_name, metrics in self.business_metrics.items():
            recent_metrics = [m for m in metrics if m.timestamp >= cutoff]
            
            if recent_metrics:
                values = [m.value for m in recent_metrics]
                summary[metric_name] = {
                    "count": len(recent_metrics),
                    "total": sum(values),
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "unit": recent_metrics[0].unit,
                    "last_value": recent_metrics[-1].value,
                    "last_timestamp": recent_metrics[-1].timestamp.isoformat()
                }
        
        return {
            "summary": summary,
            "time_period_hours": hours,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _classify_error_severity(self, error_type: str, error_message: str) -> str:
        """Classify error severity."""
        critical_patterns = [
            "database", "redis", "connection", "timeout", "memory", "disk"
        ]
        
        warning_patterns = [
            "validation", "authentication", "authorization", "rate_limit"
        ]
        
        error_lower = f"{error_type} {error_message}".lower()
        
        for pattern in critical_patterns:
            if pattern in error_lower:
                return "critical"
        
        for pattern in warning_patterns:
            if pattern in error_lower:
                return "warning"
        
        return "info"
    
    def _is_error_pattern_critical(self, pattern: ErrorPattern) -> bool:
        """Check if error pattern is critical."""
        now = datetime.utcnow()
        
        # Critical if many errors in short time
        if pattern.count > 50 and (now - pattern.first_seen).total_seconds() < 3600:
            return True
        
        # Critical if affecting many users
        if len(pattern.affected_users) > 10:
            return True
        
        # Critical if database or Redis errors
        if any(keyword in pattern.error_type.lower() for keyword in ["database", "redis", "connection"]):
            return pattern.count > 10
        
        return False
    
    async def _trigger_error_alert(self, error_type: str, pattern: ErrorPattern):
        """Trigger alert for critical error pattern."""
        alert_data = {
            "alert_type": "error_pattern",
            "error_type": error_type,
            "severity": "critical",
            "count": pattern.count,
            "affected_users": len(pattern.affected_users),
            "first_seen": pattern.first_seen.isoformat(),
            "last_seen": pattern.last_seen.isoformat(),
            "recent_messages": pattern.error_messages[-3:],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.critical(
            "error_pattern_alert",
            alert_data=alert_data,
            message=f"Critical error pattern detected: {error_type}"
        )
        
        # In production, this would send notifications via email, Slack, etc.
        print(f"🚨 CRITICAL ERROR PATTERN ALERT: {error_type}")
        print(f"   Count: {pattern.count}")
        print(f"   Affected Users: {len(pattern.affected_users)}")
        print(f"   Duration: {(pattern.last_seen - pattern.first_seen).total_seconds():.0f} seconds")
    
    async def _check_system_thresholds(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Check system thresholds and trigger alerts."""
        alerts = []
        
        if cpu_percent > self.alert_thresholds["cpu_usage"]:
            alerts.append(f"High CPU usage: {cpu_percent:.1f}%")
        
        if memory_percent > self.alert_thresholds["memory_usage"]:
            alerts.append(f"High memory usage: {memory_percent:.1f}%")
        
        if disk_percent > self.alert_thresholds["disk_usage"]:
            alerts.append(f"High disk usage: {disk_percent:.1f}%")
        
        if alerts:
            logger.warning(
                "system_threshold_alert",
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                alerts=alerts
            )
    
    async def _calculate_user_engagement(self):
        """Calculate user engagement metrics."""
        # This would calculate engagement based on user activity
        # For now, we'll simulate with dummy data
        pass
    
    async def _calculate_meeting_effectiveness(self):
        """Calculate meeting effectiveness metrics."""
        # This would calculate effectiveness based on meeting outcomes
        # For now, we'll simulate with dummy data
        pass
    
    async def _calculate_decision_velocity(self):
        """Calculate decision-making velocity."""
        # This would calculate how quickly decisions are made
        # For now, we'll simulate with dummy data
        pass


# Global monitoring service instance
monitoring_service = MonitoringService()