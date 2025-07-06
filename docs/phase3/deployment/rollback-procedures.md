# Rollback and Recovery Procedures

## Overview

This document provides comprehensive procedures for rolling back deployments and recovering from various failure scenarios. These procedures are critical for maintaining service availability and minimizing downtime during incidents.

## Rollback Decision Matrix

| Scenario | Severity | Rollback Time | Decision Maker | Procedure |
|----------|----------|---------------|----------------|-----------|
| Critical Security Vulnerability | Critical | Immediate | On-call Engineer | Emergency Rollback |
| Data Corruption | Critical | < 5 minutes | Engineering Lead | Database Rollback |
| Performance Degradation > 50% | High | < 15 minutes | DevOps Lead | Application Rollback |
| Feature Breaking Bug | Medium | < 30 minutes | Product Manager | Staged Rollback |
| Minor UI Issues | Low | Next Release | Engineering Team | Forward Fix |

## Pre-Rollback Checklist

### 1. Assess the Situation

```bash
#!/bin/bash
# assess_deployment.sh

echo "=== Deployment Health Check ==="

# Check application health
curl -f https://api.boardroom.com/api/v1/health || echo "API health check failed"

# Check error rates
ERROR_RATE=$(curl -s http://prometheus:9090/api/v1/query?query=rate\(http_requests_total\{status=~\"5..\"\}\[5m\]\) | jq '.data.result[0].value[1]')
echo "Current error rate: $ERROR_RATE"

# Check response times
RESPONSE_TIME=$(curl -s http://prometheus:9090/api/v1/query?query=http_request_duration_seconds_p95 | jq '.data.result[0].value[1]')
echo "P95 response time: $RESPONSE_TIME seconds"

# Check database connectivity
pg_isready -h $DB_HOST -p $DB_PORT || echo "Database connection failed"

# Check Redis connectivity
redis-cli -h $REDIS_HOST ping || echo "Redis connection failed"
```

### 2. Capture Current State

```bash
#!/bin/bash
# capture_state.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
STATE_DIR="/var/backups/rollback_state_$TIMESTAMP"
mkdir -p $STATE_DIR

# Capture logs
docker logs boardroom-frontend > $STATE_DIR/frontend.log 2>&1
docker logs boardroom-backend > $STATE_DIR/backend.log 2>&1

# Capture metrics
curl -s http://prometheus:9090/api/v1/query_range?query=up > $STATE_DIR/metrics.json

# Capture database state
pg_dump $DATABASE_URL | gzip > $STATE_DIR/database_backup.sql.gz

# Create manifest
cat > $STATE_DIR/manifest.json << EOF
{
  "timestamp": "$TIMESTAMP",
  "version": "$(git rev-parse HEAD)",
  "reason": "$ROLLBACK_REASON",
  "initiated_by": "$USER"
}
EOF

echo "State captured in $STATE_DIR"
```

## Application Rollback Procedures

### 1. Docker Compose Rollback

```bash
#!/bin/bash
# rollback_docker_compose.sh

# Set target version
TARGET_VERSION=${1:-"previous"}

echo "Rolling back to version: $TARGET_VERSION"

# Stop current deployment
docker-compose down

# Checkout target version
if [ "$TARGET_VERSION" = "previous" ]; then
  git checkout HEAD~1
else
  git checkout $TARGET_VERSION
fi

# Rebuild and deploy
docker-compose build
docker-compose up -d

# Verify deployment
sleep 30
./scripts/verify_deployment.sh
```

### 2. Kubernetes Rollback

#### Automatic Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/boardroom-frontend -n boardroom
kubectl rollout undo deployment/boardroom-backend -n boardroom

# Rollback to specific revision
kubectl rollout undo deployment/boardroom-backend --to-revision=3 -n boardroom

# Check rollout status
kubectl rollout status deployment/boardroom-frontend -n boardroom
kubectl rollout status deployment/boardroom-backend -n boardroom
```

#### Manual Rollback with Version

```yaml
# rollback-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boardroom-backend
  namespace: boardroom
spec:
  template:
    spec:
      containers:
      - name: backend
        image: boardroom/backend:v2.9.5  # Previous stable version
```

```bash
kubectl apply -f rollback-deployment.yaml
```

### 3. Blue-Green Rollback

```bash
#!/bin/bash
# blue_green_rollback.sh

# Current environment (blue or green)
CURRENT_ENV=$(kubectl get ingress boardroom-ingress -o jsonpath='{.spec.rules[0].http.paths[0].backend.service.name}' | grep -o 'blue\|green')

# Determine rollback environment
if [ "$CURRENT_ENV" = "blue" ]; then
  ROLLBACK_ENV="green"
else
  ROLLBACK_ENV="blue"
fi

echo "Rolling back from $CURRENT_ENV to $ROLLBACK_ENV"

# Switch traffic back
kubectl patch ingress boardroom-ingress --type=json -p='[
  {
    "op": "replace",
    "path": "/spec/rules/0/http/paths/0/backend/service/name",
    "value": "boardroom-'$ROLLBACK_ENV'"
  }
]'

# Verify traffic switch
sleep 10
curl -s https://boardroom.com/api/health | jq .
```

### 4. Canary Rollback

```bash
#!/bin/bash
# canary_rollback.sh

# Reset canary weight to 0
kubectl patch virtualservice boardroom-vs --type=json -p='[
  {
    "op": "replace",
    "path": "/spec/http/0/route/0/weight",
    "value": 100
  },
  {
    "op": "replace",
    "path": "/spec/http/0/route/1/weight",
    "value": 0
  }
]'

# Scale down canary deployment
kubectl scale deployment boardroom-backend-canary --replicas=0 -n boardroom

echo "Canary rollback completed"
```

## Database Rollback Procedures

### 1. Migration Rollback

```bash
#!/bin/bash
# database_rollback.sh

# Check current migration version
CURRENT_VERSION=$(alembic current)
echo "Current migration: $CURRENT_VERSION"

# Rollback to previous migration
alembic downgrade -1

# Verify rollback
NEW_VERSION=$(alembic current)
echo "Rolled back to: $NEW_VERSION"

# Run verification queries
psql $DATABASE_URL << EOF
-- Verify schema
\dt
-- Check data integrity
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM boardrooms;
EOF
```

### 2. Point-in-Time Recovery

```bash
#!/bin/bash
# pitr_recovery.sh

RECOVERY_TIME=${1:-"2024-01-15 10:00:00"}

echo "Recovering database to: $RECOVERY_TIME"

# Stop application connections
kubectl scale deployment boardroom-backend --replicas=0 -n boardroom

# Perform PITR
pg_restore \
  --dbname=$DATABASE_URL \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --recovery-target-time="$RECOVERY_TIME" \
  /backups/latest_backup.dump

# Verify recovery
psql $DATABASE_URL -c "SELECT current_timestamp, count(*) FROM audit_logs WHERE created_at > '$RECOVERY_TIME';"

# Restart application
kubectl scale deployment boardroom-backend --replicas=3 -n boardroom
```

### 3. Backup Restoration

```bash
#!/bin/bash
# restore_backup.sh

BACKUP_FILE=${1:-"/backups/latest_backup.sql.gz"}

# Validate backup file
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

# Create restoration point
pg_dump $DATABASE_URL | gzip > /backups/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz

# Stop applications
docker-compose stop backend worker

# Restore backup
gunzip -c $BACKUP_FILE | psql $DATABASE_URL

# Run post-restore validations
psql $DATABASE_URL << EOF
-- Verify tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- Check row counts
SELECT 'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'boardrooms', COUNT(*) FROM boardrooms
UNION ALL
SELECT 'meetings', COUNT(*) FROM meetings;
EOF

# Restart applications
docker-compose start backend worker
```

## Service-Specific Rollbacks

### 1. Frontend Rollback

```bash
#!/bin/bash
# frontend_rollback.sh

# For static sites with CDN
PREVIOUS_VERSION="v2.9.5"

# Rollback S3 deployment
aws s3 sync s3://boardroom-frontend-$PREVIOUS_VERSION/ s3://boardroom-frontend-production/ --delete

# Invalidate CDN cache
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
  --paths "/*"

# Update service worker
cat > public/service-worker.js << EOF
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
      );
    })
  );
});
EOF

# Verify rollback
curl -I https://boardroom.com | grep "x-version"
```

### 2. API Rollback

```bash
#!/bin/bash
# api_rollback.sh

# Get previous stable version
PREVIOUS_VERSION=$(kubectl rollout history deployment/boardroom-backend -n boardroom | tail -2 | head -1 | awk '{print $1}')

# Rollback API deployment
kubectl rollout undo deployment/boardroom-backend --to-revision=$PREVIOUS_VERSION -n boardroom

# Wait for rollout to complete
kubectl rollout status deployment/boardroom-backend -n boardroom

# Verify API functionality
./scripts/api_smoke_tests.sh
```

### 3. WebSocket Service Rollback

```bash
#!/bin/bash
# websocket_rollback.sh

# Gracefully disconnect clients
kubectl exec -it deployment/boardroom-websocket -n boardroom -- \
  python -c "
import redis
r = redis.Redis(host='redis', port=6379)
r.publish('websocket:broadcast', json.dumps({
  'type': 'maintenance',
  'message': 'Service will restart in 30 seconds',
  'reconnect_after': 60
}))
"

# Wait for clients to disconnect
sleep 30

# Rollback WebSocket service
kubectl rollout undo deployment/boardroom-websocket -n boardroom

# Verify WebSocket connectivity
wscat -c wss://api.boardroom.com/ws -H "Authorization: Bearer $TEST_TOKEN"
```

## Configuration Rollback

### 1. Environment Variables

```bash
#!/bin/bash
# config_rollback.sh

# Backup current config
kubectl get configmap boardroom-config -n boardroom -o yaml > config_backup_$(date +%Y%m%d_%H%M%S).yaml

# Apply previous config
kubectl apply -f /backups/configs/boardroom-config-$PREVIOUS_VERSION.yaml

# Restart pods to pick up new config
kubectl rollout restart deployment/boardroom-backend -n boardroom
kubectl rollout restart deployment/boardroom-frontend -n boardroom

# Verify configuration
kubectl exec -it deployment/boardroom-backend -n boardroom -- env | grep BOARDROOM_
```

### 2. Secrets Rollback

```bash
#!/bin/bash
# secrets_rollback.sh

# List secret versions
aws secretsmanager list-secret-version-ids --secret-id boardroom/production

# Restore previous version
PREVIOUS_VERSION="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
aws secretsmanager update-secret-version-stage \
  --secret-id boardroom/production \
  --version-stage AWSCURRENT \
  --move-to-version-id $PREVIOUS_VERSION

# Update Kubernetes secrets
./scripts/sync_secrets.sh

# Restart applications
kubectl rollout restart deployment -n boardroom
```

## Emergency Procedures

### 1. Complete System Rollback

```bash
#!/bin/bash
# emergency_rollback.sh

echo "EMERGENCY ROLLBACK INITIATED"
echo "Reason: $1"

# Set maintenance mode
kubectl apply -f - << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: maintenance-mode
  namespace: boardroom
data:
  enabled: "true"
  message: "System maintenance in progress. Please try again later."
EOF

# Capture current state
./scripts/capture_state.sh

# Rollback all components
kubectl rollout undo deployment --all -n boardroom

# Restore last known good database backup
./scripts/restore_backup.sh /backups/last_known_good.sql.gz

# Clear all caches
redis-cli FLUSHALL

# Restart all services
kubectl delete pods --all -n boardroom

# Verify system health
./scripts/full_system_check.sh

# Disable maintenance mode
kubectl patch configmap maintenance-mode -n boardroom --type merge -p '{"data":{"enabled":"false"}}'
```

### 2. Data Recovery

```bash
#!/bin/bash
# data_recovery.sh

# Identify corrupted data
psql $DATABASE_URL << EOF
-- Find inconsistencies
SELECT * FROM data_integrity_check();

-- Identify affected records
CREATE TEMP TABLE affected_records AS
SELECT * FROM audit_logs 
WHERE created_at >= NOW() - INTERVAL '1 hour'
AND action IN ('create', 'update', 'delete');
EOF

# Restore from transaction logs
pg_waldump /var/lib/postgresql/data/pg_wal/$(ls -t /var/lib/postgresql/data/pg_wal/ | head -1) \
  | grep -E "(INSERT|UPDATE|DELETE)" \
  > /tmp/wal_transactions.sql

# Apply selective recovery
psql $DATABASE_URL < /tmp/wal_transactions.sql

# Verify data integrity
./scripts/data_integrity_check.sh
```

## Monitoring During Rollback

### 1. Real-Time Monitoring Script

```bash
#!/bin/bash
# monitor_rollback.sh

while true; do
  clear
  echo "=== Rollback Monitoring Dashboard ==="
  echo "Time: $(date)"
  echo ""
  
  # Application status
  echo "Application Status:"
  kubectl get pods -n boardroom | grep -E "(frontend|backend|websocket)"
  echo ""
  
  # Error rates
  echo "Error Rates:"
  curl -s http://prometheus:9090/api/v1/query?query=rate\(http_requests_total\{status=~\"5..\"\}\[1m\]\) | \
    jq -r '.data.result[] | "\(.metric.job): \(.value[1])"'
  echo ""
  
  # Response times
  echo "Response Times (p95):"
  curl -s http://prometheus:9090/api/v1/query?query=histogram_quantile\(0.95,http_request_duration_seconds_bucket\) | \
    jq -r '.data.result[] | "\(.metric.job): \(.value[1])s"'
  echo ""
  
  # Active connections
  echo "Active Connections:"
  curl -s http://prometheus:9090/api/v1/query?query=websocket_connections_active | \
    jq -r '.data.result[0].value[1]'
  
  sleep 5
done
```

### 2. Rollback Metrics Collection

```python
# collect_rollback_metrics.py
import time
import json
from datetime import datetime
import requests

class RollbackMetrics:
    def __init__(self):
        self.start_time = datetime.now()
        self.metrics = {
            'start_time': self.start_time.isoformat(),
            'duration': 0,
            'error_count': 0,
            'success_rate': 0,
            'affected_users': 0,
            'downtime_seconds': 0
        }
    
    def collect(self):
        """Collect metrics during rollback"""
        while True:
            # Update duration
            self.metrics['duration'] = (datetime.now() - self.start_time).seconds
            
            # Collect error metrics
            response = requests.get('http://prometheus:9090/api/v1/query', 
                params={'query': 'sum(increase(http_requests_total{status=~"5.."}[1m]))'})
            if response.ok:
                data = response.json()
                if data['data']['result']:
                    self.metrics['error_count'] = int(float(data['data']['result'][0]['value'][1]))
            
            # Calculate success rate
            total_response = requests.get('http://prometheus:9090/api/v1/query',
                params={'query': 'sum(increase(http_requests_total[1m]))'})
            if total_response.ok:
                data = total_response.json()
                if data['data']['result']:
                    total = float(data['data']['result'][0]['value'][1])
                    if total > 0:
                        self.metrics['success_rate'] = ((total - self.metrics['error_count']) / total) * 100
            
            # Save metrics
            with open(f'rollback_metrics_{self.start_time.strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
                json.dump(self.metrics, f, indent=2)
            
            time.sleep(10)

if __name__ == '__main__':
    collector = RollbackMetrics()
    collector.collect()
```

## Post-Rollback Procedures

### 1. Verification Checklist

```bash
#!/bin/bash
# post_rollback_verification.sh

echo "=== Post-Rollback Verification ==="

# Health checks
echo "1. Health Checks:"
curl -f https://api.boardroom.com/api/v1/health && echo "✓ API Health: OK" || echo "✗ API Health: FAILED"
curl -f https://boardroom.com/ && echo "✓ Frontend: OK" || echo "✗ Frontend: FAILED"

# Database checks
echo -e "\n2. Database Checks:"
psql $DATABASE_URL -c "SELECT version();" && echo "✓ Database: OK" || echo "✗ Database: FAILED"

# Redis checks
echo -e "\n3. Redis Checks:"
redis-cli ping && echo "✓ Redis: OK" || echo "✗ Redis: FAILED"

# Feature checks
echo -e "\n4. Feature Checks:"
./scripts/feature_tests.sh

# Performance checks
echo -e "\n5. Performance Checks:"
./scripts/performance_tests.sh

# Security checks
echo -e "\n6. Security Checks:"
./scripts/security_scan.sh
```

### 2. Communication Template

```markdown
# Rollback Communication Template

## Subject: [RESOLVED] Service Rollback Completed - Boardroom Platform

### Summary
We have successfully completed a rollback of the Boardroom platform to address [ISSUE DESCRIPTION]. The service has been restored to the previous stable version and is now fully operational.

### Timeline
- **Issue Detected**: [TIME]
- **Rollback Initiated**: [TIME]
- **Service Restored**: [TIME]
- **Total Downtime**: [DURATION]

### Impact
- **Affected Services**: [List affected services]
- **Affected Users**: [Number or percentage]
- **Data Impact**: [Any data implications]

### Root Cause
[Brief description of what caused the issue]

### Actions Taken
1. [Action 1]
2. [Action 2]
3. [Action 3]

### Next Steps
- [ ] Root cause analysis scheduled for [DATE/TIME]
- [ ] Fix implementation planned for [DATE]
- [ ] Additional monitoring implemented

### Contact
For questions or concerns, please contact:
- Engineering: engineering@boardroom.com
- Support: support@boardroom.com

We apologize for any inconvenience and appreciate your patience.
```

### 3. Lessons Learned Document

```markdown
# Rollback Post-Mortem

## Incident Details
- **Date**: [DATE]
- **Duration**: [DURATION]
- **Severity**: [LOW/MEDIUM/HIGH/CRITICAL]
- **Services Affected**: [LIST]

## Timeline
[Detailed timeline of events]

## Root Cause Analysis
### What Went Wrong
[Detailed explanation]

### Why It Went Wrong
[Analysis of contributing factors]

## Impact Assessment
- **User Impact**: [Details]
- **Business Impact**: [Details]
- **Technical Impact**: [Details]

## What Went Well
- [Positive aspect 1]
- [Positive aspect 2]

## What Could Be Improved
- [Improvement area 1]
- [Improvement area 2]

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|---------|
| [Action 1] | [Name] | [Date] | [Status] |
| [Action 2] | [Name] | [Date] | [Status] |

## Prevention Measures
[Steps to prevent similar incidents]

## Documentation Updates
- [ ] Update rollback procedures
- [ ] Update monitoring alerts
- [ ] Update deployment checklist
```

## Rollback Testing

### 1. Regular Rollback Drills

```bash
#!/bin/bash
# rollback_drill.sh

echo "=== Rollback Drill Started ==="
echo "This is a drill - no actual rollback will occur"

# Simulate rollback steps
echo "1. Checking current version..."
kubectl get deployments -n boardroom -o wide

echo "2. Simulating health check failure..."
# Actual health check without failure

echo "3. Identifying rollback target..."
kubectl rollout history deployment/boardroom-backend -n boardroom

echo "4. Simulating rollback command..."
echo "kubectl rollout undo deployment/boardroom-backend -n boardroom"

echo "5. Verifying rollback procedure..."
# Check that all scripts exist and are executable
for script in capture_state.sh monitor_rollback.sh post_rollback_verification.sh; do
  if [ -x "./scripts/$script" ]; then
    echo "✓ $script is ready"
  else
    echo "✗ $script is missing or not executable"
  fi
done

echo -e "\n=== Rollback Drill Completed ==="
```

### 2. Automated Rollback Testing

```python
# test_rollback_procedures.py
import unittest
import subprocess
import time

class TestRollbackProcedures(unittest.TestCase):
    def test_deployment_rollback(self):
        """Test Kubernetes deployment rollback"""
        # Deploy test version
        subprocess.run(['kubectl', 'set', 'image', 
                       'deployment/test-app', 'app=test:v2', 
                       '-n', 'test'])
        time.sleep(10)
        
        # Rollback
        result = subprocess.run(['kubectl', 'rollout', 'undo', 
                                'deployment/test-app', '-n', 'test'],
                               capture_output=True)
        
        self.assertEqual(result.returncode, 0)
    
    def test_database_rollback(self):
        """Test database migration rollback"""
        # This would test in a isolated test database
        pass
    
    def test_config_rollback(self):
        """Test configuration rollback"""
        # This would test config rollback procedures
        pass

if __name__ == '__main__':
    unittest.main()
```

---

**Important**: These procedures should be regularly reviewed, tested, and updated. All team members should be familiar with these procedures before they are needed in a real incident.