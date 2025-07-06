# Basic Troubleshooting Guide

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: Solo Developer / Support  
**Next Review**: Based on issues encountered  

## Overview

This guide provides solutions to common issues encountered when running Boardroom AI. Issues are organized by category with step-by-step resolution procedures.

## Quick Diagnostics

### System Health Check
```bash
# Check if services are running
docker-compose ps

# Check API health
curl http://localhost:8000/health

# Check frontend
curl -I http://localhost:3000

# View recent logs
docker-compose logs --tail=50
```

## Common Issues and Fixes

### 1. Backend/API Issues

#### Issue: "No module named 'asyncpg'" Error
**Symptoms**: Backend crashes with import error, health check returns 500

**Solution**:
```bash
# Rebuild Docker image
docker-compose build app

# Or if running locally, install missing dependency
pip install asyncpg
```

#### Issue: Database Connection Failed
**Symptoms**: 
- Error: "could not connect to server"
- Health check shows database unhealthy

**Solutions**:
1. Check database is running:
   ```bash
   docker-compose ps postgres
   # or
   pg_isready -h localhost -p 5432
   ```

2. Verify connection string:
   ```bash
   # Check environment variable
   echo $POSTGRES_URL
   
   # Format should be:
   # postgresql://user:password@host:port/database
   ```

3. Test connection:
   ```bash
   psql $POSTGRES_URL -c "SELECT 1"
   ```

#### Issue: JWT Authentication Errors
**Symptoms**: 401 Unauthorized on all API calls

**Solutions**:
1. Check token format in request:
   ```bash
   # Correct format
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
   ```

2. Verify JWT secret is set:
   ```bash
   # In .env file
   JWT_SECRET_KEY="your-secret-key"
   ```

3. Check token expiration (24 hours by default)

#### Issue: Rate Limiting (429 Errors)
**Symptoms**: "Rate limit exceeded" errors

**Solutions**:
1. Check rate limit headers:
   ```
   X-RateLimit-Limit: 30
   X-RateLimit-Remaining: 0
   X-RateLimit-Reset: 1704628800
   ```

2. Wait for reset or implement backoff:
   ```python
   import time
   retry_after = int(response.headers.get('X-RateLimit-Reset', 0))
   wait_time = retry_after - time.time()
   time.sleep(max(0, wait_time))
   ```

### 2. Frontend Issues

#### Issue: Frontend Can't Connect to Backend
**Symptoms**: API calls fail, CORS errors in browser console

**Solutions**:
1. Check backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verify frontend environment:
   ```bash
   # frontend/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. Check CORS configuration in backend

#### Issue: Port 3000 Already in Use
**Symptoms**: "Port 3000 is in use" error

**Solutions**:
1. Find process using port:
   ```bash
   lsof -i :3000
   # or
   netstat -tulpn | grep 3000
   ```

2. Kill process or use different port:
   ```bash
   # Kill process
   kill -9 <PID>
   
   # Or use different port
   PORT=3001 npm run dev
   ```

### 3. Docker Issues

#### Issue: Container Keeps Restarting
**Symptoms**: Container status shows "Restarting"

**Solutions**:
1. Check logs:
   ```bash
   docker-compose logs app --tail=100
   ```

2. Common causes:
   - Missing environment variables
   - Database not ready
   - Port conflicts

3. Debug interactively:
   ```bash
   docker-compose run app bash
   ```

#### Issue: "No space left on device"
**Symptoms**: Build or runtime errors about disk space

**Solutions**:
1. Clean Docker resources:
   ```bash
   # Remove unused containers
   docker system prune -a
   
   # Remove unused volumes
   docker volume prune
   
   # Check disk usage
   df -h
   ```

### 4. Database Issues

#### Issue: Migration Failures
**Symptoms**: "alembic" errors, schema mismatch

**Solutions**:
1. Check current migration status:
   ```bash
   docker-compose exec app alembic current
   ```

2. Apply migrations:
   ```bash
   docker-compose exec app alembic upgrade head
   ```

3. Rollback if needed:
   ```bash
   docker-compose exec app alembic downgrade -1
   ```

#### Issue: "TypeError: Object of type datetime is not JSON serializable"
**Symptoms**: API returns 500 error on health check

**Solutions**:
1. This is a known issue with datetime serialization
2. Temporary workaround: Restart the container
3. Long-term: Update JSON encoder in response handling

### 5. Performance Issues

#### Issue: Slow API Response Times
**Symptoms**: API calls take >2 seconds

**Diagnostic Steps**:
1. Check resource usage:
   ```bash
   docker stats
   ```

2. Monitor Redis cache:
   ```bash
   docker-compose exec redis redis-cli
   > INFO stats
   > INFO memory
   ```

3. Check database query performance:
   ```bash
   # Enable slow query logging in PostgreSQL
   ```

**Solutions**:
- Increase container resources
- Enable Redis caching
- Optimize database queries
- Check for N+1 query problems

#### Issue: High Memory Usage
**Symptoms**: Container using >2GB RAM

**Solutions**:
1. Set memory limits:
   ```yaml
   # docker-compose.yml
   services:
     app:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

2. Monitor for memory leaks:
   ```bash
   docker-compose exec app python -m tracemalloc
   ```

### 6. LLM/AI Issues

#### Issue: OpenAI API Key Invalid
**Symptoms**: "Invalid API key" errors in chat

**Solutions**:
1. Verify API key:
   ```bash
   # Test API key
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $LLM_API_KEY"
   ```

2. Check environment variable:
   ```bash
   echo $LLM_API_KEY
   ```

3. Ensure key has credits/valid subscription

#### Issue: Langfuse Connection Failed
**Symptoms**: Warning logs about Langfuse, but app continues

**Solutions**:
1. Langfuse is optional - warnings can be ignored
2. To disable, remove from .env:
   ```bash
   # Comment out or remove
   # LANGFUSE_PUBLIC_KEY=...
   # LANGFUSE_SECRET_KEY=...
   ```

## Log Analysis

### Understanding Log Structure

Logs are in JSON format with structured fields:
```json
{
  "timestamp": "2025-01-07T10:30:00Z",
  "level": "error",
  "message": "database_connection_failed",
  "environment": "development",
  "error": "connection refused",
  "module": "database"
}
```

### Viewing Logs

```bash
# Real-time logs
docker-compose logs -f app

# Search for errors
docker-compose logs app | grep -i error

# Parse JSON logs
cat logs/development-2025-01-07.jsonl | jq '.level == "error"'
```

### Common Log Patterns

1. **Startup Issues**:
   - Look for "application_startup_failed"
   - Check for missing dependencies

2. **Runtime Errors**:
   - Search for "error" level logs
   - Check stack traces

3. **Performance Issues**:
   - Look for "slow_request" logs
   - Check "response_time_ms" values

## Emergency Procedures

### Complete System Reset

```bash
# Stop everything
docker-compose down -v

# Clean up
docker system prune -a

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up -d
```

### Data Recovery

```bash
# Backup current state
docker-compose exec postgres pg_dump -U postgres boardroom > emergency_backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U postgres boardroom < backup.sql
```

## Getting Help

### Information to Collect

When reporting issues, include:
1. Error messages (full stack trace)
2. Recent logs: `docker-compose logs --tail=100`
3. Environment: `echo $APP_ENV`
4. System info: `docker version && docker-compose version`

### Debug Mode

Enable debug mode for more information:
```bash
# In .env file
DEBUG=true

# Restart services
docker-compose restart
```

## Monitoring and Prevention

### Health Monitoring

Set up regular health checks:
```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:8000/health || alert_admin
```

### Log Monitoring

Monitor for warning signs:
```bash
# Check error rate
grep '"level":"error"' logs/development-*.jsonl | wc -l

# Monitor memory usage
docker stats --no-stream
```

## Next Steps

1. Set up proper monitoring with Prometheus/Grafana
2. Configure alerting for critical issues
3. Document new issues as encountered
4. Review [Maintenance Procedures](./maintenance.md)

---

**Still Having Issues?** 
- Check the [Development Setup Guide](../development/setup.md)
- Review [Deployment Guide](../deployment/deployment_guide.md)
- Search logs for specific error messages