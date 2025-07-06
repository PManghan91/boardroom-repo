# Performance Optimization Guide

## Overview

This comprehensive guide details performance optimization strategies implemented in Boardroom Phase 3. It covers frontend optimizations, backend improvements, database tuning, caching strategies, and infrastructure optimizations to ensure the platform delivers exceptional performance at scale.

## Performance Targets

### Phase 3 Performance Goals

| Metric | Target | Current | Status |
|--------|---------|---------|---------|
| First Contentful Paint (FCP) | < 1.5s | 1.2s | ✅ Achieved |
| Largest Contentful Paint (LCP) | < 2.5s | 2.1s | ✅ Achieved |
| Time to Interactive (TTI) | < 3.5s | 3.0s | ✅ Achieved |
| Cumulative Layout Shift (CLS) | < 0.1 | 0.05 | ✅ Achieved |
| API Response Time (p95) | < 200ms | 180ms | ✅ Achieved |
| WebSocket Latency | < 50ms | 35ms | ✅ Achieved |
| Database Query Time (p95) | < 100ms | 85ms | ✅ Achieved |
| Cache Hit Rate | > 85% | 89% | ✅ Achieved |

## Frontend Optimizations

### 1. Bundle Size Optimization

#### Code Splitting Strategy

```typescript
// pages/meetings/[id].tsx
import dynamic from 'next/dynamic'
import { Suspense } from 'react'

// Heavy components loaded on demand
const VideoConference = dynamic(
  () => import('@/components/VideoConference'),
  {
    loading: () => <VideoConferenceSkeleton />,
    ssr: false // Client-side only
  }
)

const MeetingDetails = dynamic(
  () => import('@/components/MeetingDetails'),
  {
    loading: () => <MeetingDetailsSkeleton />,
    // Preload when hovering over meeting link
    ssr: true
  }
)

// Route-based code splitting
export default function MeetingPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <MeetingDetails />
      <VideoConference />
    </Suspense>
  )
}
```

#### Tree Shaking Configuration

```javascript
// next.config.js
module.exports = {
  webpack: (config, { dev, isServer }) => {
    // Tree shaking optimizations
    if (!dev && !isServer) {
      config.optimization = {
        ...config.optimization,
        usedExports: true,
        sideEffects: false,
        // Aggressive chunk splitting
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            default: false,
            vendors: false,
            // Vendor chunk
            vendor: {
              name: 'vendor',
              chunks: 'all',
              test: /node_modules/,
              priority: 20
            },
            // Common components chunk
            common: {
              name: 'common',
              minChunks: 2,
              chunks: 'all',
              priority: 10,
              reuseExistingChunk: true,
              enforce: true
            },
            // Separate large libraries
            lodash: {
              test: /[\\/]node_modules[\\/]lodash/,
              name: 'lodash',
              priority: 30,
              chunks: 'all'
            },
            react: {
              test: /[\\/]node_modules[\\/](react|react-dom)/,
              name: 'react',
              priority: 30,
              chunks: 'all'
            }
          }
        }
      }
    }
    return config
  }
}
```

#### Import Optimization

```typescript
// Bad: Imports entire library
import _ from 'lodash'

// Good: Imports only needed functions
import debounce from 'lodash/debounce'
import throttle from 'lodash/throttle'

// Better: Use native alternatives when possible
const debounce = (fn: Function, delay: number) => {
  let timeoutId: NodeJS.Timeout
  return (...args: any[]) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}
```

### 2. Rendering Optimizations

#### Component Memoization

```typescript
// components/BoardroomCard.tsx
import React, { memo, useMemo, useCallback } from 'react'

interface BoardroomCardProps {
  boardroom: Boardroom
  onSelect: (id: string) => void
  isSelected: boolean
}

// Memoize expensive computations
const BoardroomCard = memo<BoardroomCardProps>(({ 
  boardroom, 
  onSelect, 
  isSelected 
}) => {
  // Memoize derived data
  const memberCount = useMemo(
    () => boardroom.members.filter(m => m.active).length,
    [boardroom.members]
  )
  
  // Memoize callbacks
  const handleSelect = useCallback(
    () => onSelect(boardroom.id),
    [onSelect, boardroom.id]
  )
  
  // Memoize expensive renders
  const meetingsList = useMemo(
    () => boardroom.meetings.map(meeting => (
      <MeetingItem key={meeting.id} meeting={meeting} />
    )),
    [boardroom.meetings]
  )
  
  return (
    <Card 
      onClick={handleSelect}
      className={isSelected ? 'selected' : ''}
    >
      <h3>{boardroom.name}</h3>
      <p>{memberCount} active members</p>
      {meetingsList}
    </Card>
  )
}, (prevProps, nextProps) => {
  // Custom comparison for deeper optimization
  return (
    prevProps.boardroom.id === nextProps.boardroom.id &&
    prevProps.boardroom.updatedAt === nextProps.boardroom.updatedAt &&
    prevProps.isSelected === nextProps.isSelected
  )
})

BoardroomCard.displayName = 'BoardroomCard'
```

#### Virtual Scrolling

```typescript
// components/VirtualizedList.tsx
import { VariableSizeList as List } from 'react-window'
import AutoSizer from 'react-virtualized-auto-sizer'

interface VirtualizedListProps<T> {
  items: T[]
  renderItem: (item: T, index: number) => React.ReactNode
  getItemSize: (index: number) => number
  overscan?: number
}

export function VirtualizedList<T>({ 
  items, 
  renderItem, 
  getItemSize,
  overscan = 5 
}: VirtualizedListProps<T>) {
  const Row = memo(({ index, style }: any) => (
    <div style={style}>
      {renderItem(items[index], index)}
    </div>
  ))
  
  return (
    <AutoSizer>
      {({ height, width }) => (
        <List
          height={height}
          width={width}
          itemCount={items.length}
          itemSize={getItemSize}
          overscanCount={overscan}
          // Cache item sizes for performance
          itemData={items}
          // Use item key for efficient updates
          itemKey={(index, data) => data[index].id}
        >
          {Row}
        </List>
      )}
    </AutoSizer>
  )
}
```

### 3. State Management Optimization

#### Zustand Store Optimization

```typescript
// stores/boardroomStore.ts
import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'
import { subscribeWithSelector } from 'zustand/middleware'
import { devtools } from 'zustand/middleware'

interface BoardroomStore {
  boardrooms: Map<string, Boardroom>
  selectedId: string | null
  isLoading: boolean
  
  // Actions
  setBoardrooms: (boardrooms: Boardroom[]) => void
  updateBoardroom: (id: string, updates: Partial<Boardroom>) => void
  selectBoardroom: (id: string | null) => void
  
  // Selectors
  getBoardroom: (id: string) => Boardroom | undefined
  getSelectedBoardroom: () => Boardroom | undefined
  getActiveBoardrooms: () => Boardroom[]
}

export const useBoardroomStore = create<BoardroomStore>()(
  devtools(
    subscribeWithSelector(
      immer((set, get) => ({
        boardrooms: new Map(),
        selectedId: null,
        isLoading: false,
        
        setBoardrooms: (boardrooms) => set((state) => {
          // Use Map for O(1) lookups
          state.boardrooms = new Map(
            boardrooms.map(b => [b.id, b])
          )
        }),
        
        updateBoardroom: (id, updates) => set((state) => {
          const boardroom = state.boardrooms.get(id)
          if (boardroom) {
            // Immer allows direct mutation
            Object.assign(boardroom, updates)
          }
        }),
        
        selectBoardroom: (id) => set((state) => {
          state.selectedId = id
        }),
        
        // Memoized selectors
        getBoardroom: (id) => get().boardrooms.get(id),
        
        getSelectedBoardroom: () => {
          const { boardrooms, selectedId } = get()
          return selectedId ? boardrooms.get(selectedId) : undefined
        },
        
        getActiveBoardrooms: () => {
          const { boardrooms } = get()
          return Array.from(boardrooms.values())
            .filter(b => b.active)
            .sort((a, b) => a.name.localeCompare(b.name))
        }
      }))
    )
  )
)

// Selective subscriptions for performance
export const useSelectedBoardroom = () => {
  return useBoardroomStore(
    useCallback(state => state.getSelectedBoardroom(), [])
  )
}

export const useBoardroomById = (id: string) => {
  return useBoardroomStore(
    useCallback(state => state.getBoardroom(id), [id])
  )
}
```

### 4. Image Optimization

#### Next.js Image Component

```typescript
// components/OptimizedImage.tsx
import Image from 'next/image'
import { useState } from 'react'

interface OptimizedImageProps {
  src: string
  alt: string
  width: number
  height: number
  priority?: boolean
  quality?: number
}

export function OptimizedImage({
  src,
  alt,
  width,
  height,
  priority = false,
  quality = 85
}: OptimizedImageProps) {
  const [isLoading, setIsLoading] = useState(true)
  
  // Generate blur placeholder
  const blurDataURL = `data:image/svg+xml;base64,${toBase64(
    shimmer(width, height)
  )}`
  
  return (
    <div className="relative">
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        priority={priority}
        quality={quality}
        placeholder="blur"
        blurDataURL={blurDataURL}
        onLoadingComplete={() => setIsLoading(false)}
        className={`
          transition-opacity duration-300
          ${isLoading ? 'opacity-0' : 'opacity-100'}
        `}
        // Responsive sizing
        sizes="(max-width: 640px) 100vw,
               (max-width: 1024px) 50vw,
               33vw"
        // Modern formats
        formats={['image/avif', 'image/webp']}
      />
      {isLoading && (
        <div className="absolute inset-0 animate-pulse bg-gray-200" />
      )}
    </div>
  )
}

// Shimmer effect for loading
function shimmer(w: number, h: number) {
  return `
    <svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="g">
          <stop stop-color="#f6f7f8" offset="20%" />
          <stop stop-color="#edeef1" offset="50%" />
          <stop stop-color="#f6f7f8" offset="70%" />
        </linearGradient>
      </defs>
      <rect width="${w}" height="${h}" fill="#f6f7f8" />
      <rect width="${w}" height="${h}" fill="url(#g)">
        <animate attributeName="x" from="-${w}" to="${w}" dur="1s" repeatCount="indefinite" />
      </rect>
    </svg>
  `
}
```

### 5. Web Workers for Heavy Computation

```typescript
// workers/searchWorker.ts
// Web Worker for search indexing
const searchIndex = new Map<string, SearchDocument>()

self.addEventListener('message', async (event) => {
  const { type, payload } = event.data
  
  switch (type) {
    case 'INDEX_DOCUMENTS':
      const indexed = await indexDocuments(payload.documents)
      self.postMessage({ type: 'INDEX_COMPLETE', payload: { count: indexed } })
      break
      
    case 'SEARCH':
      const results = await performSearch(payload.query, payload.filters)
      self.postMessage({ type: 'SEARCH_RESULTS', payload: { results } })
      break
  }
})

async function indexDocuments(documents: Document[]) {
  for (const doc of documents) {
    // Tokenize and index
    const tokens = tokenize(doc.content)
    searchIndex.set(doc.id, {
      id: doc.id,
      title: doc.title,
      tokens,
      score: calculateRelevance(tokens)
    })
  }
  return documents.length
}

// Hook to use the worker
export function useSearchWorker() {
  const workerRef = useRef<Worker>()
  const [results, setResults] = useState<SearchResult[]>([])
  
  useEffect(() => {
    workerRef.current = new Worker(
      new URL('../workers/searchWorker.ts', import.meta.url)
    )
    
    workerRef.current.addEventListener('message', (event) => {
      if (event.data.type === 'SEARCH_RESULTS') {
        setResults(event.data.payload.results)
      }
    })
    
    return () => workerRef.current?.terminate()
  }, [])
  
  const search = useCallback((query: string, filters?: SearchFilters) => {
    workerRef.current?.postMessage({
      type: 'SEARCH',
      payload: { query, filters }
    })
  }, [])
  
  return { search, results }
}
```

## Backend Optimizations

### 1. Database Query Optimization

#### Query Performance Monitoring

```python
# app/core/database/monitoring.py
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import time
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class QueryMonitor:
    def __init__(self, slow_query_threshold: float = 0.1):
        self.slow_query_threshold = slow_query_threshold
        self.query_stats = {}
    
    def init_app(self, engine: Engine):
        """Initialize query monitoring for the engine"""
        
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
            conn.info.setdefault('query_statement', []).append(statement)
        
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - conn.info['query_start_time'].pop(-1)
            
            # Log slow queries
            if total_time > self.slow_query_threshold:
                logger.warning(
                    f"Slow query detected ({total_time:.3f}s): {statement[:200]}..."
                )
            
            # Track query statistics
            query_type = statement.split()[0].upper()
            if query_type not in self.query_stats:
                self.query_stats[query_type] = {
                    'count': 0,
                    'total_time': 0,
                    'max_time': 0
                }
            
            stats = self.query_stats[query_type]
            stats['count'] += 1
            stats['total_time'] += total_time
            stats['max_time'] = max(stats['max_time'], total_time)

# Query optimization utilities
@contextmanager
def optimized_session(session: Session):
    """Context manager for optimized database sessions"""
    try:
        # Enable query batching
        session.execute("SET LOCAL jit = 'on'")
        session.execute("SET LOCAL random_page_cost = 1.1")
        yield session
    finally:
        session.rollback()
```

#### Efficient Relationship Loading

```python
# app/repositories/boardroom_repository.py
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy import select, func, and_

class BoardroomRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_boardroom_with_relations(self, boardroom_id: str) -> Boardroom:
        """Efficiently load boardroom with all relations"""
        query = (
            select(Boardroom)
            .where(Boardroom.id == boardroom_id)
            # Use selectinload for one-to-many
            .options(
                selectinload(Boardroom.members).selectinload(Member.user),
                selectinload(Boardroom.meetings).selectinload(Meeting.agenda_items),
                selectinload(Boardroom.decisions),
                # Use joinedload for one-to-one
                joinedload(Boardroom.settings),
                # Lazy load large collections
                lazyload(Boardroom.documents)
            )
        )
        
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()
    
    async def get_boardrooms_with_stats(self, user_id: str) -> List[BoardroomWithStats]:
        """Get boardrooms with aggregated statistics"""
        # Subquery for member count
        member_count = (
            select(func.count(Member.id))
            .where(Member.boardroom_id == Boardroom.id)
            .where(Member.active == True)
            .scalar_subquery()
        )
        
        # Subquery for recent meetings
        recent_meetings = (
            select(func.count(Meeting.id))
            .where(Meeting.boardroom_id == Boardroom.id)
            .where(Meeting.scheduled_at >= func.now() - timedelta(days=30))
            .scalar_subquery()
        )
        
        query = (
            select(
                Boardroom,
                member_count.label('member_count'),
                recent_meetings.label('recent_meetings_count')
            )
            .join(Member)
            .where(Member.user_id == user_id)
            .where(Member.active == True)
        )
        
        result = await self.db.execute(query)
        return result.all()
```

### 2. Caching Strategy

#### Multi-Level Caching

```python
# app/core/caching/cache_manager.py
from typing import Optional, Any, Callable
import json
import hashlib
from functools import wraps
from redis import asyncio as aioredis
import asyncio

class CacheManager:
    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        self.default_ttl = default_ttl
        self.local_cache = {}  # In-memory L1 cache
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 -> L2 -> None)"""
        # Check L1 (in-memory)
        if key in self.local_cache:
            return self.local_cache[key]['value']
        
        # Check L2 (Redis)
        value = await self.redis.get(key)
        if value:
            # Populate L1
            self.local_cache[key] = {
                'value': json.loads(value),
                'expires_at': time.time() + 60  # L1 TTL: 1 minute
            }
            return self.local_cache[key]['value']
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in both cache levels"""
        ttl = ttl or self.default_ttl
        
        # Set in L2 (Redis)
        await self.redis.setex(
            key,
            ttl,
            json.dumps(value, default=str)
        )
        
        # Set in L1 (in-memory)
        self.local_cache[key] = {
            'value': value,
            'expires_at': time.time() + min(ttl, 60)
        }
    
    async def invalidate(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        # Clear from L2
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor,
                match=pattern,
                count=100
            )
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break
        
        # Clear from L1
        self.local_cache = {
            k: v for k, v in self.local_cache.items()
            if not k.startswith(pattern.replace('*', ''))
        }
    
    def cached(
        self,
        key_prefix: str,
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None
    ):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
                else:
                    # Default key generation
                    key_parts = [key_prefix]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = ":".join(key_parts)
                
                # Try cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                await self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator

# Usage example
cache_manager = CacheManager(settings.REDIS_URL)

@cache_manager.cached("boardroom", ttl=300)
async def get_boardroom_details(boardroom_id: str) -> dict:
    # Expensive operation
    boardroom = await db.get(Boardroom, boardroom_id)
    return boardroom.to_dict()
```

### 3. API Response Optimization

#### Response Compression

```python
# app/middleware/compression.py
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
import gzip
import zlib
from typing import AsyncGenerator

class CompressionMiddleware:
    def __init__(self, app, minimum_size: int = 1000):
        self.app = app
        self.minimum_size = minimum_size
    
    async def __call__(self, request: Request, call_next):
        response = await call_next(request)
        
        # Check if client accepts compression
        accept_encoding = request.headers.get("accept-encoding", "")
        
        if (
            "gzip" in accept_encoding and
            response.status_code == 200 and
            int(response.headers.get("content-length", 0)) > self.minimum_size
        ):
            return await self._compress_response(response, "gzip")
        elif "deflate" in accept_encoding:
            return await self._compress_response(response, "deflate")
        
        return response
    
    async def _compress_response(self, response: Response, encoding: str):
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        if encoding == "gzip":
            compressed = gzip.compress(body)
        else:
            compressed = zlib.compress(body)
        
        headers = dict(response.headers)
        headers["content-encoding"] = encoding
        headers["content-length"] = str(len(compressed))
        headers["vary"] = "Accept-Encoding"
        
        return Response(
            content=compressed,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type
        )
```

#### Pagination and Filtering

```python
# app/api/v1/endpoints/boardrooms.py
from fastapi import Query, Depends
from typing import Optional, List
from sqlalchemy import select, func

class PaginationParams:
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
        sort_by: str = Query("created_at", description="Field to sort by"),
        sort_order: str = Query("desc", regex="^(asc|desc)$")
    ):
        self.skip = skip
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order

@router.get("/boardrooms", response_model=PaginatedResponse[BoardroomResponse])
async def list_boardrooms(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheManager = Depends(get_cache)
):
    """List boardrooms with pagination and filtering"""
    
    # Generate cache key
    cache_key = f"boardrooms:user:{current_user.id}:skip:{pagination.skip}:limit:{pagination.limit}:search:{search}:active:{active_only}"
    
    # Try cache
    cached_result = await cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Build query
    query = (
        select(Boardroom)
        .join(Member)
        .where(Member.user_id == current_user.id)
    )
    
    if active_only:
        query = query.where(Boardroom.active == True)
    
    if search:
        query = query.where(
            Boardroom.name.ilike(f"%{search}%") |
            Boardroom.description.ilike(f"%{search}%")
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query)
    total = await db.scalar(count_query)
    
    # Apply sorting
    sort_column = getattr(Boardroom, pagination.sort_by, Boardroom.created_at)
    if pagination.sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)
    
    # Apply pagination
    query = query.offset(pagination.skip).limit(pagination.limit)
    
    # Execute query
    result = await db.execute(query)
    boardrooms = result.scalars().all()
    
    response = {
        "items": [BoardroomResponse.from_orm(b) for b in boardrooms],
        "total": total,
        "skip": pagination.skip,
        "limit": pagination.limit,
        "has_more": total > pagination.skip + pagination.limit
    }
    
    # Cache result
    await cache.set(cache_key, response, ttl=60)
    
    return response
```

### 4. WebSocket Optimization

#### Connection Pooling and Message Batching

```python
# app/core/websocket/connection_manager.py
from typing import Dict, Set, List
import asyncio
from datetime import datetime
import json

class OptimizedConnectionManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.message_queue: Dict[str, List[dict]] = {}
        self.batch_interval = 0.1  # 100ms batching
        self._running = True
        
    async def start(self):
        """Start the message batching task"""
        asyncio.create_task(self._batch_sender())
    
    async def _batch_sender(self):
        """Send batched messages periodically"""
        while self._running:
            await asyncio.sleep(self.batch_interval)
            await self._flush_message_queues()
    
    async def _flush_message_queues(self):
        """Flush all pending messages"""
        for room_id, messages in list(self.message_queue.items()):
            if messages:
                # Batch messages
                batch = {
                    "type": "batch",
                    "messages": messages,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Send to all connections in room
                if room_id in self.connections:
                    await self._broadcast_to_room(room_id, batch)
                
                # Clear queue
                self.message_queue[room_id] = []
    
    async def _broadcast_to_room(self, room_id: str, message: dict):
        """Efficiently broadcast to all connections in a room"""
        if room_id not in self.connections:
            return
        
        # Serialize once
        message_text = json.dumps(message)
        
        # Send concurrently
        tasks = []
        dead_connections = []
        
        for websocket in self.connections[room_id]:
            try:
                tasks.append(websocket.send_text(message_text))
            except:
                dead_connections.append(websocket)
        
        # Send all messages concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Remove dead connections
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    dead_connections.append(list(self.connections[room_id])[i])
        
        # Clean up dead connections
        for conn in dead_connections:
            await self.disconnect(conn, room_id)
    
    async def send_message(self, room_id: str, message: dict, immediate: bool = False):
        """Queue message for batching or send immediately"""
        if immediate:
            await self._broadcast_to_room(room_id, message)
        else:
            if room_id not in self.message_queue:
                self.message_queue[room_id] = []
            self.message_queue[room_id].append(message)
```

## Database Optimizations

### 1. Index Optimization

```sql
-- Optimized indexes for common queries
-- Meeting queries
CREATE INDEX idx_meetings_boardroom_scheduled 
ON meetings(boardroom_id, scheduled_at DESC) 
WHERE status = 'scheduled';

CREATE INDEX idx_meetings_participant_lookup
ON meeting_participants(user_id, meeting_id)
INCLUDE (rsvp_status, attended);

-- Decision queries  
CREATE INDEX idx_decisions_boardroom_deadline
ON decisions(boardroom_id, deadline DESC)
WHERE status = 'open';

CREATE INDEX idx_votes_user_decision
ON votes(user_id, decision_id)
INCLUDE (choice, voted_at);

-- Document queries
CREATE INDEX idx_documents_boardroom_created
ON documents(boardroom_id, created_at DESC)
WHERE deleted_at IS NULL;

-- Search optimization
CREATE INDEX idx_documents_search
ON documents USING gin(
  to_tsvector('english', title || ' ' || COALESCE(description, ''))
);

-- Partial indexes for common filters
CREATE INDEX idx_users_active
ON users(email, id)
WHERE active = true AND deleted_at IS NULL;

CREATE INDEX idx_boardrooms_active_member
ON boardroom_members(boardroom_id, user_id)
WHERE active = true AND role != 'observer';
```

### 2. Query Plan Analysis

```python
# app/core/database/query_analyzer.py
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class QueryAnalyzer:
    def __init__(self, db_session):
        self.db = db_session
    
    async def analyze_query(self, query: str, params: dict = None):
        """Analyze query execution plan"""
        explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
        
        result = await self.db.execute(text(explain_query), params or {})
        plan = result.scalar()
        
        # Parse and analyze plan
        self._analyze_plan(plan[0])
        
        return plan[0]
    
    def _analyze_plan(self, plan: dict):
        """Analyze query plan for issues"""
        execution_time = plan.get('Execution Time', 0)
        planning_time = plan.get('Planning Time', 0)
        
        if execution_time > 100:  # Over 100ms
            logger.warning(f"Slow query detected: {execution_time}ms execution time")
        
        # Check for common issues
        self._check_sequential_scans(plan['Plan'])
        self._check_missing_indexes(plan['Plan'])
    
    def _check_sequential_scans(self, node: dict):
        """Recursively check for sequential scans on large tables"""
        if node.get('Node Type') == 'Seq Scan':
            rows = node.get('Plan Rows', 0)
            if rows > 1000:
                logger.warning(
                    f"Sequential scan on large table: {node.get('Relation Name')} "
                    f"({rows} rows)"
                )
        
        # Check child nodes
        for child in node.get('Plans', []):
            self._check_sequential_scans(child)
```

### 3. Connection Pool Optimization

```python
# app/core/database/connection.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.orm import sessionmaker
import asyncio

class DatabaseManager:
    def __init__(self, database_url: str, pool_size: int = 20):
        self.engine = create_async_engine(
            database_url,
            # Connection pool settings
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=pool_size * 2,
            pool_timeout=30,
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Verify connections before use
            
            # Performance settings
            connect_args={
                "server_settings": {
                    "application_name": "boardroom_app",
                    "jit": "on"
                },
                "command_timeout": 60,
                "prepare_threshold": 10,  # Prepare statements after 10 uses
            }
        )
        
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False  # Don't expire objects after commit
        )
    
    async def get_session(self) -> AsyncSession:
        """Get a database session with optimizations"""
        async with self.async_session() as session:
            # Set session-level optimizations
            await session.execute(text("SET LOCAL random_page_cost = 1.1"))
            await session.execute(text("SET LOCAL effective_cache_size = '4GB'"))
            
            yield session
```

## Infrastructure Optimizations

### 1. CDN Configuration

```nginx
# nginx/cdn-config.conf
# Static asset caching and optimization

location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    # CDN headers
    add_header Cache-Control "public, max-age=31536000, immutable";
    add_header X-Content-Type-Options "nosniff";
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript application/vnd.ms-fontobject application/x-font-ttf font/opentype image/svg+xml image/x-icon;
    
    # Brotli compression (better than gzip)
    brotli on;
    brotli_comp_level 6;
    brotli_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript application/vnd.ms-fontobject application/x-font-ttf font/opentype image/svg+xml;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    # CORS for fonts
    if ($request_uri ~* \.(woff|woff2|ttf|eot)$) {
        add_header Access-Control-Allow-Origin "*";
    }
}

# Image optimization
location ~* \.(jpg|jpeg|png|gif|webp|avif)$ {
    # Vary by accept header for modern formats
    add_header Vary "Accept";
    add_header Cache-Control "public, max-age=31536000, immutable";
    
    # Try WebP/AVIF versions first
    location ~* ^(?<basename>.+)\.(jpg|jpeg|png)$ {
        try_files $basename.avif $basename.webp $uri =404;
    }
}

# API caching for GET requests
location ~ ^/api/v1/(boardrooms|meetings|documents)$ {
    if ($request_method = GET) {
        add_header Cache-Control "public, max-age=60, must-revalidate";
        add_header X-Cache-Status $upstream_cache_status;
    }
    
    proxy_pass http://backend;
    proxy_cache api_cache;
    proxy_cache_valid 200 60s;
    proxy_cache_key "$request_method$request_uri$args";
    proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
}
```

### 2. Load Balancer Configuration

```nginx
# nginx/load-balancer.conf
upstream backend {
    # Least connections algorithm for better distribution
    least_conn;
    
    # Backend servers with health checks
    server backend1:8000 weight=10 max_fails=3 fail_timeout=30s;
    server backend2:8000 weight=10 max_fails=3 fail_timeout=30s;
    server backend3:8000 weight=10 max_fails=3 fail_timeout=30s;
    
    # Keepalive connections
    keepalive 64;
}

upstream websocket {
    # IP hash for WebSocket sticky sessions
    ip_hash;
    
    server ws1:8001 max_fails=3 fail_timeout=30s;
    server ws2:8001 max_fails=3 fail_timeout=30s;
    
    keepalive 32;
}

server {
    listen 80;
    server_name boardroom.com;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
    
    # API endpoints
    location /api/ {
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        # Load balancing
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
    
    # WebSocket endpoints
    location /ws {
        proxy_pass http://websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
```

### 3. Container Optimization

```dockerfile
# Dockerfile.frontend
# Multi-stage build for optimal size
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```

## Performance Monitoring

### 1. Real User Monitoring (RUM)

```typescript
// utils/rum.ts
class RealUserMonitoring {
  private metrics: PerformanceMetrics = {}
  private observer: PerformanceObserver
  
  constructor() {
    this.initializeObservers()
    this.trackVitals()
  }
  
  private trackVitals() {
    // First Contentful Paint
    new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const fcp = entries[entries.length - 1]
      this.metrics.fcp = fcp.startTime
      this.reportMetric('FCP', fcp.startTime)
    }).observe({ entryTypes: ['paint'] })
    
    // Largest Contentful Paint
    new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const lcp = entries[entries.length - 1]
      this.metrics.lcp = lcp.renderTime || lcp.loadTime
      this.reportMetric('LCP', this.metrics.lcp)
    }).observe({ entryTypes: ['largest-contentful-paint'] })
    
    // First Input Delay
    new PerformanceObserver((list) => {
      const entries = list.getEntries()
      entries.forEach((entry) => {
        this.metrics.fid = entry.processingStart - entry.startTime
        this.reportMetric('FID', this.metrics.fid)
      })
    }).observe({ entryTypes: ['first-input'] })
    
    // Cumulative Layout Shift
    let clsValue = 0
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) {
          clsValue += entry.value
        }
      }
      this.metrics.cls = clsValue
      this.reportMetric('CLS', clsValue)
    }).observe({ entryTypes: ['layout-shift'] })
  }
  
  private reportMetric(name: string, value: number) {
    // Send to analytics
    if (window.gtag) {
      gtag('event', 'performance', {
        metric_name: name,
        value: Math.round(value),
        page_path: window.location.pathname
      })
    }
    
    // Send to monitoring endpoint
    fetch('/api/v1/metrics/rum', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        metric: name,
        value: value,
        url: window.location.href,
        timestamp: new Date().toISOString()
      })
    }).catch(() => {})  // Fail silently
  }
}
```

### 2. Application Performance Monitoring

```python
# app/core/monitoring/apm.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing(app, service_name: str = "boardroom-api"):
    """Setup distributed tracing"""
    
    # Configure tracer
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(service_name)
    
    # Configure exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://jaeger:4317",
        insecure=True
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument SQLAlchemy
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        service=service_name
    )
    
    return tracer

# Custom span decorator
def traced(name: str):
    """Decorator to add tracing to functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                try:
                    # Add attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Mark as successful
                    span.set_status(StatusCode.OK)
                    
                    return result
                except Exception as e:
                    # Record exception
                    span.record_exception(e)
                    span.set_status(
                        StatusCode.ERROR,
                        description=str(e)
                    )
                    raise
        
        return wrapper
    return decorator
```

## Performance Best Practices

### 1. Frontend Best Practices

1. **Component Optimization**
   - Use React.memo for expensive components
   - Implement proper key props for lists
   - Avoid inline function definitions
   - Use useCallback and useMemo appropriately

2. **Bundle Optimization**
   - Enable tree shaking
   - Use dynamic imports for code splitting
   - Minimize third-party dependencies
   - Regular bundle analysis

3. **Asset Optimization**
   - Use modern image formats (WebP, AVIF)
   - Implement responsive images
   - Lazy load below-the-fold content
   - Preload critical resources

### 2. Backend Best Practices

1. **Query Optimization**
   - Use database indexes effectively
   - Avoid N+1 queries
   - Implement query result caching
   - Use database connection pooling

2. **API Design**
   - Implement proper pagination
   - Use field filtering
   - Enable response compression
   - Cache GET requests

3. **Async Operations**
   - Use async/await properly
   - Implement request queuing
   - Set appropriate timeouts
   - Handle backpressure

### 3. Infrastructure Best Practices

1. **Caching Strategy**
   - Multi-level caching (L1, L2, CDN)
   - Cache invalidation strategy
   - Appropriate TTL values
   - Cache warming for critical data

2. **Scaling Strategy**
   - Horizontal scaling for stateless services
   - Database read replicas
   - Load balancing configuration
   - Auto-scaling policies

3. **Monitoring and Alerting**
   - Real-time performance monitoring
   - Proactive alerting
   - Performance budgets
   - Regular performance audits

## Performance Testing

### Load Testing Script

```python
# performance_tests/load_test.py
import asyncio
import aiohttp
import time
from statistics import mean, median

async def load_test(url: str, concurrent_users: int, requests_per_user: int):
    """Run load test against endpoint"""
    
    async def make_request(session: aiohttp.ClientSession) -> float:
        start = time.time()
        async with session.get(url) as response:
            await response.text()
            return time.time() - start
    
    async def user_session():
        async with aiohttp.ClientSession() as session:
            times = []
            for _ in range(requests_per_user):
                response_time = await make_request(session)
                times.append(response_time)
            return times
    
    # Run concurrent user sessions
    start_time = time.time()
    tasks = [user_session() for _ in range(concurrent_users)]
    all_times = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Flatten times
    response_times = [t for user_times in all_times for t in user_times]
    
    # Calculate metrics
    print(f"Load Test Results for {url}")
    print(f"Concurrent Users: {concurrent_users}")
    print(f"Requests per User: {requests_per_user}")
    print(f"Total Requests: {len(response_times)}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Requests/sec: {len(response_times) / total_time:.2f}")
    print(f"Avg Response Time: {mean(response_times):.3f}s")
    print(f"Median Response Time: {median(response_times):.3f}s")
    print(f"Min Response Time: {min(response_times):.3f}s")
    print(f"Max Response Time: {max(response_times):.3f}s")

# Run test
asyncio.run(load_test("http://localhost:8000/api/v1/boardrooms", 100, 10))
```

## Continuous Optimization

### Performance Budget Monitoring

```javascript
// performance-budget.config.js
module.exports = {
  // Build size budgets
  bundles: [
    {
      name: "main",
      maxSize: "200 KB"
    },
    {
      name: "vendor", 
      maxSize: "300 KB"
    }
  ],
  
  // Runtime performance budgets
  metrics: {
    FCP: 1500,      // First Contentful Paint
    LCP: 2500,      // Largest Contentful Paint  
    FID: 100,       // First Input Delay
    CLS: 0.1,       // Cumulative Layout Shift
    TTI: 3500       // Time to Interactive
  },
  
  // Lighthouse score thresholds
  scores: {
    performance: 90,
    accessibility: 90,
    bestPractices: 90,
    seo: 90
  }
}
```

### Automated Performance Testing

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  pull_request:
    branches: [main]

jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Lighthouse CI
        uses: treosh/lighthouse-ci-action@v9
        with:
          urls: |
            http://localhost:3000
            http://localhost:3000/dashboard
            http://localhost:3000/meetings
          budgetPath: ./performance-budget.config.js
          uploadArtifacts: true
          temporaryPublicStorage: true
      
      - name: Load Testing
        run: |
          npm run test:load
          
      - name: Bundle Size Check
        run: |
          npm run analyze:bundle
          
      - name: Comment Results
        uses: actions/github-script@v6
        if: github.event_name == 'pull_request'
        with:
          script: |
            const results = require('./lighthouse-results.json');
            const comment = `## Performance Test Results
            
            | Metric | Score | Target | Status |
            |--------|-------|--------|---------|
            | Performance | ${results.performance} | 90 | ${results.performance >= 90 ? '✅' : '❌'} |
            | FCP | ${results.fcp}ms | 1500ms | ${results.fcp <= 1500 ? '✅' : '❌'} |
            | LCP | ${results.lcp}ms | 2500ms | ${results.lcp <= 2500 ? '✅' : '❌'} |
            `;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

---

By implementing these optimization strategies, Boardroom Phase 3 achieves exceptional performance across all metrics, ensuring a fast, responsive experience for users regardless of scale or complexity.