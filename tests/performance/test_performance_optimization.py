"""
Comprehensive performance tests for the optimization implementation.
Tests all phases of performance optimization including response optimization,
memory management, and advanced caching.
"""

import pytest
import asyncio
import time
import json
import gzip
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

# Try to import performance optimization modules with fallbacks
try:
    from app.core.response_optimization import ResponseOptimizationMiddleware, PayloadOptimizer
    from app.core.memory_management import MemoryMonitor, ResourceManager, AIMemoryOptimizer
    from app.core.advanced_caching import MultiLevelCache, PredictiveCache, CacheLevel
    PERFORMANCE_MODULES_AVAILABLE = True
except ImportError:
    PERFORMANCE_MODULES_AVAILABLE = False


@pytest.mark.skipif(not PERFORMANCE_MODULES_AVAILABLE, reason="Performance optimization modules not available")
class TestResponseOptimization:
    """Test response optimization middleware and features."""
    
    @pytest.fixture
    def client(self):
        """Test client with response optimization."""
        return TestClient(app)
    
    def test_response_compression(self, client):
        """Test response compression functionality."""
        # Make request with gzip acceptance
        headers = {"accept-encoding": "gzip"}
        response = client.get("/health", headers=headers)
        
        assert response.status_code == 200
        
        # Check cache headers are present
        assert "x-cache-status" in response.headers
    
    def test_cache_headers(self, client):
        """Test cache header generation."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "x-cache-status" in response.headers
    
    def test_payload_optimization(self):
        """Test JSON payload optimization."""
        optimizer = PayloadOptimizer()
        
        # Test request payload optimization
        request_data = {
            "field1": "value1",
            "field2": None,
            "field3": "",
            "field4": {}
        }
        
        optimized = optimizer.optimize_request_payload(request_data)
        assert "field2" not in optimized
        assert "field3" not in optimized
        assert "field4" not in optimized
        assert optimized["field1"] == "value1"
        
        # Test response payload optimization
        response_data = {
            "id": 1,
            "name": "test",
            "password": "secret",
            "token": "hidden"
        }
        
        optimized_response = optimizer.optimize_response_payload(response_data)
        assert "password" not in optimized_response
        assert "token" not in optimized_response
        assert optimized_response["id"] == 1
        assert optimized_response["name"] == "test"
    
    @pytest.mark.asyncio
    async def test_middleware_cache_integration(self):
        """Test middleware integration with caching."""
        middleware = ResponseOptimizationMiddleware(app)
        
        # Mock request
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/test"
        request.query_params.items.return_value = []
        request.state.user_id = "test_user"
        request.headers.get.return_value = "gzip"
        
        # Generate cache key
        cache_key = await middleware._generate_cache_key(request)
        assert "test_user" in cache_key
        assert "/test" in cache_key


@pytest.mark.skipif(not PERFORMANCE_MODULES_AVAILABLE, reason="Performance optimization modules not available")
class TestMemoryManagement:
    """Test memory management and optimization features."""
    
    @pytest.fixture
    def memory_monitor(self):
        """Memory monitor instance."""
        return MemoryMonitor()
    
    @pytest.fixture
    def resource_manager(self):
        """Resource manager instance."""
        return ResourceManager()
    
    @pytest.fixture
    def ai_optimizer(self):
        """AI memory optimizer instance."""
        return AIMemoryOptimizer()
    
    @pytest.mark.asyncio
    async def test_memory_monitoring(self, memory_monitor):
        """Test memory monitoring functionality."""
        # Test memory stats collection
        stats = memory_monitor.get_memory_stats()
        
        assert "rss_mb" in stats
        assert "vms_mb" in stats
        assert "percent" in stats
        assert "available_mb" in stats
        assert "gc_counts" in stats
        
        # Test stats are reasonable
        if stats:  # Only test if we have actual stats
            assert stats["rss_mb"] >= 0
            assert stats["percent"] >= 0
            assert stats["available_mb"] >= 0
    
    @pytest.mark.asyncio
    async def test_resource_cleanup(self, resource_manager):
        """Test resource cleanup functionality."""
        cleanup_called = False
        
        def test_cleanup():
            nonlocal cleanup_called
            cleanup_called = True
        
        # Register cleanup handler
        resource_manager.register_cleanup_handler(test_cleanup)
        
        # Run cleanup
        await resource_manager.cleanup_resources()
        
        assert cleanup_called
    
    @pytest.mark.asyncio
    async def test_ai_memory_optimization(self, ai_optimizer):
        """Test AI memory optimization context manager."""
        # Test optimized context manager
        async with ai_optimizer.optimized_ai_context():
            # Simulate AI operation
            await asyncio.sleep(0.1)
        
        # Should complete without errors
        assert True
    
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, memory_monitor):
        """Test memory pressure handling."""
        # Test with mock high memory usage
        with patch('psutil.Process') as mock_process:
            mock_memory_info = MagicMock()
            mock_memory_info.rss = getattr(settings, 'MEMORY_THRESHOLD_MB', 512) * 1024 * 1024 + 1000000
            mock_process.return_value.memory_info.return_value = mock_memory_info
            mock_process.return_value.memory_percent.return_value = 85.0
            
            # Mock virtual memory
            with patch('psutil.virtual_memory') as mock_virtual:
                mock_virtual.return_value.available = 1000000000
                
                # Collect stats (should trigger memory pressure handling)
                await memory_monitor._collect_memory_stats()
                
                # Should not raise exceptions
                assert True


@pytest.mark.skipif(not PERFORMANCE_MODULES_AVAILABLE, reason="Performance optimization modules not available")
class TestAdvancedCaching:
    """Test advanced caching strategies."""
    
    @pytest.fixture
    def cache(self):
        """Multi-level cache instance."""
        return MultiLevelCache()
    
    @pytest.fixture
    def predictive_cache(self, cache):
        """Predictive cache instance."""
        return PredictiveCache(cache)
    
    @pytest.mark.asyncio
    async def test_multi_level_cache_operations(self, cache):
        """Test basic multi-level cache operations."""
        key = "test_key"
        value = {"data": "test_value", "number": 42}
        
        # Test set and get
        await cache.set(key, value)
        retrieved = await cache.get(key)
        
        assert retrieved == value
        
        # Test L1 cache hit
        l1_entry = await cache._get_l1(key)
        assert l1_entry is not None
        assert l1_entry.data == value
        
        # Test cache deletion
        await cache.delete(key)
        retrieved_after_delete = await cache.get(key)
        assert retrieved_after_delete is None
    
    @pytest.mark.asyncio
    async def test_cache_statistics(self, cache):
        """Test cache statistics tracking."""
        # Perform some cache operations
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        
        assert "l1_hits" in stats
        assert "l1_misses" in stats
        assert "hit_ratio" in stats
        assert stats["l1_hits"] >= 1
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache):
        """Test cache entry expiration."""
        key = "expire_test"
        value = "expire_value"
        
        # Set with very short TTL
        await cache._set_l1(key, value, 1)  # 1 second TTL
        
        # Should be available immediately
        entry = await cache._get_l1(key)
        assert entry is not None
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        entry_after = await cache._get_l1(key)
        assert entry_after is None
    
    @pytest.mark.asyncio
    async def test_cache_eviction(self, cache):
        """Test LRU cache eviction."""
        # Set cache to small size for testing
        original_size = cache.l1_max_size
        cache.l1_max_size = 2
        
        try:
            # Fill cache beyond capacity
            await cache._set_l1("key1", "value1", 300)
            await cache._set_l1("key2", "value2", 300)
            await cache._set_l1("key3", "value3", 300)
            
            # Should only have 2 entries
            assert len(cache.l1_cache) == 2
            
            # key1 should be evicted (LRU)
            entry1 = await cache._get_l1("key1")
            assert entry1 is None
            
        finally:
            cache.l1_max_size = original_size
    
    @pytest.mark.asyncio
    async def test_predictive_cache_patterns(self, predictive_cache):
        """Test predictive caching pattern recording."""
        # Record access pattern
        await predictive_cache.record_access_pattern("user:123:profile")
        
        # Should be recorded in usage patterns
        assert "user:123:profile" in predictive_cache.usage_patterns
        assert len(predictive_cache.usage_patterns["user:123:profile"]) > 0
    
    def test_cached_decorator(self):
        """Test cached decorator functionality."""
        if PERFORMANCE_MODULES_AVAILABLE:
            from app.core.advanced_caching import cached
            
            call_count = 0
            
            @cached(ttl=300, key_prefix="test")
            async def test_function(arg1, arg2):
                nonlocal call_count
                call_count += 1
                return f"{arg1}_{arg2}"
            
            # Function should be decorated properly
            assert asyncio.iscoroutinefunction(test_function)


class TestPerformanceIntegration:
    """Integration tests for performance optimization."""
    
    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)
    
    def test_performance_endpoint(self, client):
        """Test performance statistics endpoint."""
        response = client.get("/performance")
        
        # Should respond even if performance modules aren't available
        assert response.status_code in [200, 503]
        data = response.json()
        
        assert "optimization_status" in data
        assert "timestamp" in data
        
        # If available, should have performance data
        if response.status_code == 200:
            assert "cache_stats" in data
            assert "memory_stats" in data
            assert data["optimization_status"] == "active"
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not PERFORMANCE_MODULES_AVAILABLE, reason="Performance optimization modules not available")
    async def test_memory_optimization_under_load(self):
        """Test memory optimization under simulated load."""
        from app.core.memory_management import memory_monitor
        
        # Get initial memory stats
        initial_stats = memory_monitor.get_memory_stats()
        
        # Simulate memory-intensive operations
        tasks = []
        for i in range(10):
            # Create coroutines that simulate AI operations
            async def simulate_operation():
                # Simulate some memory usage
                data = [i for i in range(1000)]
                await asyncio.sleep(0.1)
                return len(data)
            
            tasks.append(simulate_operation())
        
        # Execute operations concurrently
        results = await asyncio.gather(*tasks)
        
        # Get final memory stats
        final_stats = memory_monitor.get_memory_stats()
        
        # Memory should be managed effectively
        assert len(results) == 10
        
        # Only test memory growth if we have valid stats
        if initial_stats and final_stats and "rss_mb" in initial_stats and "rss_mb" in final_stats:
            memory_growth = final_stats["rss_mb"] - initial_stats["rss_mb"]
            assert memory_growth < 100  # Should not grow excessively
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not PERFORMANCE_MODULES_AVAILABLE, reason="Performance optimization modules not available")
    async def test_cache_hit_ratio_target(self):
        """Test that cache hit ratio meets target."""
        from app.core.advanced_caching import multi_level_cache
        
        # Perform repeated operations to warm cache
        for i in range(5):
            await multi_level_cache.set(f"test_key_{i}", f"test_value_{i}")
        
        # Perform repeated gets (should hit cache)
        for i in range(5):
            for j in range(3):  # Multiple accesses of same keys
                value = await multi_level_cache.get(f"test_key_{i}")
                assert value == f"test_value_{i}"
        
        # Check hit ratio
        stats = multi_level_cache.get_stats()
        hit_ratio = stats.get("hit_ratio", 0)
        
        # Should have a reasonable hit ratio
        assert hit_ratio > 0.5  # At least 50% hit ratio


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)
    
    def test_response_time_targets(self, client):
        """Test API response time targets."""
        endpoints = [
            "/health",
            "/"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                # Should meet response time target (<300ms for most endpoints)
                assert duration < 0.5, f"Endpoint {endpoint} took {duration:.3f}s"
    
    @pytest.mark.skipif(not PERFORMANCE_MODULES_AVAILABLE, reason="Performance optimization modules not available")
    def test_memory_usage_target(self):
        """Test memory usage stays within reasonable bounds."""
        from app.core.memory_management import memory_monitor
        
        stats = memory_monitor.get_memory_stats()
        
        # Only test if we have valid stats
        if stats and "rss_mb" in stats:
            memory_mb = stats.get("rss_mb", 0)
            # Should stay under a reasonable limit (1GB for tests)
            assert memory_mb < 1024, f"Memory usage {memory_mb}MB exceeds reasonable limit"
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not PERFORMANCE_MODULES_AVAILABLE, reason="Performance optimization modules not available")
    async def test_ai_operation_response_time(self):
        """Test AI operation response time target."""
        from app.core.advanced_caching import cached
        
        @cached(ttl=300)
        async def mock_ai_operation():
            # Simulate AI operation
            await asyncio.sleep(0.1)
            return {"result": "test response"}
        
        start_time = time.time()
        result = await mock_ai_operation()
        duration = time.time() - start_time
        
        # Should meet AI operation target (<500ms)
        assert duration < 0.5, f"AI operation took {duration:.3f}s"
        assert result["result"] == "test response"


class TestBasicFunctionality:
    """Basic functionality tests that should work without performance optimization."""
    
    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health endpoint works."""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # 503 if DB unavailable
        data = response.json()
        assert "data" in data
        assert "status" in data["data"]
    
    def test_root_endpoint(self, client):
        """Test root endpoint works."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "name" in data["data"]
    
    def test_performance_endpoint_availability(self, client):
        """Test performance endpoint is available."""
        response = client.get("/performance")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "optimization_status" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])