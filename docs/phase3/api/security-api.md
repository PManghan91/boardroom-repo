# Security API Reference

## Overview

The Security API provides comprehensive endpoints for authentication, authorization, multi-factor authentication (MFA), session management, and security monitoring. These endpoints ensure secure access to the Boardroom platform while maintaining user privacy and data protection.

## Base URL

```
https://api.boardroom.com/api/v1/security
```

## Authentication Methods

### JWT Authentication

Most endpoints require JWT authentication:

```http
Authorization: Bearer <JWT_TOKEN>
```

### API Key Authentication

For service-to-service communication:

```http
X-API-Key: <API_KEY>
X-API-Secret: <API_SECRET>
```

## Endpoints

### Authentication

#### Login

Authenticate user and receive tokens.

```http
POST /auth/login
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "deviceInfo": {
    "deviceId": "device_123",
    "platform": "web",
    "userAgent": "Mozilla/5.0...",
    "fingerprint": "abc123..."
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
    "expiresIn": 3600,
    "tokenType": "Bearer",
    "user": {
      "id": "user_123",
      "email": "user@example.com",
      "name": "John Doe",
      "roles": ["board_member", "admin"],
      "mfaEnabled": true,
      "requiresMfa": true
    },
    "session": {
      "id": "session_456",
      "deviceId": "device_123",
      "createdAt": "2024-01-15T10:30:00Z"
    }
  }
}
```

**Error Response (MFA Required):**

```json
{
  "success": false,
  "error": {
    "code": "MFA_REQUIRED",
    "message": "Multi-factor authentication required",
    "details": {
      "challengeToken": "challenge_789",
      "methods": ["totp", "sms"]
    }
  }
}
```

#### MFA Verification

Complete login with MFA code.

```http
POST /auth/mfa/verify
```

**Request Body:**

```json
{
  "challengeToken": "challenge_789",
  "code": "123456",
  "method": "totp",
  "trustDevice": true
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
    "expiresIn": 3600,
    "trustedDevice": {
      "id": "trusted_device_123",
      "expiresAt": "2024-02-15T10:30:00Z"
    }
  }
}
```

#### Logout

Terminate session and revoke tokens.

```http
POST /auth/logout
```

**Request Body:**

```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
  "allSessions": false
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "message": "Successfully logged out",
    "sessionsTerminated": 1
  }
}
```

#### Refresh Token

Get new access token using refresh token.

```http
POST /auth/refresh
```

**Request Body:**

```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "expiresIn": 3600
  }
}
```

#### Password Reset Request

Request password reset email.

```http
POST /auth/password/reset-request
```

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "message": "Password reset email sent",
    "expiresIn": 3600
  }
}
```

#### Password Reset

Reset password with token.

```http
POST /auth/password/reset
```

**Request Body:**

```json
{
  "token": "reset_token_123",
  "newPassword": "NewSecurePassword123!",
  "confirmPassword": "NewSecurePassword123!"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "message": "Password successfully reset",
    "requiresLogin": true
  }
}
```

### Multi-Factor Authentication

#### Initialize MFA

Set up MFA for user account.

```http
POST /mfa/initialize
```

**Headers:**

```http
Authorization: Bearer <JWT_TOKEN>
```

**Response:**

```json
{
  "success": true,
  "data": {
    "secret": "JBSWY3DPEHPK3PXP",
    "qrCode": "data:image/png;base64,iVBORw0KGgo...",
    "manualEntry": "boardroom:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Boardroom",
    "backupCodes": []
  }
}
```

#### Enable MFA

Confirm MFA setup with verification code.

```http
POST /mfa/enable
```

**Request Body:**

```json
{
  "code": "123456",
  "secret": "JBSWY3DPEHPK3PXP"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "mfaEnabled": true,
    "backupCodes": [
      "A1B2-C3D4",
      "E5F6-G7H8",
      "I9J0-K1L2",
      "M3N4-O5P6",
      "Q7R8-S9T0",
      "U1V2-W3X4",
      "Y5Z6-A7B8",
      "C9D0-E1F2"
    ],
    "methods": ["totp"]
  }
}
```

#### Disable MFA

Disable MFA with verification.

```http
POST /mfa/disable
```

**Request Body:**

```json
{
  "password": "CurrentPassword123!",
  "code": "123456"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "mfaEnabled": false,
    "message": "MFA successfully disabled"
  }
}
```

#### Generate Backup Codes

Generate new backup codes.

```http
POST /mfa/backup-codes/generate
```

**Request Body:**

```json
{
  "password": "CurrentPassword123!"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "backupCodes": [
      "A1B2-C3D4",
      "E5F6-G7H8",
      "I9J0-K1L2",
      "M3N4-O5P6",
      "Q7R8-S9T0",
      "U1V2-W3X4",
      "Y5Z6-A7B8",
      "C9D0-E1F2"
    ],
    "generatedAt": "2024-01-15T10:30:00Z"
  }
}
```

### Session Management

#### List Sessions

Get all active sessions.

```http
GET /sessions
```

**Response:**

```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": "session_123",
        "deviceId": "device_123",
        "deviceName": "Chrome on MacOS",
        "ipAddress": "192.168.1.100",
        "location": {
          "city": "San Francisco",
          "country": "US",
          "coordinates": {
            "lat": 37.7749,
            "lng": -122.4194
          }
        },
        "createdAt": "2024-01-15T10:30:00Z",
        "lastActivity": "2024-01-15T11:45:00Z",
        "current": true,
        "trusted": true
      }
    ],
    "total": 3,
    "activeSessions": 2
  }
}
```

#### Get Session Details

Get detailed session information.

```http
GET /sessions/{sessionId}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "session_123",
      "deviceInfo": {
        "deviceId": "device_123",
        "platform": "web",
        "browser": "Chrome",
        "browserVersion": "120.0",
        "os": "MacOS",
        "osVersion": "14.0"
      },
      "security": {
        "riskScore": 15,
        "riskFactors": ["new_location"],
        "verified": true
      },
      "activity": {
        "loginAt": "2024-01-15T10:30:00Z",
        "lastActivity": "2024-01-15T11:45:00Z",
        "actions": 145,
        "apiCalls": 523
      }
    }
  }
}
```

#### Terminate Session

End a specific session.

```http
DELETE /sessions/{sessionId}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "terminated": true,
    "sessionId": "session_123",
    "terminatedAt": "2024-01-15T12:00:00Z"
  }
}
```

#### Terminate All Sessions

End all sessions except current.

```http
POST /sessions/terminate-all
```

**Request Body:**

```json
{
  "includeCurrent": false,
  "password": "CurrentPassword123!"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "terminatedSessions": 2,
    "remainingSessions": 1
  }
}
```

### Authorization

#### Check Permissions

Verify user permissions.

```http
POST /permissions/check
```

**Request Body:**

```json
{
  "resource": "boardroom",
  "action": "create",
  "context": {
    "organizationId": "org_123"
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "allowed": true,
    "permissions": {
      "resource": "boardroom",
      "action": "create",
      "constraints": {
        "maxBoardrooms": 10,
        "allowedTypes": ["public", "private"]
      }
    },
    "roles": ["board_admin", "organization_owner"]
  }
}
```

#### Get User Permissions

Get all permissions for current user.

```http
GET /permissions
```

**Response:**

```json
{
  "success": true,
  "data": {
    "permissions": [
      {
        "resource": "boardroom",
        "actions": ["create", "read", "update", "delete"],
        "constraints": {
          "ownOnly": false,
          "maxItems": 10
        }
      },
      {
        "resource": "meeting",
        "actions": ["create", "read", "update"],
        "constraints": {
          "requiresApproval": true
        }
      }
    ],
    "roles": [
      {
        "id": "role_123",
        "name": "board_admin",
        "description": "Board Administrator"
      }
    ]
  }
}
```

#### Assign Role

Assign role to user (admin only).

```http
POST /roles/assign
```

**Request Body:**

```json
{
  "userId": "user_456",
  "roleId": "role_789",
  "expiresAt": "2024-12-31T23:59:59Z",
  "context": {
    "boardroomId": "boardroom_123"
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "assignment": {
      "id": "assignment_012",
      "userId": "user_456",
      "roleId": "role_789",
      "assignedAt": "2024-01-15T10:30:00Z",
      "expiresAt": "2024-12-31T23:59:59Z",
      "assignedBy": "user_123"
    }
  }
}
```

### Security Monitoring

#### Get Security Events

Retrieve security events.

```http
GET /events
```

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| type | string | No | Event type filter |
| severity | string | No | Severity level (low, medium, high, critical) |
| startDate | datetime | No | Start date filter |
| endDate | datetime | No | End date filter |
| page | integer | No | Page number |
| size | integer | No | Page size |

**Response:**

```json
{
  "success": true,
  "data": {
    "events": [
      {
        "id": "event_123",
        "type": "failed_login",
        "severity": "medium",
        "timestamp": "2024-01-15T10:30:00Z",
        "details": {
          "ipAddress": "192.168.1.100",
          "userAgent": "Mozilla/5.0...",
          "attemptedEmail": "user@example.com",
          "reason": "invalid_password"
        },
        "userId": null,
        "resolved": false
      }
    ],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 145
    }
  }
}
```

#### Get Security Metrics

Get security metrics dashboard data.

```http
GET /metrics
```

**Response:**

```json
{
  "success": true,
  "data": {
    "metrics": {
      "authentication": {
        "successfulLogins": 1234,
        "failedLogins": 45,
        "mfaUsage": 89.5,
        "averageSessionDuration": 3600
      },
      "threats": {
        "blockedAttempts": 123,
        "suspiciousActivities": 12,
        "activeThreats": 0,
        "riskScore": 25
      },
      "compliance": {
        "passwordCompliance": 95.5,
        "mfaCompliance": 89.5,
        "sessionCompliance": 98.2
      }
    },
    "trends": {
      "period": "7d",
      "failedLogins": [12, 8, 15, 6, 9, 11, 7],
      "successfulLogins": [180, 195, 175, 188, 201, 178, 165]
    }
  }
}
```

#### Report Security Incident

Report a security incident.

```http
POST /incidents
```

**Request Body:**

```json
{
  "type": "suspicious_activity",
  "severity": "high",
  "description": "Multiple failed login attempts from different IPs",
  "affectedResources": ["user_123"],
  "evidence": {
    "logs": ["log_entry_1", "log_entry_2"],
    "screenshots": ["screenshot_url"]
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "incident": {
      "id": "incident_456",
      "status": "investigating",
      "assignedTo": "security_team",
      "createdAt": "2024-01-15T10:30:00Z",
      "priority": "high"
    }
  }
}
```

### Password Management

#### Check Password Strength

Validate password strength.

```http
POST /password/check-strength
```

**Request Body:**

```json
{
  "password": "TestPassword123!"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "score": 85,
    "strength": "strong",
    "requirements": {
      "minLength": { "required": 12, "met": true },
      "uppercase": { "required": true, "met": true },
      "lowercase": { "required": true, "met": true },
      "numbers": { "required": true, "met": true },
      "symbols": { "required": true, "met": true }
    },
    "suggestions": [
      "Consider using a passphrase for better memorability"
    ],
    "commonPassword": false,
    "estimatedCrackTime": "2 years"
  }
}
```

#### Change Password

Change user password.

```http
POST /password/change
```

**Request Body:**

```json
{
  "currentPassword": "OldPassword123!",
  "newPassword": "NewSecurePassword456!",
  "logoutOtherSessions": true
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "changed": true,
    "sessionsTerminated": 2,
    "passwordExpiresAt": "2024-04-15T10:30:00Z"
  }
}
```

### Device Management

#### List Trusted Devices

Get trusted devices.

```http
GET /devices/trusted
```

**Response:**

```json
{
  "success": true,
  "data": {
    "devices": [
      {
        "id": "device_123",
        "name": "John's MacBook",
        "type": "laptop",
        "lastUsed": "2024-01-15T10:30:00Z",
        "trusted": true,
        "trustedAt": "2024-01-01T00:00:00Z",
        "expiresAt": "2024-02-01T00:00:00Z"
      }
    ]
  }
}
```

#### Revoke Device Trust

Remove device from trusted list.

```http
DELETE /devices/trusted/{deviceId}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "revoked": true,
    "deviceId": "device_123",
    "sessionsTerminated": 1
  }
}
```

### Audit Logs

#### Get Audit Logs

Retrieve audit logs.

```http
GET /audit-logs
```

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| userId | string | No | Filter by user |
| action | string | No | Filter by action |
| resource | string | No | Filter by resource |
| result | string | No | Filter by result (success/failure) |
| startDate | datetime | No | Start date |
| endDate | datetime | No | End date |

**Response:**

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "log_123",
        "userId": "user_456",
        "action": "boardroom.create",
        "resource": "boardroom",
        "resourceId": "boardroom_789",
        "result": "success",
        "timestamp": "2024-01-15T10:30:00Z",
        "metadata": {
          "ipAddress": "192.168.1.100",
          "userAgent": "Mozilla/5.0...",
          "duration": 234
        }
      }
    ],
    "pagination": {
      "page": 1,
      "size": 50,
      "total": 1234
    }
  }
}
```

## Security Headers

All responses include security headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## Rate Limiting

Security endpoints have stricter rate limits:

| Endpoint | Limit | Window |
|----------|-------|---------|
| Login | 5 | 15 minutes |
| Password reset | 3 | 1 hour |
| MFA verify | 5 | 5 minutes |
| Change password | 3 | 1 hour |

## Error Codes

| Code | Description |
|------|-------------|
| INVALID_CREDENTIALS | Invalid email or password |
| ACCOUNT_LOCKED | Account locked due to multiple failed attempts |
| MFA_REQUIRED | Multi-factor authentication required |
| INVALID_MFA_CODE | Invalid MFA code |
| SESSION_EXPIRED | Session has expired |
| INSUFFICIENT_PERMISSIONS | User lacks required permissions |
| PASSWORD_TOO_WEAK | Password doesn't meet requirements |
| DEVICE_NOT_TRUSTED | Device requires verification |

## SDK Examples

### JavaScript/TypeScript

```typescript
import { SecurityClient } from '@boardroom/security-sdk'

const security = new SecurityClient({
  baseUrl: 'https://api.boardroom.com/api/v1',
  interceptors: {
    onAuthError: () => {
      // Redirect to login
    }
  }
})

// Login with MFA
try {
  const loginResult = await security.login({
    email: 'user@example.com',
    password: 'password'
  })
  
  if (loginResult.requiresMfa) {
    const mfaResult = await security.verifyMfa({
      challengeToken: loginResult.challengeToken,
      code: '123456'
    })
  }
} catch (error) {
  if (error.code === 'ACCOUNT_LOCKED') {
    // Handle locked account
  }
}

// Session management
const sessions = await security.getSessions()
await security.terminateSession(sessionId)

// Permission checking
const canCreate = await security.checkPermission({
  resource: 'boardroom',
  action: 'create'
})
```

### Python

```python
from boardroom_sdk import SecurityClient

security = SecurityClient(
    base_url="https://api.boardroom.com/api/v1"
)

# Enable MFA
mfa_setup = security.initialize_mfa()
print(f"Scan QR Code: {mfa_setup['qrCode']}")

# Verify and enable
security.enable_mfa(
    code=input("Enter code: "),
    secret=mfa_setup['secret']
)

# Monitor security events
events = security.get_security_events(
    severity="high",
    limit=10
)

for event in events:
    print(f"{event['type']}: {event['details']}")
```

---

For more information, see the [Security Features Documentation](../features/security-enhancements.md) or the [Authentication Guide](../../auth.md).