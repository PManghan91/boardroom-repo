# Integration Basics

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: Developers / Integration Partners  
**Next Review**: With API updates  

## Overview

This guide covers the basics of integrating with Boardroom AI's API. Whether you're building a custom integration, connecting existing tools, or embedding our functionality into your application, this document will help you get started.

## Integration Patterns

### 1. Direct API Integration

The most common integration pattern - directly calling our RESTful API:

```javascript
// Example: Create a chat session
const response = await fetch('https://api.boardroom.ai/api/v1/chatbot/chat', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'Help me plan a board meeting',
    session_id: sessionId
  })
});

const data = await response.json();
console.log(data.response);
```

### 2. Webhook Integration (Future)

Subscribe to events and receive real-time updates:

```javascript
// Future: Subscribe to meeting completed events
const subscription = await fetch('https://api.boardroom.ai/api/v1/webhooks', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://your-app.com/webhooks/boardroom',
    events: ['session.completed', 'decision.created']
  })
});
```

### 3. Embedded Widget (Future)

Embed Boardroom AI chat directly in your application:

```html
<!-- Future: Embedded chat widget -->
<script src="https://cdn.boardroom.ai/widget.js"></script>
<div id="boardroom-chat"></div>
<script>
  BoardroomAI.init({
    apiKey: 'your-api-key',
    container: '#boardroom-chat',
    theme: 'light'
  });
</script>
```

## Authentication Methods

### API Key Authentication

Best for server-to-server integration:

```python
import requests

headers = {
    'Authorization': 'Bearer your-api-key',
    'Content-Type': 'application/json'
}

response = requests.post(
    'https://api.boardroom.ai/api/v1/chatbot/chat',
    headers=headers,
    json={'message': 'Hello'}
)
```

### OAuth 2.0 Flow (Future)

For user-authorized integrations:

```javascript
// 1. Redirect user to authorize
window.location.href = 'https://boardroom.ai/oauth/authorize?' +
  'client_id=your-client-id&' +
  'redirect_uri=https://your-app.com/callback&' +
  'response_type=code&' +
  'scope=chat:read chat:write';

// 2. Exchange code for token
const tokenResponse = await fetch('https://api.boardroom.ai/oauth/token', {
  method: 'POST',
  body: new URLSearchParams({
    grant_type: 'authorization_code',
    code: authCode,
    client_id: clientId,
    client_secret: clientSecret
  })
});
```

## Common Integration Scenarios

### 1. Slack Integration

Send Boardroom AI responses to Slack:

```python
# Handle Slack slash command
@app.route('/slack/boardroom', methods=['POST'])
def slack_boardroom():
    text = request.form.get('text')
    
    # Call Boardroom AI
    boardroom_response = boardroom_ai.chat(text)
    
    # Format for Slack
    return {
        "response_type": "in_channel",
        "text": boardroom_response.content,
        "attachments": [{
            "color": "good",
            "title": "Boardroom AI Response",
            "text": boardroom_response.content
        }]
    }
```

### 2. Calendar Integration

Sync meeting data with calendar systems:

```javascript
// Example: Google Calendar integration
async function createMeetingFromBoardroom(sessionId) {
  // Get meeting details from Boardroom AI
  const session = await boardroomAPI.getSession(sessionId);
  
  // Create calendar event
  const event = {
    summary: session.title,
    description: session.summary,
    start: { dateTime: session.startTime },
    end: { dateTime: session.endTime },
    attendees: session.participants.map(p => ({ email: p.email }))
  };
  
  await calendar.events.insert({
    calendarId: 'primary',
    resource: event
  });
}
```

### 3. CRM Integration

Sync decision data with your CRM:

```python
# Salesforce integration example
def sync_decision_to_salesforce(decision_data):
    # Map Boardroom AI decision to Salesforce object
    sf_record = {
        'Name': decision_data['title'],
        'Description__c': decision_data['description'],
        'Decision_Date__c': decision_data['created_at'],
        'Status__c': decision_data['status'],
        'Boardroom_ID__c': decision_data['id']
    }
    
    # Create or update in Salesforce
    sf.Custom_Decision__c.upsert(
        'Boardroom_ID__c/' + decision_data['id'],
        sf_record
    )
```

### 4. Analytics Integration

Send conversation data to your analytics platform:

```javascript
// Send to analytics platform
function trackBoardroomInteraction(event, properties) {
  // Google Analytics
  gtag('event', event, {
    'event_category': 'boardroom_ai',
    'event_label': properties.sessionId,
    'value': properties.messageCount
  });
  
  // Mixpanel
  mixpanel.track('Boardroom AI ' + event, properties);
  
  // Segment
  analytics.track({
    userId: properties.userId,
    event: 'Boardroom AI ' + event,
    properties: properties
  });
}
```

## SDK Examples (Community)

### Python SDK Example

```python
from boardroom_ai import BoardroomClient

# Initialize client
client = BoardroomClient(api_key='your-api-key')

# Simple chat
response = client.chat.send_message(
    message="Help me prepare for a board meeting",
    session_id="optional-session-id"
)

print(response.content)

# Streaming chat
for chunk in client.chat.stream_message("What should we discuss?"):
    print(chunk.content, end='')
```

### Node.js SDK Example

```javascript
const { BoardroomAI } = require('boardroom-ai-sdk');

// Initialize
const boardroom = new BoardroomAI({
  apiKey: process.env.BOARDROOM_API_KEY
});

// Async/await pattern
async function askBoardroom() {
  const response = await boardroom.chat.send({
    message: 'Create a meeting agenda',
    sessionId: 'my-session'
  });
  
  console.log(response.content);
}

// Promise pattern
boardroom.chat.send({ message: 'Hello' })
  .then(response => console.log(response))
  .catch(error => console.error(error));
```

## Data Formats

### Request Formats

All requests should be JSON:

```json
{
  "message": "Your message here",
  "session_id": "optional-session-id",
  "context": {
    "meeting_type": "board_meeting",
    "participants": 5
  }
}
```

### Response Formats

Standard response structure:

```json
{
  "success": true,
  "data": {
    "response": "AI response text",
    "session_id": "session-123",
    "message_id": "msg-456",
    "metadata": {
      "tokens_used": 150,
      "processing_time_ms": 1234
    }
  }
}
```

### Error Formats

Consistent error structure:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "retry_after": 60,
      "limit": 30
    }
  }
}
```

## Best Practices

### 1. Error Handling

Always implement robust error handling:

```javascript
async function safeBoardroomCall(message) {
  try {
    const response = await boardroomAPI.chat(message);
    return response;
  } catch (error) {
    if (error.code === 'RATE_LIMIT_EXCEEDED') {
      // Wait and retry
      await sleep(error.retryAfter * 1000);
      return safeBoardroomCall(message);
    } else if (error.code === 'UNAUTHORIZED') {
      // Refresh token
      await refreshAuthToken();
      return safeBoardroomCall(message);
    } else {
      // Log and handle gracefully
      console.error('Boardroom AI error:', error);
      return { error: 'Service temporarily unavailable' };
    }
  }
}
```

### 2. Rate Limiting

Respect rate limits:

```python
import time
from functools import wraps

def rate_limit_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                retry_count += 1
                wait_time = e.retry_after or (2 ** retry_count)
                time.sleep(wait_time)
        
        raise Exception("Max retries exceeded")
    
    return wrapper

@rate_limit_handler
def call_boardroom_api(message):
    return boardroom_client.chat(message)
```

### 3. Caching

Cache responses when appropriate:

```javascript
const cache = new Map();

async function getCachedResponse(message, sessionId) {
  const cacheKey = `${sessionId}:${message}`;
  
  // Check cache
  if (cache.has(cacheKey)) {
    const cached = cache.get(cacheKey);
    if (Date.now() - cached.timestamp < 3600000) { // 1 hour
      return cached.data;
    }
  }
  
  // Fetch fresh data
  const response = await boardroomAPI.chat(message, sessionId);
  
  // Cache it
  cache.set(cacheKey, {
    data: response,
    timestamp: Date.now()
  });
  
  return response;
}
```

### 4. Security

Keep your integration secure:

```python
# Never expose API keys in client-side code
# Bad:
api_key = "sk-1234567890abcdef"  # Exposed!

# Good:
api_key = os.environ.get('BOARDROOM_API_KEY')

# Validate webhooks (future)
def validate_webhook(request):
    signature = request.headers.get('X-Boardroom-Signature')
    body = request.get_data()
    
    expected = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)
```

## Testing Your Integration

### 1. Use the Sandbox

Test in a safe environment:
```
https://sandbox-api.boardroom.ai/api/v1/
```

### 2. Test Data

Use test sessions and data:
```javascript
const TEST_SESSION = 'test-session-123';
const TEST_USER = 'test@example.com';
```

### 3. Integration Tests

Write comprehensive tests:

```python
def test_boardroom_integration():
    # Test authentication
    assert boardroom_client.authenticate() == True
    
    # Test basic chat
    response = boardroom_client.chat("Hello")
    assert response.success == True
    assert len(response.content) > 0
    
    # Test error handling
    with pytest.raises(RateLimitError):
        for _ in range(100):
            boardroom_client.chat("Test")
```

## Support Resources

### Documentation
- **API Reference**: https://api.boardroom.ai/docs
- **Status Page**: https://status.boardroom.ai
- **Changelog**: https://docs.boardroom.ai/changelog

### Community
- **GitHub**: https://github.com/boardroom-ai
- **Discord**: https://discord.gg/boardroom-ai
- **Stack Overflow**: Tag `boardroom-ai`

### Direct Support
- **Email**: integrations@boardroom.ai
- **Developer Portal**: https://developers.boardroom.ai

## Related Documentation

- [API Quick Start](../api/quick_start.md)
- [API Design Patterns](../architecture/api_design.md)
- [Authentication Guide](../api/authentication.md)
- [Webhook Reference](../api/webhooks.md) (Future)

---

**Building something cool?** Let us know! We love featuring community integrations.