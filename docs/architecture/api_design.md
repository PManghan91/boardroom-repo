# API Design Patterns

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: API Developers  
**Next Review**: With API changes  

## Overview

This document outlines the API design patterns and conventions used in Boardroom AI. Following these patterns ensures consistency, maintainability, and a great developer experience.

## Core Principles

1. **RESTful Design**: Follow REST conventions where appropriate
2. **Consistency**: Uniform patterns across all endpoints
3. **Predictability**: Developers should be able to guess endpoint behavior
4. **Versioning**: Support API evolution without breaking changes
5. **Documentation**: Self-documenting through OpenAPI/Swagger

## API Structure

### Base URL Pattern

```
https://api.boardroom.ai/api/v{version}/{resource}
```

Examples:
```
https://api.boardroom.ai/api/v1/auth/login
https://api.boardroom.ai/api/v1/chatbot/chat
https://api.boardroom.ai/api/v1/boardrooms/123/sessions
```

### Versioning Strategy

**URL Versioning** (Primary):
```
/api/v1/users
/api/v2/users
```

**Header Versioning** (Alternative):
```
Accept: application/vnd.boardroom.v1+json
```

Version changes when:
- Breaking changes to request/response format
- Removing endpoints or fields
- Changing authentication methods

## Resource Naming

### Conventions

1. **Use nouns, not verbs**: `/users` not `/getUsers`
2. **Plural for collections**: `/users` not `/user`
3. **Kebab-case for multi-word**: `/auth/forgot-password`
4. **Hierarchical for relationships**: `/boardrooms/{id}/sessions`

### Examples

```
GET    /users              # List users
GET    /users/{id}         # Get specific user
POST   /users              # Create user
PUT    /users/{id}         # Update user
DELETE /users/{id}         # Delete user

GET    /boardrooms/{id}/sessions    # List sessions in boardroom
POST   /boardrooms/{id}/sessions    # Create session in boardroom
```

## Request Standards

### HTTP Methods

- **GET**: Retrieve resources (idempotent)
- **POST**: Create new resources
- **PUT**: Full update of resource
- **PATCH**: Partial update of resource
- **DELETE**: Remove resource

### Request Headers

Required headers:
```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer {token}
```

Optional headers:
```http
X-Request-ID: {uuid}
X-Client-Version: 1.0.0
Accept-Language: en-US
```

### Request Body

```json
{
  "data": {
    "type": "user",
    "attributes": {
      "email": "user@example.com",
      "fullName": "John Doe"
    }
  }
}
```

## Response Standards

### Success Response Format

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "user",
    "attributes": {
      "email": "user@example.com",
      "fullName": "John Doe",
      "createdAt": "2025-01-07T10:30:00Z"
    }
  },
  "metadata": {
    "timestamp": "2025-01-07T10:30:00Z",
    "version": "1.0.0",
    "requestId": "req_123456"
  }
}
```

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid data",
    "type": "validation_error",
    "timestamp": "2025-01-07T10:30:00Z",
    "details": [
      {
        "field": "email",
        "message": "Email format is invalid",
        "code": "INVALID_EMAIL"
      }
    ]
  },
  "metadata": {
    "requestId": "req_123456",
    "documentation": "https://docs.boardroom.ai/errors/VALIDATION_ERROR"
  }
}
```

### HTTP Status Codes

**Success Codes:**
- `200 OK`: Successful GET, PUT, PATCH
- `201 Created`: Successful POST
- `204 No Content`: Successful DELETE
- `202 Accepted`: Async operation started

**Client Error Codes:**
- `400 Bad Request`: Invalid request format
- `401 Unauthorized`: Missing/invalid authentication
- `403 Forbidden`: Authenticated but not authorized
- `404 Not Found`: Resource doesn't exist
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded

**Server Error Codes:**
- `500 Internal Server Error`: Unexpected error
- `502 Bad Gateway`: Upstream service error
- `503 Service Unavailable`: Maintenance/overload

## Authentication

### JWT Bearer Token

Request:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Token payload:
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "exp": 1704628800,
  "iat": 1704542400,
  "type": "access"
}
```

### Authentication Flow

```
1. POST /api/v1/auth/login
   Request: { "email": "...", "password": "..." }
   Response: { "accessToken": "...", "expiresIn": 86400 }

2. Use token in subsequent requests:
   Authorization: Bearer {accessToken}

3. Refresh before expiration:
   POST /api/v1/auth/refresh
```

## Pagination

### Request Parameters

```
GET /api/v1/users?page=1&limit=20&sort=-createdAt&filter[isActive]=true
```

Parameters:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `sort`: Sort field with `-` prefix for descending
- `filter[field]`: Field-specific filters

### Paginated Response

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 156,
    "pages": 8,
    "hasNext": true,
    "hasPrev": false
  },
  "links": {
    "first": "/api/v1/users?page=1&limit=20",
    "last": "/api/v1/users?page=8&limit=20",
    "next": "/api/v1/users?page=2&limit=20",
    "prev": null
  }
}
```

## Filtering and Searching

### Filter Syntax

```
# Exact match
GET /api/v1/users?filter[email]=user@example.com

# Partial match
GET /api/v1/users?filter[name]=John

# Range
GET /api/v1/users?filter[createdAt][gte]=2025-01-01&filter[createdAt][lt]=2025-02-01

# Multiple values
GET /api/v1/users?filter[status]=active,pending
```

### Search

```
# Full-text search
GET /api/v1/boardrooms?search=meeting+notes

# Field-specific search
GET /api/v1/users?search[email]=@example.com
```

## Rate Limiting

### Headers

Response headers:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 57
X-RateLimit-Reset: 1704628800
Retry-After: 3600
```

### Rate Limit Response

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "type": "rate_limit_error",
    "retryAfter": 3600
  }
}
```

### Limits by Endpoint

- Authentication: 5 requests/minute
- Chat operations: 30 requests/minute
- General API: 60 requests/minute
- Bulk operations: 10 requests/hour

## Async Operations

### Long-Running Tasks

Request:
```
POST /api/v1/reports/generate
```

Response:
```json
{
  "statusUrl": "/api/v1/operations/op_123456",
  "operationId": "op_123456",
  "status": "pending"
}
```

### Status Polling

```
GET /api/v1/operations/op_123456
```

Response:
```json
{
  "operationId": "op_123456",
  "status": "completed",
  "progress": 100,
  "result": {
    "reportUrl": "/api/v1/reports/rpt_789012"
  }
}
```

## Webhooks (Future)

### Webhook Payload

```json
{
  "id": "evt_123456",
  "type": "session.completed",
  "data": {
    "sessionId": "ses_789012",
    "completedAt": "2025-01-07T10:30:00Z"
  },
  "metadata": {
    "timestamp": "2025-01-07T10:30:01Z",
    "signature": "sha256=..."
  }
}
```

## API Security

### Input Validation

1. **Type validation**: Enforce data types
2. **Length limits**: Prevent buffer overflows
3. **Format validation**: Email, UUID, dates
4. **Sanitization**: Remove dangerous characters
5. **SQL injection prevention**: Parameterized queries

### Security Headers

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
```

## Performance Patterns

### Caching

Cache headers:
```http
Cache-Control: private, max-age=300
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
Last-Modified: Wed, 21 Oct 2024 07:28:00 GMT
```

### Compression

```http
Accept-Encoding: gzip, deflate
Content-Encoding: gzip
```

### Field Selection

```
# Request only needed fields
GET /api/v1/users/123?fields=id,email,fullName
```

## API Documentation

### OpenAPI/Swagger

Access at: `/docs` or `/redoc`

Features:
- Interactive API testing
- Request/response examples
- Authentication testing
- Schema definitions

### Endpoint Documentation

Each endpoint should include:
- Description
- Parameters with types
- Request/response examples
- Error scenarios
- Rate limits

## Deprecation Policy

### Deprecation Timeline

1. **Announcement**: 3 months before deprecation
2. **Warning headers**: `Deprecation: true`
3. **Sunset header**: `Sunset: Sat, 1 Jan 2025 00:00:00 GMT`
4. **Migration guide**: Documentation for alternatives
5. **Removal**: After sunset date

### Deprecation Response

```http
Deprecation: true
Sunset: Sat, 1 Jan 2025 00:00:00 GMT
Link: <https://docs.boardroom.ai/migrations/v2>; rel="deprecation"
```

## Best Practices

### Do's
1. ✅ Use consistent naming conventions
2. ✅ Provide meaningful error messages
3. ✅ Version your API
4. ✅ Use appropriate HTTP status codes
5. ✅ Implement proper pagination
6. ✅ Document all endpoints

### Don'ts
1. ❌ Use verbs in endpoint names
2. ❌ Return HTML from API endpoints
3. ❌ Expose internal errors
4. ❌ Use GET for state changes
5. ❌ Ignore rate limiting
6. ❌ Break backwards compatibility

## Related Documentation

- [System Architecture](./system_overview.md)
- [Authentication Guide](../api/authentication.md)
- [API Quick Start](../api/quick_start.md)
- [Error Reference](../api/errors.md)

---

**API Support**: Check `/docs` for interactive documentation or contact the development team.