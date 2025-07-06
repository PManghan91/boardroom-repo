# Data Management API Reference

## Overview

The Data Management API provides comprehensive endpoints for managing application data, including CRUD operations, search functionality, import/export capabilities, and backup/restore features. All endpoints support advanced caching, validation, and offline synchronization.

## Base URL

```
https://api.boardroom.com/api/v1/data
```

## Authentication

All requests require JWT authentication:

```http
Authorization: Bearer <JWT_TOKEN>
```

## Common Headers

```http
Content-Type: application/json
Accept: application/json
X-Request-ID: <unique-request-id>
X-Client-Version: 1.0.0
```

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "requestId": "req_123",
    "version": "1.0"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional error context
    }
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "requestId": "req_123"
  }
}
```

## Endpoints

### Data Operations

#### Get Data

Retrieve data with optional caching and filtering.

```http
GET /data/{entity}/{id}
```

**Parameters:**

| Name | Type | Location | Required | Description |
|------|------|----------|----------|-------------|
| entity | string | path | Yes | Entity type (boardroom, meeting, decision) |
| id | string | path | Yes | Entity ID |
| include | string | query | No | Related data to include (comma-separated) |
| fields | string | query | No | Fields to return (comma-separated) |

**Headers:**

```http
If-None-Match: "etag_value"
Cache-Control: max-age=300
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "123",
    "type": "boardroom",
    "attributes": {
      "name": "Executive Board",
      "description": "Main executive boardroom",
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-15T10:30:00Z"
    },
    "relationships": {
      "members": {
        "data": [
          { "type": "user", "id": "456" },
          { "type": "user", "id": "789" }
        ]
      }
    }
  },
  "metadata": {
    "etag": "new_etag_value",
    "cacheControl": "private, max-age=300"
  }
}
```

#### List Data

Retrieve paginated list with filtering and sorting.

```http
GET /data/{entity}
```

**Parameters:**

| Name | Type | Location | Required | Description |
|------|------|----------|----------|-------------|
| entity | string | path | Yes | Entity type |
| page[number] | integer | query | No | Page number (default: 1) |
| page[size] | integer | query | No | Page size (default: 20, max: 100) |
| filter | object | query | No | Filter criteria |
| sort | string | query | No | Sort fields (comma-separated, prefix with - for DESC) |
| search | string | query | No | Full-text search query |

**Example Request:**

```http
GET /data/boardrooms?page[number]=1&page[size]=20&filter[active]=true&sort=-createdAt
```

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "123",
      "type": "boardroom",
      "attributes": {
        "name": "Executive Board",
        "active": true,
        "createdAt": "2024-01-01T00:00:00Z"
      }
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "pageCount": 5,
      "total": 87
    }
  },
  "links": {
    "self": "/data/boardrooms?page[number]=1",
    "first": "/data/boardrooms?page[number]=1",
    "last": "/data/boardrooms?page[number]=5",
    "next": "/data/boardrooms?page[number]=2"
  }
}
```

#### Create Data

Create new data with validation.

```http
POST /data/{entity}
```

**Request Body:**

```json
{
  "data": {
    "type": "boardroom",
    "attributes": {
      "name": "New Boardroom",
      "description": "Description here",
      "settings": {
        "isPublic": false,
        "requiresApproval": true
      }
    },
    "relationships": {
      "owner": {
        "data": { "type": "user", "id": "123" }
      }
    }
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "generated_id",
    "type": "boardroom",
    "attributes": {
      "name": "New Boardroom",
      "description": "Description here",
      "createdAt": "2024-01-15T10:30:00Z",
      "updatedAt": "2024-01-15T10:30:00Z"
    }
  },
  "metadata": {
    "location": "/data/boardrooms/generated_id"
  }
}
```

#### Update Data

Update existing data with optimistic locking.

```http
PATCH /data/{entity}/{id}
```

**Headers:**

```http
If-Match: "current_etag_value"
```

**Request Body:**

```json
{
  "data": {
    "type": "boardroom",
    "id": "123",
    "attributes": {
      "name": "Updated Name",
      "description": "Updated description"
    }
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "123",
    "type": "boardroom",
    "attributes": {
      "name": "Updated Name",
      "description": "Updated description",
      "updatedAt": "2024-01-15T10:35:00Z"
    }
  },
  "metadata": {
    "etag": "new_etag_value",
    "previousVersion": "old_etag_value"
  }
}
```

#### Delete Data

Delete data with soft delete option.

```http
DELETE /data/{entity}/{id}
```

**Parameters:**

| Name | Type | Location | Required | Description |
|------|------|----------|----------|-------------|
| permanent | boolean | query | No | Permanent delete (default: false) |

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "123",
    "deleted": true,
    "deletedAt": "2024-01-15T10:40:00Z"
  }
}
```

### Search Operations

#### Full-Text Search

Perform full-text search across entities.

```http
POST /data/search
```

**Request Body:**

```json
{
  "query": "budget meeting",
  "entities": ["boardroom", "meeting", "decision"],
  "filters": {
    "dateRange": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-12-31T23:59:59Z"
    },
    "tags": ["finance", "quarterly"]
  },
  "facets": ["entity", "tags", "author"],
  "highlight": {
    "fields": ["title", "description"],
    "preTag": "<em>",
    "postTag": "</em>"
  },
  "pagination": {
    "page": 1,
    "size": 20
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "123",
        "entity": "meeting",
        "score": 0.95,
        "highlights": {
          "title": "Q4 <em>Budget</em> Review <em>Meeting</em>"
        },
        "attributes": {
          "title": "Q4 Budget Review Meeting",
          "date": "2024-10-15T14:00:00Z"
        }
      }
    ],
    "facets": {
      "entity": {
        "meeting": 45,
        "decision": 23,
        "boardroom": 12
      },
      "tags": {
        "finance": 34,
        "quarterly": 28,
        "budget": 25
      }
    }
  },
  "meta": {
    "total": 80,
    "page": 1,
    "pageSize": 20,
    "took": 23
  }
}
```

#### Advanced Query

Execute complex queries with aggregations.

```http
POST /data/query
```

**Request Body:**

```json
{
  "entity": "decision",
  "query": {
    "bool": {
      "must": [
        { "term": { "status": "pending" } },
        { "range": { "deadline": { "gte": "now", "lte": "now+7d" } } }
      ],
      "should": [
        { "match": { "priority": "high" } }
      ]
    }
  },
  "aggregations": {
    "by_status": {
      "terms": { "field": "status" }
    },
    "by_deadline": {
      "date_histogram": {
        "field": "deadline",
        "interval": "day"
      }
    }
  }
}
```

### Import/Export Operations

#### Export Data

Export data in various formats.

```http
POST /data/export
```

**Request Body:**

```json
{
  "entities": ["boardroom", "meeting"],
  "format": "csv",
  "filters": {
    "dateRange": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-12-31T23:59:59Z"
    }
  },
  "options": {
    "includeRelationships": true,
    "includeMetadata": false
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "exportId": "export_123",
    "status": "processing",
    "format": "csv",
    "estimatedSize": 1048576,
    "expiresAt": "2024-01-16T10:30:00Z"
  }
}
```

#### Get Export Status

Check export job status.

```http
GET /data/export/{exportId}/status
```

**Response:**

```json
{
  "success": true,
  "data": {
    "exportId": "export_123",
    "status": "completed",
    "progress": 100,
    "downloadUrl": "/data/export/export_123/download",
    "size": 1234567,
    "expiresAt": "2024-01-16T10:30:00Z"
  }
}
```

#### Download Export

Download exported data.

```http
GET /data/export/{exportId}/download
```

**Response Headers:**

```http
Content-Type: text/csv
Content-Disposition: attachment; filename="boardroom_export_20240115.csv"
Content-Length: 1234567
```

#### Import Data

Import data from file.

```http
POST /data/import
```

**Request Body (multipart/form-data):**

```
------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="import.csv"
Content-Type: text/csv

[File contents]
------WebKitFormBoundary
Content-Disposition: form-data; name="options"

{
  "entity": "boardroom",
  "format": "csv",
  "mapping": {
    "Name": "name",
    "Description": "description"
  },
  "validation": {
    "skipInvalid": false,
    "dryRun": true
  }
}
------WebKitFormBoundary--
```

**Response:**

```json
{
  "success": true,
  "data": {
    "importId": "import_456",
    "status": "validating",
    "totalRecords": 100,
    "validRecords": 98,
    "errors": [
      {
        "row": 45,
        "field": "name",
        "error": "Required field missing"
      }
    ]
  }
}
```

### Backup/Restore Operations

#### Create Backup

Create a data backup.

```http
POST /data/backup
```

**Request Body:**

```json
{
  "name": "Weekly Backup",
  "description": "Regular weekly backup",
  "entities": ["all"],
  "options": {
    "compress": true,
    "encrypt": true,
    "includeFiles": false
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "backupId": "backup_789",
    "name": "Weekly Backup",
    "status": "in_progress",
    "createdAt": "2024-01-15T10:30:00Z",
    "estimatedSize": 52428800
  }
}
```

#### List Backups

Get list of available backups.

```http
GET /data/backups
```

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "backupId": "backup_789",
      "name": "Weekly Backup",
      "size": 52428800,
      "compressed": true,
      "encrypted": true,
      "createdAt": "2024-01-15T10:30:00Z",
      "expiresAt": "2024-02-15T10:30:00Z",
      "status": "completed"
    }
  ]
}
```

#### Restore Backup

Restore data from backup.

```http
POST /data/restore
```

**Request Body:**

```json
{
  "backupId": "backup_789",
  "options": {
    "entities": ["boardroom", "meeting"],
    "overwrite": false,
    "targetEnvironment": "staging"
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "restoreId": "restore_012",
    "status": "in_progress",
    "backupId": "backup_789",
    "startedAt": "2024-01-15T11:00:00Z"
  }
}
```

### Validation Operations

#### Validate Data

Validate data against schema.

```http
POST /data/validate
```

**Request Body:**

```json
{
  "entity": "boardroom",
  "data": {
    "name": "Test Boardroom",
    "description": "A"
  },
  "options": {
    "strict": true,
    "schema": "v2"
  }
}
```

**Response:**

```json
{
  "success": false,
  "data": {
    "valid": false,
    "errors": [
      {
        "field": "description",
        "code": "min_length",
        "message": "Description must be at least 10 characters",
        "params": {
          "min": 10,
          "actual": 1
        }
      }
    ],
    "warnings": []
  }
}
```

#### Bulk Validate

Validate multiple records.

```http
POST /data/validate/bulk
```

**Request Body:**

```json
{
  "entity": "meeting",
  "records": [
    {
      "title": "Meeting 1",
      "date": "2024-01-20T10:00:00Z"
    },
    {
      "title": "M",
      "date": "invalid-date"
    }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "totalRecords": 2,
    "validRecords": 1,
    "invalidRecords": 1,
    "results": [
      {
        "index": 0,
        "valid": true
      },
      {
        "index": 1,
        "valid": false,
        "errors": [
          {
            "field": "title",
            "code": "min_length",
            "message": "Title must be at least 3 characters"
          },
          {
            "field": "date",
            "code": "invalid_format",
            "message": "Invalid date format"
          }
        ]
      }
    ]
  }
}
```

### Synchronization Operations

#### Get Sync Status

Get synchronization status.

```http
GET /data/sync/status
```

**Response:**

```json
{
  "success": true,
  "data": {
    "lastSync": "2024-01-15T10:00:00Z",
    "pendingChanges": 5,
    "syncInProgress": false,
    "conflicts": 0,
    "offlineQueue": [
      {
        "id": "queue_123",
        "operation": "update",
        "entity": "boardroom",
        "entityId": "123",
        "timestamp": "2024-01-15T10:25:00Z"
      }
    ]
  }
}
```

#### Sync Data

Trigger manual synchronization.

```http
POST /data/sync
```

**Request Body:**

```json
{
  "entities": ["boardroom", "meeting"],
  "direction": "bidirectional",
  "resolveConflicts": "server_wins"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "syncId": "sync_456",
    "status": "in_progress",
    "startedAt": "2024-01-15T10:30:00Z",
    "entities": {
      "boardroom": {
        "toSync": 3,
        "synced": 0
      },
      "meeting": {
        "toSync": 2,
        "synced": 0
      }
    }
  }
}
```

#### Resolve Conflicts

Resolve synchronization conflicts.

```http
POST /data/sync/conflicts/resolve
```

**Request Body:**

```json
{
  "conflicts": [
    {
      "conflictId": "conflict_123",
      "resolution": "client",
      "mergedData": {
        "name": "Merged Boardroom Name"
      }
    }
  ]
}
```

## Caching

### Cache Headers

The API supports various caching strategies:

```http
# Response headers
ETag: "686897696a7c876b7e"
Last-Modified: Wed, 15 Jan 2024 10:30:00 GMT
Cache-Control: private, max-age=300
Vary: Accept-Encoding, Authorization

# Request headers
If-None-Match: "686897696a7c876b7e"
If-Modified-Since: Wed, 15 Jan 2024 10:30:00 GMT
```

### Cache Control Options

| Directive | Description |
|-----------|-------------|
| no-cache | Revalidate before using cached response |
| no-store | Don't cache the response |
| max-age=N | Cache for N seconds |
| private | Cache in browser only |
| public | Can be cached by proxies |

## Rate Limiting

### Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

### Limits

| Endpoint | Limit | Window |
|----------|-------|---------|
| GET requests | 1000 | 1 hour |
| POST/PUT/PATCH | 100 | 1 hour |
| DELETE | 50 | 1 hour |
| Import/Export | 10 | 1 hour |
| Backup/Restore | 5 | 1 hour |

## Error Codes

| Code | Description |
|------|-------------|
| INVALID_REQUEST | Request format is invalid |
| VALIDATION_ERROR | Data validation failed |
| NOT_FOUND | Resource not found |
| CONFLICT | Resource conflict (e.g., duplicate) |
| PRECONDITION_FAILED | ETag mismatch |
| QUOTA_EXCEEDED | Storage quota exceeded |
| RATE_LIMITED | Too many requests |
| SERVER_ERROR | Internal server error |

## WebSocket Integration

The Data API integrates with WebSocket for real-time updates:

```javascript
// Subscribe to data changes
ws.subscribe('data:boardroom:123')

// Receive real-time updates
ws.on('data.updated', (event) => {
  if (event.entity === 'boardroom' && event.id === '123') {
    // Update local cache
    updateCache(event.data)
  }
})
```

## SDK Examples

### JavaScript/TypeScript

```typescript
import { DataClient } from '@boardroom/data-sdk'

const client = new DataClient({
  baseUrl: 'https://api.boardroom.com/api/v1',
  token: authToken,
  cache: true
})

// Get data with caching
const boardroom = await client.get('boardroom', '123', {
  include: ['members', 'meetings'],
  cache: {
    strategy: 'stale-while-revalidate',
    ttl: 300
  }
})

// Search with facets
const results = await client.search({
  query: 'budget',
  entities: ['meeting', 'decision'],
  facets: ['tags', 'status']
})

// Import data
const importResult = await client.import(file, {
  entity: 'boardroom',
  format: 'csv',
  validation: { dryRun: true }
})
```

### Python

```python
from boardroom_sdk import DataClient

client = DataClient(
    base_url="https://api.boardroom.com/api/v1",
    token=auth_token,
    cache=True
)

# Create with validation
boardroom = client.create("boardroom", {
    "name": "New Boardroom",
    "description": "Description here"
})

# Bulk operations
results = client.bulk_update("meeting", [
    {"id": "123", "status": "completed"},
    {"id": "456", "status": "cancelled"}
])

# Export data
export_job = client.export(
    entities=["boardroom", "meeting"],
    format="excel",
    filters={"active": True}
)
```

---

For more information, see the [Data Management Features](../features/data-management.md) or the [API Standards Documentation](../../api/quick_start.md).