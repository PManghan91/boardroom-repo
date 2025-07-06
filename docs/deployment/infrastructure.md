# Infrastructure Notes

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: DevOps / Infrastructure Team  
**Next Review**: With infrastructure changes  

## Overview

This document outlines the infrastructure requirements and configuration for running Boardroom AI in production. It covers server specifications, network configuration, and essential services setup.

## Minimum Server Requirements

### Development Environment
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **OS**: Ubuntu 22.04 LTS or similar

### Production Environment
- **CPU**: 4+ cores (8 recommended)
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 100GB SSD (expandable)
- **OS**: Ubuntu 22.04 LTS
- **Network**: 100Mbps minimum

### Resource Allocation

```yaml
# docker-compose.yml resource limits
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
          
  postgres:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
          
  redis:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## Network Configuration

### Port Requirements

| Service | Port | Protocol | Access |
|---------|------|----------|--------|
| HTTP | 80 | TCP | Public |
| HTTPS | 443 | TCP | Public |
| FastAPI | 8000 | TCP | Internal |
| Next.js | 3000 | TCP | Internal |
| PostgreSQL | 5432 | TCP | Internal |
| Redis | 6379 | TCP | Internal |
| Prometheus | 9090 | TCP | Internal |
| Grafana | 3001 | TCP | Internal |

### Firewall Rules

```bash
# UFW configuration
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port as needed)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

### Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/boardroom
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name boardroom.ai www.boardroom.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name boardroom.ai;

    ssl_certificate /etc/letsencrypt/live/boardroom.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/boardroom.ai/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # API routes
    location /api {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Frontend routes
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Service Configuration

### PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Configure PostgreSQL
sudo -u postgres psql

CREATE USER boardroom WITH PASSWORD 'secure_password';
CREATE DATABASE boardroom_prod OWNER boardroom;
GRANT ALL PRIVILEGES ON DATABASE boardroom_prod TO boardroom;

# Enable remote connections (if needed)
# Edit /etc/postgresql/14/main/postgresql.conf
listen_addresses = 'localhost'  # or '*' for all interfaces

# Edit /etc/postgresql/14/main/pg_hba.conf
# Add: host all all 0.0.0.0/0 md5
```

### Redis Configuration

```bash
# Install Redis
sudo apt install redis-server

# Configure Redis (/etc/redis/redis.conf)
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
appendfsync everysec

# Set password
requirepass your_redis_password

# Enable service
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Docker Setup

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Configure Docker daemon (/etc/docker/daemon.json)
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'boardroom-api'
    static_configs:
      - targets: ['app:8000']
    metrics_path: /metrics

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres_exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis_exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node_exporter:9100']
```

### Grafana Dashboards

Import these dashboard IDs:
- **Node Exporter**: 1860
- **PostgreSQL**: 9628
- **Redis**: 763
- **Docker**: 893

Custom dashboard for Boardroom AI metrics available in `grafana/dashboards/`

## Scaling Configuration

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
services:
  app:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/load-balancer.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
```

### Load Balancer Configuration

```nginx
# nginx/load-balancer.conf
upstream app_servers {
    least_conn;
    server app_1:8000 weight=1;
    server app_2:8000 weight=1;
    server app_3:8000 weight=1;
}
```

### Database Read Replicas

```python
# Future: Read replica configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'primary.db.host',
        'PORT': 5432,
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'replica.db.host',
        'PORT': 5432,
    }
}
```

## Security Hardening

### OS-Level Security

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install security updates automatically
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Fail2ban for SSH protection
sudo apt install fail2ban
sudo systemctl enable fail2ban

# Configure sysctl for security
cat >> /etc/sysctl.conf << EOF
# IP Spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0

# Log Martians
net.ipv4.conf.all.log_martians = 1

# Ignore ICMP ping requests
net.ipv4.icmp_echo_ignore_broadcasts = 1
EOF

sudo sysctl -p
```

### SSL/TLS Configuration

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d boardroom.ai -d www.boardroom.ai

# Auto-renewal
sudo certbot renew --dry-run

# Add to crontab
0 2 * * * /usr/bin/certbot renew --quiet
```

## Backup Infrastructure

### Automated Backup System

```bash
# Backup script location
/opt/boardroom/scripts/backup.sh

# Cron configuration
0 2 * * * /opt/boardroom/scripts/backup.sh

# S3 backup configuration
aws configure set default.s3.max_concurrent_requests 10
aws configure set default.s3.max_queue_size 1000
aws configure set default.s3.multipart_threshold 64MB
```

### Backup Storage

```bash
# Local backup directory structure
/backups/
├── postgres/
│   └── daily/
│   └── weekly/
│   └── monthly/
├── redis/
├── application/
└── logs/
```

## Disaster Recovery

### Multi-Region Setup (Future)

```yaml
# Infrastructure as Code (Terraform example)
resource "aws_instance" "boardroom_primary" {
  ami           = "ami-12345678"
  instance_type = "t3.large"
  region        = "us-east-1"
}

resource "aws_instance" "boardroom_secondary" {
  ami           = "ami-12345678"
  instance_type = "t3.large"
  region        = "us-west-2"
}
```

### Database Replication

```sql
-- Primary database
CREATE PUBLICATION boardroom_pub FOR ALL TABLES;

-- Replica database
CREATE SUBSCRIPTION boardroom_sub
CONNECTION 'host=primary.db port=5432 dbname=boardroom'
PUBLICATION boardroom_pub;
```

## Performance Tuning

### System Parameters

```bash
# /etc/security/limits.conf
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768

# Kernel parameters
echo 'vm.swappiness=10' >> /etc/sysctl.conf
echo 'vm.vfs_cache_pressure=50' >> /etc/sysctl.conf
```

### PostgreSQL Tuning

```conf
# postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

## Cost Optimization

### Resource Monitoring

```bash
# Monitor resource usage
docker stats --no-stream

# Optimize container sizes
docker image prune -a
docker container prune
docker volume prune
```

### Auto-scaling Rules

```yaml
# Future: Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: boardroom-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: boardroom-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Maintenance Access

### SSH Configuration

```bash
# /etc/ssh/sshd_config
Port 22  # Consider changing
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers boardroom-admin
```

### VPN Setup (Optional)

For additional security, consider setting up WireGuard VPN for administrative access.

## Related Documentation

- [Deployment Guide](./deployment_guide.md)
- [Security Best Practices](../operations/security.md)
- [Monitoring Setup](../operations/monitoring.md)
- [Maintenance Procedures](../operations/maintenance.md)

---

**Infrastructure Support**: Document all infrastructure changes and maintain infrastructure as code where possible.