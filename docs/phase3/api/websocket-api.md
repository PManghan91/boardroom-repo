# WebSocket API Reference

## Overview

The Boardroom WebSocket API enables real-time bidirectional communication between the client and server. This API powers live features such as real-time collaboration, instant notifications, presence tracking, and live voting.

## Connection

### WebSocket URL

```
wss://api.boardroom.com/ws?token={JWT_TOKEN}
```

### Connection Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| token | string | Yes | JWT authentication token |
| clientId | string | No | Unique client identifier for session tracking |
| version | string | No | API version (default: "1.0") |

### Connection Example

```typescript
const token = await getAuthToken()
const ws = new WebSocket(`wss://api.boardroom.com/ws?token=${token}`)

ws.onopen = () => {
  console.log('Connected to Boardroom WebSocket')
}

ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  handleMessage(message)
}

ws.onerror = (error) => {
  console.error('WebSocket error:', error)
}

ws.onclose = (event) => {
  console.log('WebSocket closed:', event.code, event.reason)
}
```

## Message Format

### Standard Message Structure

All WebSocket messages follow this structure:

```json
{
  "id": "unique-message-id",
  "type": "message.type",
  "data": {
    // Message-specific payload
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "userId": "user_123",
    "correlationId": "req_456",
    "version": "1.0"
  }
}
```

### Message Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique message identifier |
| type | string | Message type (dot-notation) |
| data | object | Message payload |
| metadata | object | Message metadata |

## Event Types

### Connection Events

#### connection.ready
Sent by server when connection is established and authenticated.

```json
{
  "type": "connection.ready",
  "data": {
    "sessionId": "session_123",
    "userId": "user_456",
    "permissions": ["read", "write"],
    "serverTime": "2024-01-15T10:30:00Z"
  }
}
```

#### connection.error
Sent when a connection error occurs.

```json
{
  "type": "connection.error",
  "data": {
    "code": "AUTH_FAILED",
    "message": "Authentication token expired",
    "retryable": true
  }
}
```

#### connection.heartbeat
Keep-alive ping/pong messages.

Client sends:
```json
{
  "type": "connection.heartbeat.ping",
  "data": {
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

Server responds:
```json
{
  "type": "connection.heartbeat.pong",
  "data": {
    "timestamp": "2024-01-15T10:30:00Z",
    "latency": 23
  }
}
```

### Meeting Events

#### meeting.join
Join a meeting room.

Client sends:
```json
{
  "type": "meeting.join",
  "data": {
    "meetingId": "meeting_123",
    "role": "participant"
  }
}
```

Server broadcasts:
```json
{
  "type": "meeting.participant.joined",
  "data": {
    "meetingId": "meeting_123",
    "participant": {
      "userId": "user_456",
      "name": "John Doe",
      "role": "participant",
      "joinedAt": "2024-01-15T10:30:00Z"
    },
    "totalParticipants": 5
  }
}
```

#### meeting.leave
Leave a meeting room.

Client sends:
```json
{
  "type": "meeting.leave",
  "data": {
    "meetingId": "meeting_123"
  }
}
```

Server broadcasts:
```json
{
  "type": "meeting.participant.left",
  "data": {
    "meetingId": "meeting_123",
    "participant": {
      "userId": "user_456",
      "name": "John Doe",
      "leftAt": "2024-01-15T10:35:00Z"
    },
    "totalParticipants": 4
  }
}
```

#### meeting.chat.message
Send a chat message in a meeting.

Client sends:
```json
{
  "type": "meeting.chat.message",
  "data": {
    "meetingId": "meeting_123",
    "message": "Hello everyone!",
    "replyTo": null
  }
}
```

Server broadcasts:
```json
{
  "type": "meeting.chat.message",
  "data": {
    "meetingId": "meeting_123",
    "messageId": "msg_789",
    "userId": "user_456",
    "userName": "John Doe",
    "message": "Hello everyone!",
    "replyTo": null,
    "timestamp": "2024-01-15T10:31:00Z"
  }
}
```

#### meeting.agenda.update
Update meeting agenda progress.

Server sends:
```json
{
  "type": "meeting.agenda.update",
  "data": {
    "meetingId": "meeting_123",
    "currentItem": 3,
    "totalItems": 5,
    "itemDetails": {
      "id": "item_3",
      "title": "Budget Review",
      "status": "in_progress",
      "startedAt": "2024-01-15T10:32:00Z"
    }
  }
}
```

### Decision Events

#### decision.vote.cast
Cast a vote on a decision.

Client sends:
```json
{
  "type": "decision.vote.cast",
  "data": {
    "decisionId": "decision_123",
    "vote": "approve",
    "comment": "Looks good to me"
  }
}
```

Server responds:
```json
{
  "type": "decision.vote.received",
  "data": {
    "decisionId": "decision_123",
    "voteId": "vote_456",
    "status": "recorded",
    "timestamp": "2024-01-15T10:33:00Z"
  }
}
```

Server broadcasts:
```json
{
  "type": "decision.vote.update",
  "data": {
    "decisionId": "decision_123",
    "voteSummary": {
      "approve": 8,
      "reject": 2,
      "abstain": 1,
      "total": 11,
      "required": 15
    },
    "status": "voting",
    "deadline": "2024-01-15T12:00:00Z"
  }
}
```

#### decision.result
Final decision result.

Server sends:
```json
{
  "type": "decision.result",
  "data": {
    "decisionId": "decision_123",
    "result": "approved",
    "finalVotes": {
      "approve": 12,
      "reject": 2,
      "abstain": 1
    },
    "completedAt": "2024-01-15T11:00:00Z"
  }
}
```

### Presence Events

#### presence.update
Update user presence status.

Client sends:
```json
{
  "type": "presence.update",
  "data": {
    "status": "online",
    "activity": {
      "type": "viewing",
      "target": "meeting_123"
    }
  }
}
```

Server broadcasts:
```json
{
  "type": "presence.changed",
  "data": {
    "userId": "user_456",
    "status": "online",
    "activity": {
      "type": "viewing",
      "target": "meeting_123"
    },
    "lastSeen": "2024-01-15T10:35:00Z"
  }
}
```

#### presence.subscribe
Subscribe to presence updates for a room.

Client sends:
```json
{
  "type": "presence.subscribe",
  "data": {
    "roomId": "meeting_123"
  }
}
```

Server responds:
```json
{
  "type": "presence.list",
  "data": {
    "roomId": "meeting_123",
    "users": [
      {
        "userId": "user_456",
        "status": "online",
        "activity": {
          "type": "viewing",
          "target": "meeting_123"
        },
        "lastSeen": "2024-01-15T10:35:00Z"
      }
    ]
  }
}
```

### Notification Events

#### notification.send
Server sends notification to client.

```json
{
  "type": "notification.send",
  "data": {
    "notificationId": "notif_123",
    "priority": "high",
    "title": "Meeting Starting Soon",
    "message": "Board meeting starts in 5 minutes",
    "category": "meeting",
    "actions": [
      {
        "id": "join",
        "label": "Join Meeting",
        "url": "/meetings/123"
      }
    ],
    "expiresAt": "2024-01-15T10:40:00Z"
  }
}
```

#### notification.acknowledge
Acknowledge notification receipt.

Client sends:
```json
{
  "type": "notification.acknowledge",
  "data": {
    "notificationId": "notif_123"
  }
}
```

### Collaboration Events

#### collaboration.cursor
Share cursor position for collaborative editing.

Client sends:
```json
{
  "type": "collaboration.cursor",
  "data": {
    "documentId": "doc_123",
    "position": {
      "line": 10,
      "column": 25
    },
    "selection": {
      "start": { "line": 10, "column": 20 },
      "end": { "line": 10, "column": 30 }
    }
  }
}
```

Server broadcasts:
```json
{
  "type": "collaboration.cursor.update",
  "data": {
    "documentId": "doc_123",
    "userId": "user_456",
    "userName": "John Doe",
    "color": "#4A90E2",
    "position": {
      "line": 10,
      "column": 25
    },
    "selection": {
      "start": { "line": 10, "column": 20 },
      "end": { "line": 10, "column": 30 }
    }
  }
}
```

#### collaboration.typing
Typing indicator for collaborative features.

Client sends:
```json
{
  "type": "collaboration.typing",
  "data": {
    "roomId": "meeting_123",
    "isTyping": true
  }
}
```

Server broadcasts:
```json
{
  "type": "collaboration.typing.update",
  "data": {
    "roomId": "meeting_123",
    "userId": "user_456",
    "userName": "John Doe",
    "isTyping": true
  }
}
```

## Error Handling

### Error Response Format

```json
{
  "type": "error",
  "data": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional error context
    },
    "correlationId": "req_456",
    "retryable": true,
    "retryAfter": 5000
  }
}
```

### Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| AUTH_FAILED | Authentication failed | No |
| AUTH_EXPIRED | Token expired | Yes |
| PERMISSION_DENIED | Insufficient permissions | No |
| RATE_LIMITED | Too many requests | Yes |
| INVALID_MESSAGE | Message format invalid | No |
| RESOURCE_NOT_FOUND | Resource doesn't exist | No |
| CONNECTION_ERROR | Connection issue | Yes |
| SERVER_ERROR | Internal server error | Yes |

## Rate Limiting

### Limits

| Action | Limit | Window |
|--------|-------|---------|
| Messages per connection | 100 | 1 minute |
| Join meeting | 5 | 1 minute |
| Send chat message | 30 | 1 minute |
| Cast vote | 10 | 1 minute |
| Cursor updates | 60 | 1 second |

### Rate Limit Response

```json
{
  "type": "error",
  "data": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 100,
      "window": 60,
      "retryAfter": 45
    }
  }
}
```

## Subscriptions

### Subscribe to Channel

```json
{
  "type": "subscribe",
  "data": {
    "channels": [
      "meeting:123",
      "decision:456",
      "user:789"
    ]
  }
}
```

### Unsubscribe from Channel

```json
{
  "type": "unsubscribe",
  "data": {
    "channels": ["meeting:123"]
  }
}
```

### Subscription Response

```json
{
  "type": "subscription.update",
  "data": {
    "subscribed": ["meeting:123", "decision:456"],
    "failed": {
      "user:789": "Permission denied"
    }
  }
}
```

## Security

### Authentication

1. JWT token must be provided in connection URL
2. Token is validated on connection
3. Token refresh handled automatically
4. Connection closed on token expiration

### Authorization

1. Channel-based permissions
2. Message-level authorization
3. Resource access control
4. Role-based restrictions

### Encryption

1. All connections use WSS (WebSocket Secure)
2. TLS 1.3 minimum
3. Message payload encryption for sensitive data
4. End-to-end encryption for private messages

## Client Libraries

### JavaScript/TypeScript

```typescript
import { BoardroomWebSocket } from '@boardroom/websocket-client'

const client = new BoardroomWebSocket({
  url: 'wss://api.boardroom.com/ws',
  token: authToken,
  reconnect: true,
  debug: process.env.NODE_ENV === 'development'
})

client.on('meeting.participant.joined', (data) => {
  console.log('Participant joined:', data.participant)
})

client.subscribe('meeting:123')
client.send('meeting.chat.message', {
  meetingId: '123',
  message: 'Hello!'
})
```

### Python

```python
from boardroom_ws import BoardroomWebSocket

client = BoardroomWebSocket(
    url="wss://api.boardroom.com/ws",
    token=auth_token,
    reconnect=True
)

@client.on("meeting.participant.joined")
def on_participant_joined(data):
    print(f"Participant joined: {data['participant']}")

client.subscribe("meeting:123")
client.send("meeting.chat.message", {
    "meetingId": "123",
    "message": "Hello!"
})

client.connect()
```

## Best Practices

### Connection Management

1. Implement exponential backoff for reconnection
2. Handle connection lifecycle properly
3. Clean up subscriptions on disconnect
4. Monitor connection health with heartbeats

### Message Handling

1. Always validate incoming messages
2. Handle unknown message types gracefully
3. Implement proper error handling
4. Use correlation IDs for request tracking

### Performance

1. Batch multiple operations when possible
2. Throttle high-frequency updates
3. Implement client-side caching
4. Use compression for large payloads

### Security

1. Never expose tokens in logs
2. Validate all input data
3. Implement rate limiting on client
4. Handle authentication errors properly

## Examples

### Complete Connection Flow

```typescript
class BoardroomConnection {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  
  async connect(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`wss://api.boardroom.com/ws?token=${token}`)
      
      this.ws.onopen = () => {
        console.log('Connected')
        this.reconnectAttempts = 0
        resolve()
      }
      
      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data)
        this.handleMessage(message)
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
      
      this.ws.onclose = (event) => {
        console.log('Disconnected:', event.code, event.reason)
        
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect(token)
        }
      }
    })
  }
  
  private scheduleReconnect(token: string): void {
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts)
    this.reconnectAttempts++
    
    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`)
      this.connect(token)
    }, delay)
  }
  
  private handleMessage(message: any): void {
    switch (message.type) {
      case 'connection.ready':
        this.onConnectionReady(message.data)
        break
      case 'meeting.participant.joined':
        this.onParticipantJoined(message.data)
        break
      case 'error':
        this.handleError(message.data)
        break
      default:
        console.log('Unknown message type:', message.type)
    }
  }
}
```

### Live Voting Implementation

```typescript
class LiveVoting {
  constructor(private ws: BoardroomWebSocket) {}
  
  async joinVotingSession(decisionId: string): Promise<void> {
    // Subscribe to decision updates
    await this.ws.subscribe(`decision:${decisionId}`)
    
    // Listen for vote updates
    this.ws.on('decision.vote.update', (data) => {
      if (data.decisionId === decisionId) {
        this.updateVoteDisplay(data.voteSummary)
      }
    })
    
    // Listen for final result
    this.ws.on('decision.result', (data) => {
      if (data.decisionId === decisionId) {
        this.displayFinalResult(data)
      }
    })
  }
  
  async castVote(decisionId: string, vote: string, comment?: string): Promise<void> {
    try {
      const response = await this.ws.sendAndWait('decision.vote.cast', {
        decisionId,
        vote,
        comment
      })
      
      if (response.data.status === 'recorded') {
        console.log('Vote recorded successfully')
      }
    } catch (error) {
      console.error('Failed to cast vote:', error)
    }
  }
}
```

---

For more information, see the [Real-Time Collaboration Features](../features/real-time-collaboration.md) or the [WebSocket Service Implementation](../../src/services/websocket.service.ts).