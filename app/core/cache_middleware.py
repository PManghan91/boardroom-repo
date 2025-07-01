"""Cache middleware for API response caching.

This middleware provides automatic response caching for GET requests with configurable
patterns, smart cache invalidation, ETag generation, and performance optimization.
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, parse_qs

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import logger
from app.services.redis_service import get_redis_service


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic API response caching."""
    
    def __init__(
        self,
        app: ASGIApp,
        cache_patterns: Optional[Dict[str, Dict]] = None,
        default_ttl: int = 600,  # 10 minutes
        enabled: bool = True
    ):
        super().__init__(app)
        self.enabled = enabled
        self.default_ttl = default_ttl
        
        # Default cache patterns - can be overridden
        self.cache_patterns = cache_patterns or {
            "/api/v1/health": {"ttl": 60, "cache_type": "health"},
            "/api/v1/standards": {"ttl": 3600, "cache_type": "api_responses"},
            "/api/v1/boardroom": {"ttl": 300, "cache_type": "api_responses"},
            "/api/v1/decisions": {"ttl": 180, "cache_type": "api_responses"},
            "/api/v1/ai/health": {"ttl": 120, "cache_type": "ai_operations"},
            "/api/v1/ai/metrics": {"ttl": 300, "cache_type": "ai_operations"},
            "/metrics": {"ttl": 30, "cache_type": "api_responses"},
        }
        
        # Methods that invalidate cache
        self.invalidating_methods = {"POST", "PUT", "DELETE", "PATCH"}
        
        # Patterns to exclude from caching
        self.exclude_patterns = {
            "/api/v1/auth/",  # Never cache auth endpoints
            "/api/v1/chatbot/",  # Never cache chat responses
            "/api/v1/cache/",  # Never cache cache management endpoints
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through cache middleware."""
        if not self.enabled:
            return await call_next(request)
        
        redis_service = await get_redis_service()
        
        # Check if path should be excluded
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        # Handle cache invalidation for data-modifying requests
        if request.method in self.invalidating_methods:
            await self._invalidate_related_cache(redis_service, request)
            return await call_next(request)
        
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        start_time = time.time()
        cached_response = await redis_service.get(cache_key)
        
        if cached_response:
            # Cache hit - return cached response
            response_time = (time.time() - start_time) * 1000
            logger.info("cache_hit", 
                       path=request.url.path,
                       cache_key=cache_key,
                       response_time_ms=response_time)
            
            return self._create_response_from_cache(cached_response, request)
        
        # Cache miss - execute request
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200 and hasattr(response, 'body'):
            await self._cache_response(redis_service, cache_key, response, request)
        
        # Add cache headers
        self._add_cache_headers(response, cached=False)
        
        response_time = (time.time() - start_time) * 1000
        logger.info("cache_miss",
                   path=request.url.path,
                   cache_key=cache_key,
                   response_time_ms=response_time,
                   status_code=response.status_code)
        
        return response
    
    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from caching."""
        return any(pattern in path for pattern in self.exclude_patterns)
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        # Include path, query parameters, and relevant headers
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        
        # Include user-specific headers if present (for user-specific caching)
        user_headers = []
        if "authorization" in request.headers:
            # Hash the auth header for user-specific caching
            auth_hash = hashlib.md5(request.headers["authorization"].encode()).hexdigest()[:8]
            user_headers.append(f"auth:{auth_hash}")
        
        # Create cache key
        key_parts = [path, query] + user_headers
        key_string = "|".join(filter(None, key_parts))
        
        # Hash long keys
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"api_cache:hash:{key_hash}"
        
        return f"api_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def _get_cache_config(self, path: str) -> Dict:
        """Get cache configuration for path."""
        # Check exact matches first
        if path in self.cache_patterns:
            return self.cache_patterns[path]
        
        # Check prefix matches
        for pattern, config in self.cache_patterns.items():
            if path.startswith(pattern.rstrip("*")):
                return config
        
        # Default configuration
        return {"ttl": self.default_ttl, "cache_type": "api_responses"}
    
    async def _cache_response(self, redis_service, cache_key: str, response: Response, request: Request):
        """Cache the response."""
        try:
            # Get cache configuration
            config = self._get_cache_config(request.url.path)
            
            # Prepare cache data
            cache_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": None,
                "content_type": response.headers.get("content-type", "application/json"),
                "timestamp": time.time(),
                "ttl": config["ttl"]
            }
            
            # Get response body
            if hasattr(response, 'body'):
                try:
                    if isinstance(response.body, bytes):
                        cache_data["body"] = response.body.decode('utf-8')
                    else:
                        cache_data["body"] = str(response.body)
                except Exception as e:
                    logger.warning("cache_body_extraction_failed", error=str(e))
                    return
            
            # Cache the response
            await redis_service.set(
                cache_key,
                cache_data,
                ttl=config["ttl"],
                cache_type=config["cache_type"]
            )
            
            logger.debug("response_cached",
                        path=request.url.path,
                        cache_key=cache_key,
                        ttl=config["ttl"])
        
        except Exception as e:
            logger.error("response_caching_failed",
                        path=request.url.path,
                        error=str(e),
                        exc_info=True)
    
    def _create_response_from_cache(self, cached_data: Dict, request: Request) -> Response:
        """Create response from cached data."""
        try:
            # Create response
            response = JSONResponse(
                content=json.loads(cached_data["body"]) if cached_data.get("body") else {},
                status_code=cached_data.get("status_code", 200),
                headers=cached_data.get("headers", {})
            )
            
            # Add cache headers
            self._add_cache_headers(response, cached=True, cached_data=cached_data)
            
            return response
        
        except Exception as e:
            logger.error("cache_response_creation_failed", error=str(e))
            # Return empty response if cache data is corrupted
            return JSONResponse(content={"error": "Cache data corrupted"}, status_code=500)
    
    def _add_cache_headers(self, response: Response, cached: bool, cached_data: Optional[Dict] = None):
        """Add cache-related headers to response."""
        if cached and cached_data:
            response.headers["X-Cache"] = "HIT"
            response.headers["X-Cache-Timestamp"] = str(cached_data.get("timestamp", time.time()))
            
            # Calculate age
            cache_time = cached_data.get("timestamp", time.time())
            age = int(time.time() - cache_time)
            response.headers["Age"] = str(age)
            
            # Calculate remaining TTL
            ttl = cached_data.get("ttl", 0)
            max_age = max(0, ttl - age)
            response.headers["Cache-Control"] = f"public, max-age={max_age}"
        else:
            response.headers["X-Cache"] = "MISS"
            response.headers["Cache-Control"] = "public, max-age=60"  # Default cache control
        
        # Generate ETag
        if hasattr(response, 'body') and response.body:
            etag = hashlib.md5(str(response.body).encode()).hexdigest()[:16]
            response.headers["ETag"] = f'"{etag}"'
    
    async def _invalidate_related_cache(self, redis_service, request: Request):
        """Invalidate cache entries related to the request."""
        path = request.url.path
        
        # Define invalidation patterns based on request path
        invalidation_patterns = []
        
        if "/api/v1/boardroom" in path:
            invalidation_patterns.extend([
                "api_cache:*boardroom*",
                "api_cache:*decisions*"
            ])
        elif "/api/v1/decisions" in path:
            invalidation_patterns.extend([
                "api_cache:*decisions*",
                "api_cache:*boardroom*"
            ])
        elif "/api/v1/auth" in path:
            invalidation_patterns.extend([
                "api_cache:*auth*"
            ])
        elif "/api/v1/ai" in path:
            invalidation_patterns.extend([
                "api_cache:*ai*"
            ])
        
        # Perform invalidation
        for pattern in invalidation_patterns:
            try:
                invalidated = await redis_service.invalidate_pattern(pattern)
                if invalidated > 0:
                    logger.info("cache_invalidated",
                               pattern=pattern,
                               invalidated_count=invalidated,
                               triggering_path=path)
            except Exception as e:
                logger.error("cache_invalidation_failed",
                           pattern=pattern,
                           error=str(e))
    
    def _generate_request_fingerprint(self, request: Request) -> str:
        """Generate unique fingerprint for request."""
        # Include method, path, query, and content hash
        components = [
            request.method,
            request.url.path,
            str(request.url.query) if request.url.query else "",
        ]
        
        # Add body hash for POST/PUT requests
        if hasattr(request, 'body') and request.body:
            body_hash = hashlib.md5(request.body).hexdigest()[:8]
            components.append(f"body:{body_hash}")
        
        fingerprint = "|".join(components)
        return hashlib.md5(fingerprint.encode()).hexdigest()