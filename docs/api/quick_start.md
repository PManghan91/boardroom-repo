# API Quick Start Guide

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: Developers integrating with Boardroom AI API  
**Next Review**: With API changes  

## Overview

The Boardroom AI API is a RESTful service built with FastAPI that provides AI-powered chat functionality, authentication, and various management endpoints. This guide will help you get started quickly with the most common use cases.

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://your-domain.com/api/v1
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

The API uses JWT (JSON Web Token) authentication. Most endpoints require authentication.

### 1. Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe"
  }'
```

**Response:**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_verified": false
  },
  "token": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=SecurePassword123!"
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 3. Using the Token

Include the token in the Authorization header for authenticated requests:

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

## Core Use Cases

### 1. AI Chat Conversation

Start a chat conversation with the AI assistant:

```bash
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the best way to run a board meeting?",
    "session_id": "optional-session-id"
  }'
```

**Response:**
```json
{
  "response": "Here are the key elements for running an effective board meeting...",
  "session_id": "550e8400-e29b-41d4-a716-446655440001",
  "message_id": "msg_123456",
  "created_at": "2025-01-07T10:30:00Z"
}
```

### 2. Streaming Chat Response

For real-time streaming responses:

```bash
curl -X POST http://localhost:8000/api/v1/chatbot/chat/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain corporate governance",
    "session_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

The response will be Server-Sent Events (SSE) stream.

### 3. Get Chat History

Retrieve previous conversations:

```bash
curl -X GET http://localhost:8000/api/v1/chatbot/history?session_id=SESSION_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. AI Operations

Execute specific AI workflows:

```bash
curl -X POST http://localhost:8000/api/v1/ai/operations/execute \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "summarize_meeting",
    "params": {
      "text": "Meeting transcript here...",
      "style": "executive_summary"
    }
  }'
```

## Common Patterns

### Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": 400,
    "message": "Invalid request parameters",
    "type": "validation_error",
    "timestamp": "2025-01-07T10:30:00Z",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  }
}
```

Common error codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

### Rate Limiting

The API implements rate limiting to prevent abuse:

- **Authentication endpoints**: 5 requests per minute
- **Chat endpoints**: 30 requests per minute
- **General endpoints**: 60 requests per minute

Rate limit headers:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 29
X-RateLimit-Reset: 1704628800
```

### Pagination

List endpoints support pagination:

```bash
curl -X GET "http://localhost:8000/api/v1/chatbot/history?limit=20&offset=0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response includes pagination metadata:
```json
{
  "items": [...],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

## Health Checks

### Basic Health Check
```bash
curl http://localhost:8000/health
```

### Detailed Health Status
```bash
curl http://localhost:8000/api/v1/health/services
```

## Code Examples

### Python Example

```python
import requests

# Configuration
API_BASE = "http://localhost:8000/api/v1"
email = "user@example.com"
password = "SecurePassword123!"

# Login
login_response = requests.post(
    f"{API_BASE}/auth/login",
    data={"username": email, "password": password}
)
token = login_response.json()["access_token"]

# Make authenticated request
headers = {"Authorization": f"Bearer {token}"}
chat_response = requests.post(
    f"{API_BASE}/chatbot/chat",
    headers=headers,
    json={
        "message": "What is the best way to run a board meeting?",
        "session_id": None
    }
)

print(chat_response.json()["response"])
```

### JavaScript/TypeScript Example

```typescript
// Using axios
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

// Login function
async function login(email: string, password: string) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  
  const response = await axios.post(`${API_BASE}/auth/login`, formData);
  return response.data.access_token;
}

// Chat function
async function chat(token: string, message: string) {
  const response = await axios.post(
    `${API_BASE}/chatbot/chat`,
    { message, session_id: null },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.data;
}

// Usage
const token = await login('user@example.com', 'SecurePassword123!');
const result = await chat(token, 'What is the best way to run a board meeting?');
console.log(result.response);
```

## Troubleshooting

### Authentication Issues

1. **Invalid token**: Ensure the token hasn't expired (24-hour lifetime)
2. **401 Unauthorized**: Check token is included in Authorization header
3. **Token format**: Must be `Bearer YOUR_TOKEN` (note the space)

### Rate Limiting

If you receive 429 errors:
1. Check the `X-RateLimit-Reset` header for reset time
2. Implement exponential backoff
3. Consider caching responses where appropriate

### Connection Issues

1. Verify the API is running: `curl http://localhost:8000/health`
2. Check CORS if calling from browser
3. Ensure correct port (8000 for development)

## Next Steps

1. Explore the full API documentation at `/docs`
2. Review [API Design Patterns](../architecture/api_design.md)
3. Check [Integration Basics](../integration/basics.md)
4. Set up monitoring with [Langfuse](https://langfuse.com)

## Additional Resources

- [Development Setup](../development/setup.md)
- [Authentication Details](../architecture/api_design.md#authentication)
- [Error Handling Guide](../operations/troubleshooting.md#api-errors)
- [API Change Notes](./changes.md)

---

**Need Help?** Check the interactive documentation at `/docs` or review the [Troubleshooting Guide](../operations/troubleshooting.md).