# Performance Optimization

## Overview

Phase 3 introduces comprehensive performance optimizations to ensure the Boardroom platform delivers exceptional speed and responsiveness. These optimizations span from frontend bundle optimization to backend caching strategies, providing a seamless user experience even under heavy load.

## Performance Architecture

### Optimization Layers

```mermaid
graph TB
    subgraph "Frontend Optimization"
        A[Code Splitting] --> B[Lazy Loading]
        B --> C[Bundle Optimization]
        C --> D[Image Optimization]
        D --> E[Service Worker Caching]
    end
    
    subgraph "Rendering Optimization"
        F[React Memoization] --> G[Virtual Scrolling]
        G --> H[Suspense Boundaries]
        H --> I[Progressive Enhancement]
    end
    
    subgraph "Network Optimization"
        J[Request Batching] --> K[Response Compression]
        K --> L[CDN Integration]
        L --> M[Edge Caching]
    end
    
    subgraph "Backend Optimization"
        N[Query Optimization] --> O[Redis Caching]
        O --> P[Connection Pooling]
        P --> Q[Load Balancing]
    end
```

## Frontend Performance

### Code Splitting Strategy

#### Route-Based Splitting

```typescript
// Dynamic imports for route components
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Meetings = lazy(() => import('./pages/Meetings'))
const Decisions = lazy(() => import('./pages/Decisions'))
const Settings = lazy(() => import('./pages/Settings'))

// App routing with lazy loading
function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/meetings" element={<Meetings />} />
        <Route path="/decisions" element={<Decisions />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  )
}
```

#### Component-Based Splitting

```typescript
// LazyLoader component for heavy components
export const LazyLoader: React.FC<{
  component: () => Promise<{ default: React.ComponentType<any> }>
  fallback?: React.ReactNode
  errorFallback?: React.ComponentType<{ error: Error }>
}> = ({ component, fallback, errorFallback }) => {
  const LazyComponent = lazy(component)
  
  return (
    <ErrorBoundary fallback={errorFallback}>
      <Suspense fallback={fallback || <ComponentLoader />}>
        <LazyComponent />
      </Suspense>
    </ErrorBoundary>
  )
}

// Usage
<LazyLoader
  component={() => import('./components/HeavyChart')}
  fallback={<ChartSkeleton />}
/>
```

### Bundle Optimization

#### Webpack Configuration

```javascript
// next.config.js optimization
module.exports = {
  webpack: (config, { dev, isServer }) => {
    // Production optimizations
    if (!dev && !isServer) {
      // Tree shaking
      config.optimization.usedExports = true
      config.optimization.sideEffects = false
      
      // Module concatenation
      config.optimization.concatenateModules = true
      
      // Split chunks strategy
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          default: false,
          vendors: false,
          vendor: {
            name: 'vendor',
            chunks: 'all',
            test: /node_modules/,
            priority: 20
          },
          common: {
            name: 'common',
            minChunks: 2,
            chunks: 'all',
            priority: 10,
            reuseExistingChunk: true,
            enforce: true
          }
        }
      }
    }
    
    return config
  }
}
```

#### Bundle Analysis

```typescript
// Bundle size monitoring
interface BundleMetrics {
  totalSize: number
  mainBundleSize: number
  vendorBundleSize: number
  chunkSizes: Record<string, number>
  criticalCss: number
}

class BundleAnalyzer {
  async analyze(): Promise<BundleMetrics> {
    const stats = await this.getWebpackStats()
    
    return {
      totalSize: this.calculateTotalSize(stats),
      mainBundleSize: stats.assets.find(a => a.name === 'main.js')?.size || 0,
      vendorBundleSize: stats.assets.find(a => a.name === 'vendor.js')?.size || 0,
      chunkSizes: this.getChunkSizes(stats),
      criticalCss: this.getCriticalCssSize()
    }
  }
  
  checkBudgets(metrics: BundleMetrics): BudgetResult {
    const budgets = {
      total: 1000 * 1024,      // 1MB total
      main: 250 * 1024,        // 250KB main bundle
      vendor: 500 * 1024,      // 500KB vendor bundle
      chunk: 100 * 1024        // 100KB per chunk
    }
    
    const violations = []
    
    if (metrics.totalSize > budgets.total) {
      violations.push(`Total size ${metrics.totalSize} exceeds budget ${budgets.total}`)
    }
    
    return { passed: violations.length === 0, violations }
  }
}
```

### React Performance Optimization

#### Memoization Strategies

```typescript
// MemoizedComponents.tsx
import { memo, useMemo, useCallback } from 'react'

// Heavy computation memoization
export const ExpensiveComponent = memo(({ data }: { data: any[] }) => {
  const processedData = useMemo(() => {
    return data
      .filter(item => item.active)
      .sort((a, b) => b.score - a.score)
      .map(item => ({
        ...item,
        formatted: formatComplexData(item)
      }))
  }, [data])
  
  return <DataVisualization data={processedData} />
}, (prevProps, nextProps) => {
  // Custom comparison for deep equality
  return deepEqual(prevProps.data, nextProps.data)
})

// Callback memoization
export const InteractiveList = ({ items, onItemClick }) => {
  const handleClick = useCallback((id: string) => {
    onItemClick(id)
  }, [onItemClick])
  
  const memoizedItems = useMemo(() => 
    items.map(item => (
      <MemoizedListItem
        key={item.id}
        item={item}
        onClick={handleClick}
      />
    )),
    [items, handleClick]
  )
  
  return <div className="list">{memoizedItems}</div>
}

const MemoizedListItem = memo(({ item, onClick }) => (
  <div onClick={() => onClick(item.id)}>
    {item.name}
  </div>
))
```

#### Virtual Scrolling

```typescript
// VirtualList component for large datasets
import { FixedSizeList } from 'react-window'

export const VirtualizedMeetingList: React.FC<{
  meetings: Meeting[]
  height: number
}> = ({ meetings, height }) => {
  const Row = ({ index, style }) => (
    <div style={style}>
      <MeetingCard meeting={meetings[index]} />
    </div>
  )
  
  return (
    <FixedSizeList
      height={height}
      itemCount={meetings.length}
      itemSize={120} // Fixed height per item
      width="100%"
      overscanCount={5} // Render 5 items outside visible area
    >
      {Row}
    </FixedSizeList>
  )
}

// Variable height virtual list
import { VariableSizeList } from 'react-window'

export const VirtualizedDecisionList: React.FC<{
  decisions: Decision[]
}> = ({ decisions }) => {
  const listRef = useRef<VariableSizeList>(null)
  const rowHeights = useRef<Record<number, number>>({})
  
  const getItemSize = (index: number) => {
    return rowHeights.current[index] || 150 // Default height
  }
  
  const Row = ({ index, style }) => {
    const rowRef = useRef<HTMLDivElement>(null)
    
    useEffect(() => {
      if (rowRef.current) {
        const height = rowRef.current.getBoundingClientRect().height
        if (rowHeights.current[index] !== height) {
          rowHeights.current[index] = height
          listRef.current?.resetAfterIndex(index)
        }
      }
    }, [index])
    
    return (
      <div ref={rowRef} style={style}>
        <DecisionCard decision={decisions[index]} />
      </div>
    )
  }
  
  return (
    <AutoSizer>
      {({ height, width }) => (
        <VariableSizeList
          ref={listRef}
          height={height}
          itemCount={decisions.length}
          itemSize={getItemSize}
          width={width}
        >
          {Row}
        </VariableSizeList>
      )}
    </AutoSizer>
  )
}
```

### Performance Monitoring

#### Real-Time Performance Tracking

```typescript
// PerformanceMonitor.tsx
export const PerformanceMonitor: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    fps: 0,
    memory: 0,
    renderTime: 0,
    networkLatency: 0
  })
  
  useEffect(() => {
    const monitor = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      
      entries.forEach(entry => {
        if (entry.entryType === 'measure') {
          setMetrics(prev => ({
            ...prev,
            renderTime: entry.duration
          }))
        }
      })
    })
    
    monitor.observe({ entryTypes: ['measure', 'navigation'] })
    
    // FPS monitoring
    let lastTime = performance.now()
    let frames = 0
    
    const calculateFPS = () => {
      frames++
      const currentTime = performance.now()
      
      if (currentTime >= lastTime + 1000) {
        setMetrics(prev => ({
          ...prev,
          fps: Math.round((frames * 1000) / (currentTime - lastTime))
        }))
        frames = 0
        lastTime = currentTime
      }
      
      requestAnimationFrame(calculateFPS)
    }
    
    calculateFPS()
    
    // Memory monitoring
    if ('memory' in performance) {
      const memoryInterval = setInterval(() => {
        setMetrics(prev => ({
          ...prev,
          memory: (performance as any).memory.usedJSHeapSize / 1048576
        }))
      }, 1000)
      
      return () => clearInterval(memoryInterval)
    }
  }, [])
  
  return (
    <div className="performance-monitor">
      <MetricDisplay label="FPS" value={metrics.fps} target={60} />
      <MetricDisplay label="Memory (MB)" value={metrics.memory} />
      <MetricDisplay label="Render (ms)" value={metrics.renderTime} target={16} />
      <MetricDisplay label="Latency (ms)" value={metrics.networkLatency} target={100} />
    </div>
  )
}
```

#### Performance Budgets

```typescript
interface PerformanceBudget {
  metric: string
  budget: number
  unit: string
}

const performanceBudgets: PerformanceBudget[] = [
  { metric: 'First Contentful Paint', budget: 1.5, unit: 's' },
  { metric: 'Largest Contentful Paint', budget: 2.5, unit: 's' },
  { metric: 'Time to Interactive', budget: 3.5, unit: 's' },
  { metric: 'Total Blocking Time', budget: 300, unit: 'ms' },
  { metric: 'Cumulative Layout Shift', budget: 0.1, unit: '' },
  { metric: 'Bundle Size', budget: 1000, unit: 'KB' }
]

class PerformanceBudgetChecker {
  async checkBudgets(): Promise<BudgetCheckResult> {
    const metrics = await this.collectMetrics()
    const results: BudgetViolation[] = []
    
    for (const budget of performanceBudgets) {
      const actual = metrics[budget.metric]
      if (actual > budget.budget) {
        results.push({
          metric: budget.metric,
          budget: budget.budget,
          actual,
          exceeded: actual - budget.budget,
          percentage: ((actual - budget.budget) / budget.budget) * 100
        })
      }
    }
    
    return {
      passed: results.length === 0,
      violations: results
    }
  }
}
```

## Service Worker Optimization

### Advanced Caching Strategies

```javascript
// service-worker-enhanced.js
const CACHE_VERSION = 'v1'
const CACHE_NAMES = {
  static: `static-${CACHE_VERSION}`,
  dynamic: `dynamic-${CACHE_VERSION}`,
  images: `images-${CACHE_VERSION}`,
  api: `api-${CACHE_VERSION}`
}

// Precache critical resources
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/offline.html',
  '/css/critical.css',
  '/js/app.js'
]

// Cache strategies
const cacheStrategies = {
  // Stale while revalidate for API calls
  staleWhileRevalidate: async (request) => {
    const cache = await caches.open(CACHE_NAMES.api)
    const cachedResponse = await cache.match(request)
    
    const fetchPromise = fetch(request).then(response => {
      if (response.ok) {
        cache.put(request, response.clone())
      }
      return response
    })
    
    return cachedResponse || fetchPromise
  },
  
  // Network first with cache fallback
  networkFirst: async (request, cacheName) => {
    try {
      const response = await fetch(request)
      if (response.ok) {
        const cache = await caches.open(cacheName)
        cache.put(request, response.clone())
      }
      return response
    } catch (error) {
      const cachedResponse = await caches.match(request)
      if (cachedResponse) {
        return cachedResponse
      }
      throw error
    }
  },
  
  // Cache first for static assets
  cacheFirst: async (request, cacheName) => {
    const cachedResponse = await caches.match(request)
    if (cachedResponse) {
      return cachedResponse
    }
    
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(cacheName)
      cache.put(request, response.clone())
    }
    return response
  }
}

// Request routing
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)
  
  // API calls - stale while revalidate
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(cacheStrategies.staleWhileRevalidate(request))
    return
  }
  
  // Images - cache first
  if (request.destination === 'image') {
    event.respondWith(cacheStrategies.cacheFirst(request, CACHE_NAMES.images))
    return
  }
  
  // Static assets - cache first
  if (url.pathname.match(/\.(js|css|woff2?)$/)) {
    event.respondWith(cacheStrategies.cacheFirst(request, CACHE_NAMES.static))
    return
  }
  
  // Everything else - network first
  event.respondWith(cacheStrategies.networkFirst(request, CACHE_NAMES.dynamic))
})
```

### Background Sync

```javascript
// Register sync events
self.addEventListener('sync', async (event) => {
  if (event.tag === 'sync-data') {
    event.waitUntil(syncOfflineData())
  }
})

async function syncOfflineData() {
  const db = await openDB('offline-queue', 1)
  const tx = db.transaction('requests', 'readonly')
  const requests = await tx.objectStore('requests').getAll()
  
  for (const request of requests) {
    try {
      const response = await fetch(request.url, {
        method: request.method,
        headers: request.headers,
        body: request.body
      })
      
      if (response.ok) {
        // Remove from queue
        await removeFromQueue(request.id)
        
        // Notify client
        self.clients.matchAll().then(clients => {
          clients.forEach(client => {
            client.postMessage({
              type: 'sync-success',
              requestId: request.id
            })
          })
        })
      }
    } catch (error) {
      console.error('Sync failed for request:', request.id, error)
    }
  }
}
```

## Image Optimization

### Next.js Image Component

```typescript
import Image from 'next/image'

// Optimized image loading
export const OptimizedImage: React.FC<{
  src: string
  alt: string
  priority?: boolean
  placeholder?: 'blur' | 'empty'
  blurDataURL?: string
}> = ({ src, alt, priority = false, placeholder = 'blur', blurDataURL }) => {
  return (
    <Image
      src={src}
      alt={alt}
      width={800}
      height={600}
      priority={priority}
      placeholder={placeholder}
      blurDataURL={blurDataURL}
      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
      quality={85}
      loading={priority ? 'eager' : 'lazy'}
    />
  )
}

// Progressive image loading
export const ProgressiveImage: React.FC<{
  src: string
  placeholderSrc: string
  alt: string
}> = ({ src, placeholderSrc, alt }) => {
  const [imgSrc, setImgSrc] = useState(placeholderSrc)
  const [isLoading, setIsLoading] = useState(true)
  
  useEffect(() => {
    const img = new window.Image()
    img.src = src
    img.onload = () => {
      setImgSrc(src)
      setIsLoading(false)
    }
  }, [src])
  
  return (
    <div className={`progressive-image ${isLoading ? 'loading' : 'loaded'}`}>
      <img src={imgSrc} alt={alt} />
    </div>
  )
}
```

### Image Format Optimization

```typescript
// Automatic WebP/AVIF conversion
class ImageOptimizer {
  async optimizeImage(
    file: File,
    options: ImageOptimizationOptions = {}
  ): Promise<OptimizedImage> {
    const {
      maxWidth = 1920,
      maxHeight = 1080,
      quality = 85,
      formats = ['webp', 'avif', 'original']
    } = options
    
    // Resize image if needed
    const resized = await this.resizeImage(file, maxWidth, maxHeight)
    
    // Generate multiple formats
    const results: Record<string, Blob> = {}
    
    for (const format of formats) {
      if (format === 'original') {
        results[format] = resized
      } else {
        results[format] = await this.convertToFormat(resized, format, quality)
      }
    }
    
    return {
      formats: results,
      metadata: await this.extractMetadata(file)
    }
  }
  
  private async convertToFormat(
    blob: Blob,
    format: string,
    quality: number
  ): Promise<Blob> {
    const bitmap = await createImageBitmap(blob)
    const canvas = document.createElement('canvas')
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(bitmap, 0, 0)
    
    return new Promise((resolve) => {
      canvas.toBlob(
        (blob) => resolve(blob!),
        `image/${format}`,
        quality / 100
      )
    })
  }
}
```

## Database Query Optimization

### Query Performance Analysis

```typescript
// Backend query optimization
class QueryOptimizer {
  async analyzeQuery(query: string): Promise<QueryAnalysis> {
    const explainResult = await db.raw(`EXPLAIN ANALYZE ${query}`)
    
    return {
      executionTime: this.extractExecutionTime(explainResult),
      scanType: this.extractScanType(explainResult),
      rowsExamined: this.extractRowsExamined(explainResult),
      suggestions: this.generateSuggestions(explainResult)
    }
  }
  
  async optimizeQuery(query: string): Promise<string> {
    const analysis = await this.analyzeQuery(query)
    
    // Apply optimizations based on analysis
    let optimized = query
    
    if (analysis.scanType === 'sequential') {
      optimized = this.addIndexHints(optimized)
    }
    
    if (analysis.rowsExamined > 10000) {
      optimized = this.addPagination(optimized)
    }
    
    return optimized
  }
  
  // Index suggestions
  async suggestIndexes(table: string): Promise<IndexSuggestion[]> {
    const queries = await this.getSlowQueries(table)
    const suggestions: IndexSuggestion[] = []
    
    for (const query of queries) {
      const missingIndexes = await this.identifyMissingIndexes(query)
      suggestions.push(...missingIndexes)
    }
    
    return this.deduplicateSuggestions(suggestions)
  }
}
```

### Connection Pooling

```typescript
// Database connection pool configuration
const poolConfig = {
  min: 2,
  max: 10,
  acquireTimeoutMillis: 30000,
  createTimeoutMillis: 30000,
  destroyTimeoutMillis: 5000,
  idleTimeoutMillis: 30000,
  reapIntervalMillis: 1000,
  createRetryIntervalMillis: 100,
  propagateCreateError: false
}

class ConnectionPool {
  private pool: Pool
  private metrics: PoolMetrics = {
    activeConnections: 0,
    idleConnections: 0,
    totalConnections: 0,
    waitingRequests: 0
  }
  
  async getConnection(): Promise<PoolConnection> {
    const start = performance.now()
    
    try {
      const connection = await this.pool.acquire()
      this.metrics.activeConnections++
      
      // Track connection usage
      const wrapped = this.wrapConnection(connection, start)
      return wrapped
    } catch (error) {
      this.metrics.connectionErrors++
      throw error
    }
  }
  
  private wrapConnection(
    connection: Connection,
    acquireTime: number
  ): PoolConnection {
    return {
      ...connection,
      release: async () => {
        const usageTime = performance.now() - acquireTime
        this.recordUsageMetrics(usageTime)
        
        this.metrics.activeConnections--
        await this.pool.release(connection)
      }
    }
  }
}
```

## Redis Caching Optimization

### Advanced Caching Patterns

```typescript
class RedisCache {
  private client: Redis
  private defaultTTL = 300 // 5 minutes
  
  // Cache aside pattern
  async cacheAside<T>(
    key: string,
    fetcher: () => Promise<T>,
    options?: CacheOptions
  ): Promise<T> {
    // Try cache first
    const cached = await this.get<T>(key)
    if (cached !== null) {
      this.recordHit(key)
      return cached
    }
    
    this.recordMiss(key)
    
    // Fetch from source
    const data = await fetcher()
    
    // Cache the result
    await this.set(key, data, options?.ttl || this.defaultTTL)
    
    return data
  }
  
  // Write through pattern
  async writeThrough<T>(
    key: string,
    data: T,
    writer: (data: T) => Promise<void>,
    ttl?: number
  ): Promise<void> {
    // Write to cache
    await this.set(key, data, ttl || this.defaultTTL)
    
    // Write to database
    await writer(data)
  }
  
  // Batch operations
  async mget<T>(keys: string[]): Promise<(T | null)[]> {
    const pipeline = this.client.pipeline()
    
    keys.forEach(key => {
      pipeline.get(key)
    })
    
    const results = await pipeline.exec()
    
    return results.map(([err, value]) => {
      if (err) return null
      return value ? JSON.parse(value) : null
    })
  }
  
  // Cache warming
  async warmCache(patterns: CacheWarmPattern[]): Promise<void> {
    for (const pattern of patterns) {
      const data = await pattern.fetcher()
      await this.set(pattern.key, data, pattern.ttl)
    }
  }
  
  // Cache invalidation
  async invalidatePattern(pattern: string): Promise<number> {
    const keys = await this.client.keys(pattern)
    
    if (keys.length === 0) return 0
    
    const pipeline = this.client.pipeline()
    keys.forEach(key => pipeline.del(key))
    
    await pipeline.exec()
    return keys.length
  }
}
```

### Cache Metrics

```typescript
interface CacheMetrics {
  hits: number
  misses: number
  hitRate: number
  avgResponseTime: number
  memoryUsage: number
  evictions: number
  keyCount: number
}

class CacheMonitor {
  async getMetrics(): Promise<CacheMetrics> {
    const info = await this.redis.info('stats')
    const memory = await this.redis.info('memory')
    
    const hits = parseInt(info.keyspace_hits || '0')
    const misses = parseInt(info.keyspace_misses || '0')
    const total = hits + misses
    
    return {
      hits,
      misses,
      hitRate: total > 0 ? (hits / total) * 100 : 0,
      avgResponseTime: await this.getAverageResponseTime(),
      memoryUsage: parseInt(memory.used_memory || '0'),
      evictions: parseInt(info.evicted_keys || '0'),
      keyCount: await this.redis.dbsize()
    }
  }
  
  async optimizeCacheUsage(): Promise<OptimizationResult> {
    const metrics = await this.getMetrics()
    const suggestions: string[] = []
    
    // Low hit rate
    if (metrics.hitRate < 80) {
      suggestions.push('Consider increasing TTL for frequently accessed keys')
      suggestions.push('Implement cache warming for critical data')
    }
    
    // High memory usage
    if (metrics.memoryUsage > 0.8 * MAX_MEMORY) {
      suggestions.push('Implement eviction policies')
      suggestions.push('Review and reduce TTL for large objects')
    }
    
    // High eviction rate
    if (metrics.evictions > 1000) {
      suggestions.push('Increase Redis memory allocation')
      suggestions.push('Implement data compression')
    }
    
    return { metrics, suggestions }
  }
}
```

## Network Optimization

### Request Batching

```typescript
class RequestBatcher {
  private queue: Map<string, PendingRequest[]> = new Map()
  private timeout: NodeJS.Timeout | null = null
  private batchSize = 10
  private batchDelay = 50 // ms
  
  async add<T>(
    endpoint: string,
    params: any
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const request: PendingRequest = {
        params,
        resolve,
        reject
      }
      
      if (!this.queue.has(endpoint)) {
        this.queue.set(endpoint, [])
      }
      
      this.queue.get(endpoint)!.push(request)
      
      // Schedule batch processing
      if (!this.timeout) {
        this.timeout = setTimeout(() => this.processBatch(), this.batchDelay)
      }
      
      // Process immediately if batch is full
      if (this.queue.get(endpoint)!.length >= this.batchSize) {
        this.processBatch()
      }
    })
  }
  
  private async processBatch(): Promise<void> {
    if (this.timeout) {
      clearTimeout(this.timeout)
      this.timeout = null
    }
    
    const batches = new Map(this.queue)
    this.queue.clear()
    
    for (const [endpoint, requests] of batches) {
      try {
        const batchParams = requests.map(r => r.params)
        const results = await this.executeBatch(endpoint, batchParams)
        
        requests.forEach((request, index) => {
          request.resolve(results[index])
        })
      } catch (error) {
        requests.forEach(request => {
          request.reject(error)
        })
      }
    }
  }
}
```

### Response Compression

```typescript
// Compression middleware
app.use(compression({
  level: 6, // Compression level (0-9)
  threshold: 1024, // Only compress responses > 1KB
  filter: (req, res) => {
    // Don't compress if already compressed
    if (res.getHeader('Content-Encoding')) {
      return false
    }
    
    // Compress JSON, HTML, CSS, JS
    const contentType = res.getHeader('Content-Type')
    return /json|text|javascript|css/.test(contentType)
  }
}))

// Brotli compression for static assets
app.use('/static', expressStaticBrotli('public', {
  enableBrotli: true,
  orderPreference: ['br', 'gz'],
  maxAge: 31536000 // 1 year
}))
```

## Performance Testing

### Load Testing

```typescript
// Load test configuration
interface LoadTestConfig {
  url: string
  duration: number
  virtualUsers: number
  rampUp: number
  scenarios: TestScenario[]
}

class LoadTester {
  async runTest(config: LoadTestConfig): Promise<LoadTestResults> {
    const results: LoadTestResults = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      avgResponseTime: 0,
      p95ResponseTime: 0,
      p99ResponseTime: 0,
      throughput: 0,
      errors: []
    }
    
    // Execute test scenarios
    const responses = await this.executeScenarios(config)
    
    // Calculate metrics
    results.totalRequests = responses.length
    results.successfulRequests = responses.filter(r => r.success).length
    results.failedRequests = responses.filter(r => !r.success).length
    
    const responseTimes = responses
      .filter(r => r.success)
      .map(r => r.duration)
      .sort((a, b) => a - b)
    
    results.avgResponseTime = this.average(responseTimes)
    results.p95ResponseTime = this.percentile(responseTimes, 95)
    results.p99ResponseTime = this.percentile(responseTimes, 99)
    results.throughput = results.successfulRequests / (config.duration / 1000)
    
    return results
  }
}
```

### Performance Regression Detection

```typescript
class PerformanceRegression {
  async detectRegressions(
    current: PerformanceMetrics,
    baseline: PerformanceMetrics,
    thresholds: RegressionThresholds
  ): Promise<RegressionResult> {
    const regressions: Regression[] = []
    
    // Check each metric
    const metrics = [
      { name: 'FCP', current: current.fcp, baseline: baseline.fcp, threshold: thresholds.fcp },
      { name: 'LCP', current: current.lcp, baseline: baseline.lcp, threshold: thresholds.lcp },
      { name: 'TTI', current: current.tti, baseline: baseline.tti, threshold: thresholds.tti },
      { name: 'TBT', current: current.tbt, baseline: baseline.tbt, threshold: thresholds.tbt },
      { name: 'CLS', current: current.cls, baseline: baseline.cls, threshold: thresholds.cls }
    ]
    
    for (const metric of metrics) {
      const degradation = ((metric.current - metric.baseline) / metric.baseline) * 100
      
      if (degradation > metric.threshold) {
        regressions.push({
          metric: metric.name,
          baseline: metric.baseline,
          current: metric.current,
          degradation: degradation,
          severity: this.getSeverity(degradation, metric.threshold)
        })
      }
    }
    
    return {
      hasRegressions: regressions.length > 0,
      regressions,
      summary: this.generateSummary(regressions)
    }
  }
}
```

## Best Practices

### Performance Checklist

#### Frontend
- [ ] Code splitting implemented
- [ ] Lazy loading for routes and components
- [ ] Images optimized with next/image
- [ ] Bundle size under budget
- [ ] Critical CSS inlined
- [ ] Fonts optimized
- [ ] Third-party scripts deferred
- [ ] Service worker caching active

#### React
- [ ] Components memoized where appropriate
- [ ] useCallback for event handlers
- [ ] useMemo for expensive computations
- [ ] Virtual scrolling for long lists
- [ ] Suspense boundaries implemented
- [ ] Error boundaries in place

#### Network
- [ ] API calls batched
- [ ] Responses compressed
- [ ] CDN configured
- [ ] HTTP/2 enabled
- [ ] Resource hints added
- [ ] Prefetching implemented

#### Backend
- [ ] Database queries optimized
- [ ] Indexes properly configured
- [ ] Connection pooling enabled
- [ ] Redis caching implemented
- [ ] Response caching headers set
- [ ] Rate limiting configured

### Monitoring Dashboard

```typescript
// Performance dashboard component
export const PerformanceDashboard: React.FC = () => {
  const { metrics, trends, alerts } = usePerformanceData()
  
  return (
    <div className="performance-dashboard">
      <div className="metrics-grid">
        <MetricCard
          title="Page Load Time"
          value={metrics.pageLoadTime}
          unit="ms"
          trend={trends.pageLoadTime}
          target={1500}
        />
        <MetricCard
          title="API Response Time"
          value={metrics.apiResponseTime}
          unit="ms"
          trend={trends.apiResponseTime}
          target={200}
        />
        <MetricCard
          title="Cache Hit Rate"
          value={metrics.cacheHitRate}
          unit="%"
          trend={trends.cacheHitRate}
          target={85}
        />
        <MetricCard
          title="Error Rate"
          value={metrics.errorRate}
          unit="%"
          trend={trends.errorRate}
          target={0.1}
        />
      </div>
      
      <div className="performance-alerts">
        {alerts.map(alert => (
          <PerformanceAlert key={alert.id} alert={alert} />
        ))}
      </div>
      
      <div className="performance-charts">
        <ResponseTimeChart data={metrics.responseTimeHistory} />
        <ThroughputChart data={metrics.throughputHistory} />
        <ResourceUsageChart data={metrics.resourceUsage} />
      </div>
    </div>
  )
}
```

---

For implementation details, see the [Performance Components](../../src/components/performance/) or the [Performance API Documentation](../api/performance-api.md).