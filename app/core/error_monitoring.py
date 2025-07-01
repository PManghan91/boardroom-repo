"""Error monitoring and alerting utilities for the Boardroom AI application.

This module provides essential error monitoring capabilities suitable for solo development,
including error aggregation, alerting thresholds, and basic monitoring patterns.
"""

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.core.logging import logger


@dataclass
class ErrorMetric:
    """Represents an error metric for monitoring."""
    error_type: str
    count: int
    last_occurrence: datetime
    first_occurrence: datetime
    paths: List[str]
    status_codes: List[int]


class ErrorMonitor:
    """Simple error monitoring system for solo development.
    
    Tracks error patterns, frequencies, and provides basic alerting
    without requiring external monitoring infrastructure.
    """
    
    def __init__(self, window_minutes: int = 60, alert_threshold: int = 10):
        """Initialize the error monitor.
        
        Args:
            window_minutes: Time window for error aggregation
            alert_threshold: Number of errors to trigger alert
        """
        self.window_minutes = window_minutes
        self.alert_threshold = alert_threshold
        self.error_counts: Dict[str, deque] = defaultdict(lambda: deque())
        self.error_details: Dict[str, ErrorMetric] = {}
        self.last_alert_time: Dict[str, datetime] = {}
        
    def record_error(
        self,
        error_type: str,
        path: str,
        status_code: int,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None
    ):
        """Record an error occurrence.
        
        Args:
            error_type: Type/category of the error
            path: Request path where error occurred
            status_code: HTTP status code
            error_message: Error message (optional)
            client_ip: Client IP address (optional)
        """
        now = datetime.now()
        
        # Add timestamp to error count queue
        self.error_counts[error_type].append(now)
        
        # Clean old entries outside the window
        cutoff = now - timedelta(minutes=self.window_minutes)
        while (self.error_counts[error_type] and 
               self.error_counts[error_type][0] < cutoff):
            self.error_counts[error_type].popleft()
        
        # Update error details
        if error_type in self.error_details:
            metric = self.error_details[error_type]
            metric.count = len(self.error_counts[error_type])
            metric.last_occurrence = now
            if path not in metric.paths:
                metric.paths.append(path)
            if status_code not in metric.status_codes:
                metric.status_codes.append(status_code)
        else:
            self.error_details[error_type] = ErrorMetric(
                error_type=error_type,
                count=1,
                last_occurrence=now,
                first_occurrence=now,
                paths=[path],
                status_codes=[status_code]
            )
        
        # Check if alert threshold is exceeded
        error_count = len(self.error_counts[error_type])
        if error_count >= self.alert_threshold:
            self._check_alert_threshold(error_type, error_count, now)
        
        # Log the error for monitoring
        logger.warning(
            "error_monitored",
            error_type=error_type,
            path=path,
            status_code=status_code,
            count_in_window=error_count,
            client_ip=client_ip or "unknown",
            error_message=error_message
        )
    
    def _check_alert_threshold(self, error_type: str, count: int, now: datetime):
        """Check if an alert should be triggered."""
        # Avoid spamming alerts (minimum 10 minutes between alerts for same error type)
        last_alert = self.last_alert_time.get(error_type)
        if last_alert and (now - last_alert) < timedelta(minutes=10):
            return
        
        self.last_alert_time[error_type] = now
        
        # Log alert-level error
        logger.error(
            "error_threshold_exceeded",
            error_type=error_type,
            count=count,
            window_minutes=self.window_minutes,
            threshold=self.alert_threshold,
            alert_triggered=True
        )
        
        # In a production system, this would trigger external alerts
        # For solo development, we log and could send notifications
        self._trigger_alert(error_type, count)
    
    def _trigger_alert(self, error_type: str, count: int):
        """Trigger an alert for high error rates.
        
        In solo development, this logs the alert. In production,
        this could send emails, Slack messages, etc.
        """
        metric = self.error_details[error_type]
        
        alert_message = (
            f"ALERT: High error rate detected\n"
            f"Error Type: {error_type}\n"
            f"Count: {count} errors in {self.window_minutes} minutes\n"
            f"Affected Paths: {', '.join(metric.paths[:5])}\n"
            f"Status Codes: {', '.join(map(str, set(metric.status_codes)))}\n"
            f"First Occurrence: {metric.first_occurrence.isoformat()}\n"
            f"Last Occurrence: {metric.last_occurrence.isoformat()}"
        )
        
        logger.error("error_alert_triggered", alert_message=alert_message)
        
        # For solo development, could also:
        # - Write to a special alert log file
        # - Send email notification
        # - Update a simple dashboard file
        # - Print to console with special formatting
        
        print(f"\n🚨 ERROR ALERT 🚨\n{alert_message}\n")
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, ErrorMetric]:
        """Get error summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary of error metrics
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        summary = {}
        for error_type, metric in self.error_details.items():
            if metric.last_occurrence >= cutoff:
                summary[error_type] = metric
        
        return summary
    
    def get_health_status(self) -> Dict[str, any]:
        """Get overall error monitoring health status.
        
        Returns:
            Health status information
        """
        now = datetime.now()
        recent_cutoff = now - timedelta(minutes=5)
        
        recent_errors = 0
        total_errors = 0
        error_types = set()
        
        for error_type, timestamps in self.error_counts.items():
            total_errors += len(timestamps)
            error_types.add(error_type)
            
            # Count recent errors
            for timestamp in timestamps:
                if timestamp >= recent_cutoff:
                    recent_errors += 1
        
        status = "healthy"
        if recent_errors > 5:
            status = "degraded"
        elif recent_errors > 10:
            status = "unhealthy"
        
        return {
            "status": status,
            "recent_errors_5min": recent_errors,
            "total_error_types": len(error_types),
            "monitoring_window_minutes": self.window_minutes,
            "alert_threshold": self.alert_threshold,
            "timestamp": now.isoformat()
        }


# Global error monitor instance
error_monitor = ErrorMonitor(window_minutes=60, alert_threshold=10)


def record_error(
    error_type: str,
    path: str,
    status_code: int,
    error_message: Optional[str] = None,
    client_ip: Optional[str] = None
):
    """Convenience function to record an error."""
    error_monitor.record_error(
        error_type=error_type,
        path=path,
        status_code=status_code,
        error_message=error_message,
        client_ip=client_ip
    )


def get_error_summary(hours: int = 24) -> Dict[str, ErrorMetric]:
    """Convenience function to get error summary."""
    return error_monitor.get_error_summary(hours=hours)


def get_monitoring_health() -> Dict[str, any]:
    """Convenience function to get monitoring health status."""
    return error_monitor.get_health_status()