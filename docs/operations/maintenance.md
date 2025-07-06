# Maintenance Procedures

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: DevOps / Solo Developer  
**Next Review**: Based on operational experience  

## Overview

This document outlines maintenance procedures for keeping Boardroom AI running smoothly in production. It covers routine maintenance, updates, backups, and security practices.

## Routine Maintenance Schedule

### Daily Tasks

1. **Health Checks** (Automated)
   ```bash
   # Automated via cron
   0 * * * * curl -f http://localhost:8000/health || alert_admin
   ```

2. **Log Rotation**
   ```bash
   # Check log sizes
   du -sh logs/*.jsonl
   
   # Rotate if needed (automated via logrotate)
   ```

3. **Monitor Alerts**
   - Check Grafana dashboards
   - Review error rates
   - Monitor response times

### Weekly Tasks

1. **Backup Verification**
   ```bash
   # Test latest backup
   pg_restore --list backup_latest.sql | head -20
   ```

2. **Security Updates**
   ```bash
   # Check for updates
   docker scan boardroom-repo-app:latest
   
   # Update base images if needed
   docker pull python:3.13.2-slim
   ```

3. **Performance Review**
   - Check slow query logs
   - Review cache hit rates
   - Monitor memory usage trends

### Monthly Tasks

1. **Full System Backup**
2. **Dependency Updates**
3. **Security Audit**
4. **Capacity Planning**

## Update Procedures

### 1. Application Updates

**Preparation:**
```bash
# 1. Backup current state
./scripts/backup.sh

# 2. Test in staging
git checkout develop
docker-compose -f docker-compose.staging.yml up

# 3. Run tests
pytest
cd frontend && npm test
```

**Deployment:**
```bash
# 1. Pull latest changes
git pull origin main

# 2. Build new images
docker-compose build

# 3. Deploy with zero downtime
docker-compose up -d --no-deps --scale app=2 app
docker-compose up -d --no-deps app

# 4. Verify deployment
curl http://localhost:8000/health
```

**Rollback if needed:**
```bash
# Quick rollback
git checkout <previous-version>
docker-compose build
docker-compose up -d
```

### 2. Database Updates

**Schema Migrations:**
```bash
# 1. Backup database
pg_dump -h localhost -U postgres boardroom_prod > backup_pre_migration.sql

# 2. Test migration
alembic upgrade head --sql

# 3. Apply migration
docker-compose exec app alembic upgrade head

# 4. Verify
docker-compose exec app alembic current
```

**Data Migrations:**
```python
# scripts/migrate_data.py
import asyncio
from app.services.database import database_service

async def migrate_data():
    """Perform data migration."""
    await database_service.initialize()
    
    # Migration logic here
    # Always test in staging first!
    
asyncio.run(migrate_data())
```

### 3. Dependency Updates

**Python Dependencies:**
```bash
# 1. Update dependencies
cd backend
pip list --outdated

# 2. Test updates
pip install --upgrade package_name
pytest

# 3. Update requirements
pip freeze > requirements.txt

# 4. Rebuild Docker image
docker-compose build app
```

**Frontend Dependencies:**
```bash
# 1. Check outdated
cd frontend
npm outdated

# 2. Update safely
npm update  # Minor updates
npm install package@latest  # Major updates

# 3. Test
npm test
npm run build

# 4. Update lock file
npm install
```

## Backup Procedures

### 1. Automated Backups

**Database Backup Script** (`scripts/backup_db.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/boardroom_$TIMESTAMP.sql"

# Create backup
pg_dump -h localhost -U postgres boardroom_prod > $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

# Upload to S3 (optional)
aws s3 cp $BACKUP_FILE.gz s3://boardroom-backups/

# Keep only last 7 days locally
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
```

**Cron Schedule:**
```bash
# Daily at 2 AM
0 2 * * * /home/app/scripts/backup_db.sh
```

### 2. Application Backup

```bash
#!/bin/bash
# Backup application data
tar -czf boardroom_app_$(date +%Y%m%d).tar.gz \
  .env.production \
  docker-compose.yml \
  logs/ \
  uploads/
```

### 3. Restore Procedures

**Database Restore:**
```bash
# 1. Stop application
docker-compose stop app

# 2. Restore database
gunzip < backup_20250107.sql.gz | psql -h localhost -U postgres boardroom_prod

# 3. Restart application
docker-compose start app

# 4. Verify
curl http://localhost:8000/health
```

## Security Maintenance

### 1. Certificate Renewal

**Let's Encrypt (Automated):**
```bash
# Check certificate expiry
certbot certificates

# Manual renewal if needed
certbot renew --nginx

# Verify renewal
echo | openssl s_client -servername boardroom.ai -connect boardroom.ai:443 2>/dev/null | openssl x509 -noout -dates
```

### 2. Security Scanning

**Weekly Security Scan:**
```bash
# 1. Scan Docker images
docker scan boardroom-repo-app:latest

# 2. Check Python dependencies
safety check

# 3. Scan for secrets
trufflehog git file://./

# 4. Check SSL configuration
nmap --script ssl-cert -p 443 boardroom.ai
```

### 3. Access Review

**Monthly Access Audit:**
```sql
-- Check user activity
SELECT 
    email,
    last_login,
    CASE 
        WHEN last_login < NOW() - INTERVAL '30 days' THEN 'Inactive'
        ELSE 'Active'
    END as status
FROM users
ORDER BY last_login DESC;

-- Review admin users
SELECT * FROM users WHERE is_admin = true;
```

## Performance Optimization

### 1. Database Maintenance

**Weekly Tasks:**
```sql
-- Update statistics
ANALYZE;

-- Reindex if needed
REINDEX INDEX CONCURRENTLY idx_users_email;

-- Check for bloat
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

### 2. Cache Maintenance

**Redis Maintenance:**
```bash
# Check memory usage
redis-cli INFO memory

# Clear old cache entries
redis-cli --scan --pattern "cache:*" | \
  xargs -L 1 -I {} redis-cli TTL {} | \
  grep -E "^-1$" | wc -l

# Optimize memory
redis-cli MEMORY DOCTOR
```

### 3. Log Management

**Log Cleanup:**
```bash
# Compress old logs
find logs/ -name "*.jsonl" -mtime +7 -exec gzip {} \;

# Archive to S3
aws s3 sync logs/ s3://boardroom-logs/ --exclude "*" --include "*.gz"

# Remove old compressed logs
find logs/ -name "*.gz" -mtime +30 -delete
```

## Monitoring and Alerting

### 1. Prometheus Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: boardroom_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        annotations:
          summary: "Database is down"
```

### 2. Health Check Script

```python
#!/usr/bin/env python3
# scripts/health_check.py
import requests
import sys

def check_health():
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        data = response.json()
        
        if data["status"] != "healthy":
            print(f"Unhealthy status: {data}")
            sys.exit(1)
            
        print("All systems operational")
        
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_health()
```

## Disaster Recovery

### 1. Emergency Procedures

**System Down:**
1. Check Docker containers: `docker-compose ps`
2. Check logs: `docker-compose logs --tail=100`
3. Restart services: `docker-compose restart`
4. If persistent, restore from backup

**Data Corruption:**
1. Stop application immediately
2. Assess damage using backups
3. Restore from last known good backup
4. Run integrity checks
5. Document incident

### 2. Recovery Time Objectives

- **RTO** (Recovery Time): 4 hours
- **RPO** (Recovery Point): 24 hours
- **Backup retention**: 30 days
- **Archive retention**: 1 year

## Maintenance Mode

### Enable Maintenance Mode

```nginx
# /etc/nginx/sites-available/boardroom
location / {
    if (-f /var/www/maintenance.flag) {
        return 503;
    }
    proxy_pass http://localhost:8000;
}

error_page 503 @maintenance;
location @maintenance {
    root /var/www;
    rewrite ^.*$ /maintenance.html break;
}
```

```bash
# Enable maintenance
touch /var/www/maintenance.flag

# Disable maintenance
rm /var/www/maintenance.flag
```

## Documentation Updates

### After Each Maintenance

1. Update this document with lessons learned
2. Document any new procedures discovered
3. Update runbooks with specific scenarios
4. Share knowledge in team notes

## Maintenance Checklist

### Pre-Maintenance
- [ ] Announce maintenance window
- [ ] Backup all data
- [ ] Test in staging
- [ ] Prepare rollback plan

### During Maintenance
- [ ] Enable maintenance mode
- [ ] Monitor progress
- [ ] Test each change
- [ ] Document actions

### Post-Maintenance
- [ ] Verify all services
- [ ] Check monitoring
- [ ] Update documentation
- [ ] Send completion notice

## Related Documentation

- [Deployment Guide](../deployment/deployment_guide.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Infrastructure Notes](../deployment/infrastructure.md)
- [Security Practices](./security.md)

---

**Emergency Contact**: Keep emergency contacts and escalation procedures readily available.