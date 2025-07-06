# Troubleshooting Guide

## Overview

This comprehensive troubleshooting guide helps developers quickly identify and resolve common issues in the Boardroom Phase 3 platform. It covers frontend, backend, infrastructure, and integration issues with practical solutions.

## Quick Diagnostics

### System Health Check Script

```bash
#!/bin/bash
# health_check.sh - Run this first when encountering issues

echo "🔍 Boardroom System Health Check"
echo "================================"

# Check services
echo -e "\n📦 Service Status:"
curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend: Running" || echo "❌ Frontend: Not responding"
curl -s http://localhost:8000/api/v1/health > /dev/null && echo "✅ Backend: Running" || echo "❌ Backend: Not responding"
redis-cli ping > /dev/null 2>&1 && echo "✅ Redis: Running" || echo "❌ Redis: Not responding"
pg_isready > /dev/null 2>&1 && echo "✅ PostgreSQL: Running" || echo "❌ PostgreSQL: Not responding"

# Check disk space
echo -e "\n💾 Disk Space:"
df -h | grep -E "^/dev|Filesystem"

# Check memory
echo -e "\n🧠 Memory Usage:"
free -h

# Check recent errors
echo -e "\n🚨 Recent Errors (last 50 lines):"
if [ -f "logs/app.log" ]; then
    grep -i "error\|exception" logs/app.log | tail -50
else
    echo "No log file found"
fi

# Check Docker containers (if using Docker)
if command -v docker &> /dev/null; then
    echo -e "\n🐳 Docker Containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
fi
```

## Common Issues and Solutions

### Frontend Issues

#### 1. Build Failures

**Problem**: `npm run build` fails with module errors

**Symptoms**:
```bash
Module not found: Can't resolve '@/components/SomeComponent'
```

**Solutions**:
```bash
# Clear cache and reinstall
rm -rf node_modules .next
npm cache clean --force
npm install

# Check for case sensitivity issues (common on Linux)
find src -name "*.tsx" -o -name "*.ts" | xargs grep -l "SomeComponent"

# Verify tsconfig paths
cat tsconfig.json | grep -A5 "paths"
```

**Prevention**:
- Always use consistent casing in imports
- Run `npm run type-check` before committing

---

#### 2. Hydration Errors

**Problem**: "Text content does not match server-rendered HTML"

**Symptoms**:
```
Warning: Text content did not match. Server: "Loading..." Client: "Welcome, John"
```

**Solutions**:
```typescript
// Wrap dynamic content in useEffect
import { useEffect, useState } from 'react'

const UserGreeting = () => {
  const [mounted, setMounted] = useState(false)
  const [user, setUser] = useState(null)
  
  useEffect(() => {
    setMounted(true)
    setUser(getUserFromStorage())
  }, [])
  
  if (!mounted) {
    return <div>Loading...</div>
  }
  
  return <div>Welcome, {user?.name || 'Guest'}</div>
}

// Or use dynamic imports with ssr: false
import dynamic from 'next/dynamic'

const ClientOnlyComponent = dynamic(
  () => import('@/components/ClientOnlyComponent'),
  { ssr: false }
)
```

---

#### 3. State Management Issues

**Problem**: State not updating or stale closures

**Solutions**:
```typescript
// Use functional updates for state dependent on previous value
const increment = () => {
  setCount(prevCount => prevCount + 1) // ✅ Correct
  // setCount(count + 1) // ❌ May cause issues
}

// For Zustand, ensure proper subscription
const useBoardroomStore = create((set, get) => ({
  boardrooms: [],
  addBoardroom: (boardroom) => {
    set((state) => ({
      boardrooms: [...state.boardrooms, boardroom]
    }))
  },
  // Use get() to access current state in actions
  updateBoardroom: (id, updates) => {
    const current = get().boardrooms
    set({
      boardrooms: current.map(b => 
        b.id === id ? { ...b, ...updates } : b
      )
    })
  }
}))
```

---

#### 4. WebSocket Connection Issues

**Problem**: WebSocket fails to connect or disconnects frequently

**Diagnosis**:
```javascript
// Add debug logging
const ws = new WebSocket(url)

ws.onopen = () => console.log('✅ WebSocket connected')
ws.onerror = (error) => console.error('❌ WebSocket error:', error)
ws.onclose = (event) => {
  console.log(`WebSocket closed: ${event.code} - ${event.reason}`)
  // 1000: Normal closure
  // 1001: Going away
  // 1006: Abnormal closure
}
```

**Solutions**:
```typescript
// Implement robust reconnection logic
class WebSocketManager {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 1000
  
  connect(url: string) {
    try {
      this.ws = new WebSocket(url)
      this.setupEventHandlers()
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.scheduleReconnect()
    }
  }
  
  private setupEventHandlers() {
    if (!this.ws) return
    
    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
      this.reconnectDelay = 1000
    }
    
    this.ws.onclose = (event) => {
      if (event.code !== 1000) { // Not a normal closure
        this.scheduleReconnect()
      }
    }
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }
  
  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }
    
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
      30000 // Max 30 seconds
    )
    
    setTimeout(() => {
      this.reconnectAttempts++
      this.connect(this.url)
    }, delay)
  }
}
```

### Backend Issues

#### 1. Database Connection Errors

**Problem**: "connection to server on socket failed"

**Diagnosis**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check if PostgreSQL is listening
sudo netstat -plnt | grep postgres

# Test connection
psql -U postgres -h localhost -d boardroom

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

**Solutions**:
```python
# Implement connection retry logic
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import time

def create_db_engine(retries=5, delay=2):
    """Create database engine with retry logic"""
    for attempt in range(retries):
        try:
            engine = create_engine(
                DATABASE_URL,
                poolclass=NullPool,  # Disable pooling for debugging
                connect_args={
                    "connect_timeout": 10,
                    "options": "-c statement_timeout=30000"
                }
            )
            # Test connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return engine
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"Database connection failed, retrying in {delay}s: {e}")
            time.sleep(delay)
```

---

#### 2. Redis Connection Issues

**Problem**: "Connection refused" or timeout errors

**Solutions**:
```python
# Redis connection with retry and fallback
import redis
from functools import wraps
import logging

class RedisFallback:
    def __init__(self, redis_url, fallback_cache=None):
        self.redis_url = redis_url
        self.fallback_cache = fallback_cache or {}
        self._redis = None
        self._connect()
    
    def _connect(self):
        try:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            self._redis.ping()
            logging.info("Redis connected successfully")
        except Exception as e:
            logging.error(f"Redis connection failed: {e}")
            self._redis = None
    
    def get(self, key, default=None):
        if self._redis:
            try:
                return self._redis.get(key) or default
            except Exception as e:
                logging.error(f"Redis get failed: {e}")
                self._connect()  # Try to reconnect
        
        # Fallback to in-memory cache
        return self.fallback_cache.get(key, default)
    
    def set(self, key, value, ttl=None):
        # Always update fallback cache
        self.fallback_cache[key] = value
        
        if self._redis:
            try:
                if ttl:
                    return self._redis.setex(key, ttl, value)
                return self._redis.set(key, value)
            except Exception as e:
                logging.error(f"Redis set failed: {e}")
                self._connect()  # Try to reconnect
```

---

#### 3. Memory Leaks

**Problem**: Application memory usage grows over time

**Diagnosis**:
```python
# Add memory profiling
import tracemalloc
import gc
import psutil
import os

# Start tracing
tracemalloc.start()

# In your monitoring endpoint
@app.get("/api/v1/debug/memory")
async def memory_stats():
    """Get memory usage statistics"""
    # Force garbage collection
    gc.collect()
    
    # Get process memory info
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # Get top memory allocations
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    return {
        "memory_usage_mb": memory_info.rss / 1024 / 1024,
        "memory_percent": process.memory_percent(),
        "top_allocations": [
            {
                "file": stat.traceback.format()[0],
                "size_mb": stat.size / 1024 / 1024,
                "count": stat.count
            }
            for stat in top_stats[:10]
        ]
    }
```

**Solutions**:
```python
# Common memory leak fixes

# 1. Close database connections
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db():
    async with AsyncSession() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise
        finally:
            await session.close()

# 2. Limit cache size
from cachetools import LRUCache
cache = LRUCache(maxsize=1000)

# 3. Clean up background tasks
background_tasks = set()

async def create_task(coro):
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task

# 4. Use weak references for callbacks
import weakref

class EventEmitter:
    def __init__(self):
        self._handlers = {}
    
    def on(self, event, handler):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(weakref.ref(handler))
    
    def emit(self, event, *args):
        if event in self._handlers:
            # Clean up dead references
            self._handlers[event] = [
                h for h in self._handlers[event] 
                if h() is not None
            ]
            # Call handlers
            for handler_ref in self._handlers[event]:
                handler = handler_ref()
                if handler:
                    handler(*args)
```

---

#### 4. Slow API Response Times

**Problem**: API endpoints taking too long to respond

**Diagnosis**:
```python
# Add request timing middleware
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 1.0:  # 1 second threshold
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {process_time:.2f}s"
        )
    
    return response
```

**Solutions**:
```python
# 1. Add database query optimization
from sqlalchemy.orm import selectinload, joinedload

# Bad: N+1 query problem
boardrooms = await db.execute(select(Boardroom))
for boardroom in boardrooms:
    members = await db.execute(
        select(User).where(User.boardroom_id == boardroom.id)
    )

# Good: Eager loading
boardrooms = await db.execute(
    select(Boardroom).options(selectinload(Boardroom.members))
)

# 2. Implement caching
from functools import lru_cache
from cachetools import TTLCache
import asyncio

# In-memory cache with TTL
cache = TTLCache(maxsize=100, ttl=300)

async def get_boardroom_cached(boardroom_id: str):
    if boardroom_id in cache:
        return cache[boardroom_id]
    
    boardroom = await get_boardroom_from_db(boardroom_id)
    cache[boardroom_id] = boardroom
    return boardroom

# 3. Use connection pooling
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Verify connections before use
)

# 4. Implement pagination
from fastapi import Query

@app.get("/api/v1/boardrooms")
async def list_boardrooms(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    query = select(Boardroom).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
```

### Infrastructure Issues

#### 1. Docker Container Crashes

**Problem**: Containers keep restarting

**Diagnosis**:
```bash
# Check container logs
docker logs boardroom-backend --tail 100

# Check container resource usage
docker stats

# Inspect container
docker inspect boardroom-backend | jq '.[0].State'

# Check events
docker events --since 10m --filter container=boardroom-backend
```

**Solutions**:
```yaml
# docker-compose.yml - Add resource limits and health checks
services:
  backend:
    image: boardroom/backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - PYTHONUNBUFFERED=1  # See Python output in logs
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

#### 2. Nginx 502 Bad Gateway

**Problem**: Nginx returns 502 errors

**Solutions**:
```nginx
# nginx.conf - Fix common 502 causes

upstream backend {
    server backend:8000 max_fails=3 fail_timeout=30s;
    server backend-2:8000 max_fails=3 fail_timeout=30s backup;
    keepalive 32;  # Keep connections alive
}

server {
    location /api {
        proxy_pass http://backend;
        
        # Increase timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Increase buffer sizes
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # Error handling
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_next_upstream_tries 2;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    # Custom error page
    error_page 502 /502.html;
    location = /502.html {
        root /usr/share/nginx/html;
        internal;
    }
}
```

---

#### 3. SSL Certificate Issues

**Problem**: SSL certificate errors or warnings

**Solutions**:
```bash
# Check certificate expiration
echo | openssl s_client -connect boardroom.com:443 2>/dev/null | openssl x509 -noout -dates

# Renew Let's Encrypt certificate
certbot renew --dry-run  # Test first
certbot renew

# Debug SSL issues
openssl s_client -connect boardroom.com:443 -servername boardroom.com < /dev/null

# Check certificate chain
openssl s_client -connect boardroom.com:443 -showcerts < /dev/null
```

### Performance Issues

#### 1. Slow Page Load Times

**Diagnosis**:
```javascript
// Add performance monitoring
if (typeof window !== 'undefined') {
  window.addEventListener('load', () => {
    const perfData = performance.getEntriesByType('navigation')[0]
    console.table({
      'DNS Lookup': perfData.domainLookupEnd - perfData.domainLookupStart,
      'TCP Connection': perfData.connectEnd - perfData.connectStart,
      'Request Time': perfData.responseStart - perfData.requestStart,
      'Response Time': perfData.responseEnd - perfData.responseStart,
      'DOM Processing': perfData.domComplete - perfData.domLoading,
      'Total Load Time': perfData.loadEventEnd - perfData.fetchStart
    })
  })
}
```

**Solutions**:
```javascript
// 1. Implement code splitting
const DynamicComponent = dynamic(
  () => import('../components/HeavyComponent'),
  {
    loading: () => <Skeleton />,
    ssr: false
  }
)

// 2. Optimize images
import Image from 'next/image'

<Image
  src="/hero.jpg"
  alt="Hero"
  width={1200}
  height={600}
  priority={true}  // For above-the-fold images
  placeholder="blur"
  blurDataURL={blurDataUrl}
/>

// 3. Prefetch critical data
export async function getStaticProps() {
  // Fetch data at build time
  const data = await fetchCriticalData()
  
  return {
    props: { data },
    revalidate: 3600  // Revalidate every hour
  }
}

// 4. Use React.memo for expensive components
const ExpensiveComponent = React.memo(({ data }) => {
  // Component logic
}, (prevProps, nextProps) => {
  // Custom comparison function
  return prevProps.data.id === nextProps.data.id
})
```

---

#### 2. High Memory Usage in Browser

**Solutions**:
```javascript
// 1. Clean up event listeners
useEffect(() => {
  const handleScroll = () => { /* ... */ }
  window.addEventListener('scroll', handleScroll)
  
  return () => {
    window.removeEventListener('scroll', handleScroll)
  }
}, [])

// 2. Virtualize long lists
import { VariableSizeList } from 'react-window'

const VirtualList = ({ items }) => (
  <VariableSizeList
    height={600}
    itemCount={items.length}
    itemSize={() => 50}
    width="100%"
  >
    {({ index, style }) => (
      <div style={style}>
        {items[index].name}
      </div>
    )}
  </VariableSizeList>
)

// 3. Debounce expensive operations
import { debounce } from 'lodash'

const expensiveOperation = debounce((value) => {
  // Expensive computation
}, 300)

// 4. Clear refs on unmount
const imageRef = useRef(null)

useEffect(() => {
  return () => {
    if (imageRef.current) {
      imageRef.current.src = ''  // Clear image
      imageRef.current = null
    }
  }
}, [])
```

## Debugging Tools and Techniques

### Frontend Debugging

```javascript
// 1. React Developer Tools
// Install browser extension and use profiler

// 2. Add debug logging
const DEBUG = process.env.NODE_ENV === 'development'

export const debug = (...args) => {
  if (DEBUG) {
    console.log('[DEBUG]', new Date().toISOString(), ...args)
  }
}

// 3. Performance profiling
const ProfiledComponent = () => {
  useEffect(() => {
    if (DEBUG) {
      performance.mark('component-start')
      
      return () => {
        performance.mark('component-end')
        performance.measure(
          'component-render',
          'component-start',
          'component-end'
        )
        
        const measure = performance.getEntriesByName('component-render')[0]
        console.log(`Component rendered in ${measure.duration}ms`)
      }
    }
  }, [])
  
  return <div>Content</div>
}

// 4. Network request debugging
if (DEBUG) {
  // Log all fetch requests
  const originalFetch = window.fetch
  window.fetch = async (...args) => {
    console.log('Fetch:', args)
    const response = await originalFetch(...args)
    console.log('Response:', response.status, response.statusText)
    return response
  }
}
```

### Backend Debugging

```python
# 1. Enable SQL query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# 2. Add debug endpoints
if settings.DEBUG:
    @app.get("/api/v1/debug/routes")
    async def debug_routes():
        """List all registered routes"""
        routes = []
        for route in app.routes:
            routes.append({
                "path": route.path,
                "methods": route.methods,
                "name": route.name
            })
        return routes
    
    @app.get("/api/v1/debug/config")
    async def debug_config():
        """Show configuration (sanitized)"""
        config = settings.dict()
        # Remove sensitive data
        for key in ['secret_key', 'database_url', 'jwt_secret']:
            if key in config:
                config[key] = "***HIDDEN***"
        return config

# 3. Request ID tracking
import uuid
from contextvars import ContextVar

request_id_var = ContextVar('request_id', default=None)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# 4. Detailed error logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = request_id_var.get()
    logger.error(
        f"Unhandled exception in request {request_id}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id
        }
    )
```

## Monitoring and Alerting

### Setting Up Monitoring

```yaml
# prometheus/alerts.yml
groups:
  - name: boardroom_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"
      
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response times"
          description: "95th percentile response time is {{ $value }} seconds"
      
      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes / 1024 / 1024 > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Process using {{ $value }}MB of memory"
```

### Log Aggregation

```python
# Structured logging setup
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage
logger.info(
    "user_action",
    user_id=user.id,
    action="create_boardroom",
    boardroom_id=boardroom.id,
    duration=time.time() - start_time
)
```

## Emergency Procedures

### When Everything is Down

```bash
#!/bin/bash
# emergency_recovery.sh

echo "🚨 Emergency Recovery Procedure"

# 1. Check system resources
echo "Checking system resources..."
df -h
free -h
ps aux --sort=-%cpu | head -10

# 2. Restart services in order
echo "Restarting services..."
docker-compose down
docker system prune -f  # Clean up
docker-compose up -d db redis  # Start data services first
sleep 10
docker-compose up -d backend  # Then backend
sleep 10
docker-compose up -d frontend nginx  # Finally frontend

# 3. Verify services
echo "Verifying services..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null; then
        echo "✅ Backend is up"
        break
    fi
    echo "Waiting for backend... ($i/30)"
    sleep 2
done

# 4. Clear caches if needed
echo "Clear Redis cache? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
    redis-cli FLUSHALL
fi

# 5. Run diagnostics
./health_check.sh
```

## Best Practices for Avoiding Issues

### Development Practices

1. **Always run tests before committing**
   ```bash
   npm test
   npm run lint
   npm run type-check
   ```

2. **Use proper error handling**
   ```typescript
   try {
     await riskyOperation()
   } catch (error) {
     logger.error('Operation failed', { error, context })
     // Handle gracefully
   }
   ```

3. **Monitor resource usage during development**
   ```bash
   # Watch memory usage
   watch -n 1 'ps aux | grep node'
   
   # Monitor file descriptors
   lsof -p $(pgrep node) | wc -l
   ```

4. **Use feature flags for risky changes**
   ```typescript
   if (featureFlags.isEnabled('new-feature')) {
     // New code
   } else {
     // Stable code
   }
   ```

### Deployment Practices

1. **Always backup before deployment**
2. **Deploy during low-traffic periods**
3. **Have rollback plan ready**
4. **Monitor closely after deployment**
5. **Use gradual rollout strategies**

---

Remember: The best debugging tool is good logging. When in doubt, add more logs (but clean them up later)!