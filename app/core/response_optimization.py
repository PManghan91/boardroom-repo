"""
Response optimization middleware for API performance enhancement.
Implements compression, caching, and payload optimization.
"""

import gzip
import json
import time
from typing import Any, Dict, Optional, Union
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
import logging
from app.core.config import get_settings
from app.services.redis_service import redis_service
from app.core.metrics import performance_metrics

logger = logging.getLogger(__name__)
settings = get_settings()


class ResponseOptimizationMiddleware(BaseHTTPMiddleware):
    """Middleware for optimizing API responses with compression and caching."""
    
    def __init__(self, app: FastAPI, min_size: int = 500):
        super().__init__(app)
        self.min_size = min_size
        self.compress_types = {
            "application/json",
            "application/javascript", 
            "text/css",
            "text/html",
            "text/plain",
            "text/xml"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and optimize response."""
        start_time = time.time()
        
        # Check for cached response first
        cache_key = await self._generate_cache_key(request)
        cached_response = await self._get_cached_response(cache_key)
        
        if cached_response:
            logger.debug(f"Cache hit for {request.url.path}")
            performance_metrics.cache_operations_total.labels(operation="hit", status="success").inc()
            response = await self._create_response_from_cache(cached_response, request)
            return response
        
        # Process request
        response = await call_next(request)
        
        # Optimize response
        optimized_response = await self._optimize_response(request, response, cache_key)
        
        # Record metrics
        duration = time.time() - start_time
        performance_metrics.http_request_duration_seconds.labels(
            method=request.method, 
            endpoint=request.url.path
        ).observe(duration)
        performance_metrics.cache_operations_total.labels(operation="miss", status="success").inc()
        
        return optimized_response
    
    async def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        # Include method, path, and relevant query parameters
        method = request.method
        path = request.url.path
        query_params = sorted(request.query_params.items())
        
        # Include user context if available
        user_id = getattr(request.state, 'user_id', 'anonymous')
        
        cache_key = f"api_cache:{method}:{path}:{user_id}:{hash(str(query_params))}"
        return cache_key
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if available."""
        try:
            cached_data = await redis_service.get(cache_key)
            if cached_data:
                return json.loads(cached_data) if isinstance(cached_data, str) else cached_data
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        return None
    
    async def _create_response_from_cache(self, cached_data: Dict[str, Any], request: Request) -> Response:
        """Create response from cached data."""
        content = cached_data.get('content', '')
        status_code = cached_data.get('status_code', 200)
        headers = cached_data.get('headers', {})
        
        # Apply compression if requested
        if self._should_compress(request, headers.get('content-type', '')):
            content = await self._compress_content(content)
            headers['content-encoding'] = 'gzip'
        
        headers['x-cache-status'] = 'HIT'
        
        return Response(
            content=content,
            status_code=status_code,
            headers=headers
        )
    
    async def _optimize_response(self, request: Request, response: Response, cache_key: str) -> Response:
        """Optimize response with compression and caching."""
        # Read response content
        content = b""
        async for chunk in response.body_iterator:
            content += chunk
        
        # Optimize payload size
        if response.headers.get("content-type", "").startswith("application/json"):
            content = await self._optimize_json_payload(content)
        
        # Apply compression if appropriate
        original_size = len(content)
        if self._should_compress(request, response.headers.get("content-type", "")):
            if original_size >= self.min_size:
                content = await self._compress_content(content)
                response.headers["content-encoding"] = "gzip"
                # Record compression ratio
                compression_ratio = original_size / len(content) if len(content) > 0 else 1
                logger.debug(f"Compressed response: {original_size} -> {len(content)} bytes (ratio: {compression_ratio:.2f})")
        
        # Cache response if appropriate
        if self._should_cache_response(request, response):
            await self._cache_response(cache_key, content, response)
        
        # Add optimization headers
        response.headers["x-cache-status"] = "MISS"
        response.headers["x-original-size"] = str(original_size)
        response.headers["x-compressed-size"] = str(len(content))
        
        return Response(
            content=content,
            status_code=response.status_code,
            headers=response.headers
        )
    
    async def _optimize_json_payload(self, content: bytes) -> bytes:
        """Optimize JSON payload by removing unnecessary whitespace and fields."""
        try:
            data = json.loads(content)
            
            # Remove null values and empty objects/arrays if configured
            if getattr(settings, 'OPTIMIZE_JSON_PAYLOAD', True):
                data = self._clean_json_data(data)
            
            # Serialize with minimal formatting
            return json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        except Exception as e:
            logger.warning(f"JSON optimization error: {e}")
            return content
    
    def _clean_json_data(self, data: Any) -> Any:
        """Recursively clean JSON data."""
        if isinstance(data, dict):
            return {
                k: self._clean_json_data(v)
                for k, v in data.items()
                if v is not None and v != {} and v != []
            }
        elif isinstance(data, list):
            return [self._clean_json_data(item) for item in data if item is not None]
        return data
    
    async def _compress_content(self, content: Union[str, bytes]) -> bytes:
        """Compress content using gzip."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return gzip.compress(content, compresslevel=6)
    
    def _should_compress(self, request: Request, content_type: str) -> bool:
        """Determine if response should be compressed."""
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return False
        
        # Check content type
        return any(ct in content_type for ct in self.compress_types)
    
    def _should_cache_response(self, request: Request, response: Response) -> bool:
        """Determine if response should be cached."""
        # Only cache GET requests
        if request.method != "GET":
            return False
        
        # Only cache successful responses
        if response.status_code >= 400:
            return False
        
        # Don't cache if explicitly disabled
        if response.headers.get("cache-control") == "no-cache":
            return False
        
        return True
    
    async def _cache_response(self, cache_key: str, content: bytes, response: Response):
        """Cache response for future requests."""
        try:
            cache_data = {
                'content': content.decode('utf-8') if isinstance(content, bytes) else content,
                'status_code': response.status_code,
                'headers': dict(response.headers)
            }
            
            # Determine TTL based on endpoint
            ttl = self._get_cache_ttl(cache_key)
            
            await redis_service.set(
                cache_key, 
                cache_data,
                ttl=ttl,
                cache_type="api_responses"
            )
            
            logger.debug(f"Cached response for {cache_key} with TTL {ttl}")
            
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    def _get_cache_ttl(self, cache_key: str) -> int:
        """Get appropriate TTL for cache key."""
        if "ai_operations" in cache_key or "ai-operations" in cache_key:
            return 300  # 5 minutes for AI operations
        elif "boardroom" in cache_key:
            return 600  # 10 minutes for boardroom data
        elif "auth" in cache_key:
            return 60   # 1 minute for auth data
        else:
            return 180  # 3 minutes default


class PayloadOptimizer:
    """Utility class for optimizing request/response payloads."""
    
    @staticmethod
    def optimize_request_payload(data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize incoming request payload."""
        # Remove empty strings and null values
        return {
            k: v for k, v in data.items() 
            if v is not None and v != "" and v != {}
        }
    
    @staticmethod
    def optimize_response_payload(data: Dict[str, Any], fields: Optional[list] = None) -> Dict[str, Any]:
        """Optimize outgoing response payload."""
        if fields:
            # Return only requested fields
            return {k: v for k, v in data.items() if k in fields}
        
        # Remove sensitive or unnecessary fields
        excluded_fields = {'password', 'secret', 'token', '_internal'}
        return {
            k: v for k, v in data.items() 
            if not any(excluded in k.lower() for excluded in excluded_fields)
        }


def setup_response_optimization(app: FastAPI):
    """Setup response optimization middleware."""
    app.add_middleware(ResponseOptimizationMiddleware)
    logger.info("Response optimization middleware configured")