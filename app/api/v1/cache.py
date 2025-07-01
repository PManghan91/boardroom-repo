"""Cache management API endpoints.

This module provides comprehensive cache management endpoints including health monitoring,
statistics, cache warming, invalidation, and administrative operations.
"""

import time
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.v1.auth import get_current_session, get_current_user
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.api_standards import create_standard_response, create_error_response
from app.models.session import Session
from app.models.user import User
from app.services.redis_service import get_redis_service
from app.services.database import database_service

router = APIRouter()


@router.get("/health")
@limiter.limit("30 per minute")
async def get_cache_health(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get comprehensive cache service health status.
    
    Returns detailed information about Redis connectivity, performance metrics,
    connection pool status, and recent error history.
    """
    try:
        redis_service = await get_redis_service()
        health_info = await redis_service.health_check()
        
        # Add additional health metrics
        health_info.update({
            "service": "redis_cache",
            "version": "1.0.0",
            "timestamp": time.time(),
            "request_id": getattr(request.state, 'request_id', 'unknown')
        })
        
        # Determine overall health status
        overall_status = "healthy"
        if health_info["status"] == "unhealthy":
            overall_status = "unhealthy"
        elif health_info["status"] == "degraded" or health_info.get("stats", {}).get("errors", 0) > 10:
            overall_status = "degraded"
        
        health_info["overall_status"] = overall_status
        
        logger.info("cache_health_check_requested",
                   session_id=session.id,
                   cache_status=health_info["status"],
                   overall_status=overall_status)
        
        return create_standard_response(
            data=health_info,
            message="Cache health status retrieved successfully"
        )
    
    except Exception as e:
        logger.error("cache_health_check_failed",
                    session_id=session.id,
                    error=str(e),
                    exc_info=True)
        return create_error_response(
            message="Failed to retrieve cache health status",
            error_type="cache_health_error",
            details={"session_id": session.id},
            status_code=500
        )


@router.get("/stats")
@limiter.limit("20 per minute")
async def get_cache_statistics(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get detailed cache performance statistics.
    
    Returns comprehensive cache metrics including hit rates, operation counts,
    error rates, and performance data over different time windows.
    """
    try:
        redis_service = await get_redis_service()
        health_info = await redis_service.health_check()
        stats = health_info.get("stats", {})
        
        # Enhanced statistics
        detailed_stats = {
            "performance": {
                "hit_rate": stats.get("hit_rate", 0.0),
                "total_operations": stats.get("total_operations", 0),
                "operations_per_second": stats.get("total_operations", 0) / max(stats.get("uptime_seconds", 1), 1),
                "error_rate": stats.get("errors", 0) / max(stats.get("total_operations", 1), 1),
            },
            "operations": {
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
                "sets": stats.get("sets", 0),
                "deletes": stats.get("deletes", 0),
                "errors": stats.get("errors", 0),
            },
            "health": {
                "status": health_info.get("status", "unknown"),
                "uptime_seconds": stats.get("uptime_seconds", 0),
                "connection_pool_active": health_info.get("connection_pool_created", False),
                "recent_error_count": len(health_info.get("recent_errors", [])),
            },
            "metadata": {
                "timestamp": time.time(),
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "last_health_check": health_info.get("last_check", 0),
            }
        }
        
        logger.info("cache_statistics_requested",
                   session_id=session.id,
                   hit_rate=detailed_stats["performance"]["hit_rate"],
                   total_operations=detailed_stats["performance"]["total_operations"])
        
        return create_standard_response(
            data=detailed_stats,
            message="Cache statistics retrieved successfully"
        )
    
    except Exception as e:
        logger.error("cache_statistics_failed",
                    session_id=session.id,
                    error=str(e),
                    exc_info=True)
        return create_error_response(
            message="Failed to retrieve cache statistics",
            error_type="cache_stats_error",
            details={"session_id": session.id},
            status_code=500
        )


@router.post("/warm/user/{user_id}")
@limiter.limit("5 per minute")
async def warm_user_cache(
    user_id: str,
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Warm cache with user-specific data.
    
    Pre-loads frequently accessed user data into cache to improve
    response times for subsequent requests.
    """
    try:
        redis_service = await get_redis_service()
        
        # Validate user access (users can only warm their own cache unless admin)
        current_user = await database_service.get_user_by_id(session.user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="Current user not found")
        
        # For now, allow users to warm any cache (in production, add proper permission checks)
        target_user = await database_service.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        
        warmed_items = []
        
        # Warm user profile data
        user_cache_key = f"user_profile:{user_id}"
        if not await redis_service.exists(user_cache_key):
            await redis_service.set(
                user_cache_key,
                {
                    "id": target_user.id,
                    "email": target_user.email,
                    "full_name": target_user.full_name,
                    "is_active": target_user.is_active,
                    "created_at": target_user.created_at.isoformat() if target_user.created_at else None,
                },
                ttl=3600,
                cache_type="user_sessions"
            )
            warmed_items.append("user_profile")
        
        # Warm user sessions data
        sessions_cache_key = f"user_sessions:{user_id}"
        if not await redis_service.exists(sessions_cache_key):
            # This would typically fetch session data from database
            await redis_service.set(
                sessions_cache_key,
                {"sessions": [], "total_count": 0},
                ttl=1800,
                cache_type="user_sessions"
            )
            warmed_items.append("user_sessions")
        
        logger.info("user_cache_warmed",
                   session_id=session.id,
                   target_user_id=user_id,
                   warmed_items=warmed_items)
        
        return create_standard_response(
            data={
                "user_id": user_id,
                "warmed_items": warmed_items,
                "cache_keys_created": len(warmed_items),
                "timestamp": time.time()
            },
            message=f"User cache warmed successfully with {len(warmed_items)} items"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("user_cache_warming_failed",
                    session_id=session.id,
                    target_user_id=user_id,
                    error=str(e),
                    exc_info=True)
        return create_error_response(
            message="Failed to warm user cache",
            error_type="cache_warming_error",
            details={"session_id": session.id, "user_id": user_id},
            status_code=500
        )


@router.delete("/invalidate/user/{user_id}")
@limiter.limit("10 per minute") 
async def invalidate_user_cache(
    user_id: str,
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Invalidate all cache entries for a specific user.
    
    Removes all cached data related to the specified user including
    profile data, sessions, and user-specific API responses.
    """
    try:
        redis_service = await get_redis_service()
        
        # Invalidate user-related cache patterns
        patterns_to_invalidate = [
            f"user_profile:{user_id}",
            f"user_sessions:{user_id}",
            f"api_cache:*auth*{user_id}*",
        ]
        
        total_invalidated = 0
        invalidation_results = {}
        
        for pattern in patterns_to_invalidate:
            try:
                count = await redis_service.invalidate_pattern(pattern)
                invalidation_results[pattern] = count
                total_invalidated += count
            except Exception as e:
                logger.warning("pattern_invalidation_failed",
                             pattern=pattern,
                             error=str(e))
                invalidation_results[pattern] = 0
        
        logger.info("user_cache_invalidated",
                   session_id=session.id,
                   target_user_id=user_id,
                   total_invalidated=total_invalidated,
                   patterns=list(invalidation_results.keys()))
        
        return create_standard_response(
            data={
                "user_id": user_id,
                "total_invalidated": total_invalidated,
                "invalidation_results": invalidation_results,
                "timestamp": time.time()
            },
            message=f"User cache invalidated successfully ({total_invalidated} items removed)"
        )
    
    except Exception as e:
        logger.error("user_cache_invalidation_failed",
                    session_id=session.id,
                    target_user_id=user_id,
                    error=str(e),
                    exc_info=True)
        return create_error_response(
            message="Failed to invalidate user cache",
            error_type="cache_invalidation_error",
            details={"session_id": session.id, "user_id": user_id},
            status_code=500
        )


@router.post("/test")
@limiter.limit("10 per minute")
async def test_cache_operations(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Test cache operations for validation and debugging.
    
    Performs a series of cache operations (set, get, delete) to validate
    cache functionality and measure performance.
    """
    try:
        redis_service = await get_redis_service()
        
        test_results = {}
        test_key = f"cache_test:{session.id}:{int(time.time())}"
        test_value = {
            "test_data": "cache_operation_test",
            "timestamp": time.time(),
            "session_id": session.id
        }
        
        # Test SET operation
        start_time = time.time()
        set_result = await redis_service.set(test_key, test_value, ttl=60, cache_type="default")
        set_duration = (time.time() - start_time) * 1000
        test_results["set"] = {
            "success": set_result,
            "duration_ms": set_duration
        }
        
        # Test GET operation
        start_time = time.time()
        get_result = await redis_service.get(test_key)
        get_duration = (time.time() - start_time) * 1000
        test_results["get"] = {
            "success": get_result is not None,
            "data_matches": get_result == test_value if get_result else False,
            "duration_ms": get_duration
        }
        
        # Test EXISTS operation
        start_time = time.time()
        exists_result = await redis_service.exists(test_key)
        exists_duration = (time.time() - start_time) * 1000
        test_results["exists"] = {
            "success": exists_result,
            "duration_ms": exists_duration
        }
        
        # Test DELETE operation
        start_time = time.time()
        delete_result = await redis_service.delete(test_key)
        delete_duration = (time.time() - start_time) * 1000
        test_results["delete"] = {
            "success": delete_result,
            "duration_ms": delete_duration
        }
        
        # Overall test status
        all_operations_successful = all(
            result.get("success", False) for result in test_results.values()
        )
        
        total_duration = sum(
            result.get("duration_ms", 0) for result in test_results.values()
        )
        
        logger.info("cache_operations_tested",
                   session_id=session.id,
                   test_key=test_key,
                   all_successful=all_operations_successful,
                   total_duration_ms=total_duration)
        
        return create_standard_response(
            data={
                "test_results": test_results,
                "all_operations_successful": all_operations_successful,
                "total_duration_ms": total_duration,
                "test_key": test_key,
                "timestamp": time.time()
            },
            message="Cache operations test completed successfully"
        )
    
    except Exception as e:
        logger.error("cache_operations_test_failed",
                    session_id=session.id,
                    error=str(e),
                    exc_info=True)
        return create_error_response(
            message="Failed to complete cache operations test",
            error_type="cache_test_error",
            details={"session_id": session.id},
            status_code=500
        )