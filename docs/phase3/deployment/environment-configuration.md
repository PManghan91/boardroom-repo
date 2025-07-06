# Environment Configuration Guide

## Overview

This guide provides detailed information on configuring the Boardroom application for different environments (development, staging, production). It covers environment variables, configuration files, secrets management, and best practices for maintaining secure and scalable configurations.

## Environment Structure

```
environments/
├── development/
│   ├── .env.development
│   ├── docker-compose.dev.yml
│   └── config/
├── staging/
│   ├── .env.staging
│   ├── docker-compose.staging.yml
│   └── config/
└── production/
    ├── .env.production
    ├── docker-compose.prod.yml
    └── config/
```

## Environment Variables

### Frontend Environment Variables

#### Development (.env.development)

```bash
# Application
NODE_ENV=development
NEXT_PUBLIC_APP_NAME=Boardroom Dev
NEXT_PUBLIC_APP_VERSION=3.0.0-dev

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_VERSION=/api/v1
NEXT_PUBLIC_API_TIMEOUT=30000

# WebSocket Configuration
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_WS_RECONNECT_INTERVAL=1000
NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS=5

# Feature Flags
NEXT_PUBLIC_ENABLE_MFA=false
NEXT_PUBLIC_ENABLE_OFFLINE=true
NEXT_PUBLIC_ENABLE_DEBUG_MODE=true
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_SENTRY=false

# Development Tools
NEXT_PUBLIC_SHOW_DEBUG_INFO=true
NEXT_PUBLIC_MOCK_API=false
NEXT_PUBLIC_API_DELAY=0

# Authentication
NEXT_PUBLIC_SESSION_TIMEOUT=3600000
NEXT_PUBLIC_REFRESH_TOKEN_INTERVAL=300000

# Cache Configuration
NEXT_PUBLIC_CACHE_TTL=300000
NEXT_PUBLIC_CACHE_STRATEGY=network-first
```

#### Staging (.env.staging)

```bash
# Application
NODE_ENV=staging
NEXT_PUBLIC_APP_NAME=Boardroom Staging
NEXT_PUBLIC_APP_VERSION=3.0.0-rc1

# API Configuration
NEXT_PUBLIC_API_URL=https://staging-api.boardroom.com
NEXT_PUBLIC_API_VERSION=/api/v1
NEXT_PUBLIC_API_TIMEOUT=20000

# WebSocket Configuration
NEXT_PUBLIC_WS_URL=wss://staging-api.boardroom.com/ws
NEXT_PUBLIC_WS_RECONNECT_INTERVAL=2000
NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS=10

# Feature Flags
NEXT_PUBLIC_ENABLE_MFA=true
NEXT_PUBLIC_ENABLE_OFFLINE=true
NEXT_PUBLIC_ENABLE_DEBUG_MODE=false
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_SENTRY=true

# External Services
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/staging
NEXT_PUBLIC_GA_TRACKING_ID=G-STAGING123

# Authentication
NEXT_PUBLIC_SESSION_TIMEOUT=1800000
NEXT_PUBLIC_REFRESH_TOKEN_INTERVAL=600000

# Security
NEXT_PUBLIC_ALLOWED_ORIGINS=https://staging.boardroom.com
NEXT_PUBLIC_CSP_REPORT_URI=https://staging-api.boardroom.com/api/v1/security/csp-report

# Cache Configuration
NEXT_PUBLIC_CACHE_TTL=600000
NEXT_PUBLIC_CACHE_STRATEGY=stale-while-revalidate
```

#### Production (.env.production)

```bash
# Application
NODE_ENV=production
NEXT_PUBLIC_APP_NAME=Boardroom
NEXT_PUBLIC_APP_VERSION=3.0.0

# API Configuration
NEXT_PUBLIC_API_URL=https://api.boardroom.com
NEXT_PUBLIC_API_VERSION=/api/v1
NEXT_PUBLIC_API_TIMEOUT=15000

# WebSocket Configuration
NEXT_PUBLIC_WS_URL=wss://api.boardroom.com/ws
NEXT_PUBLIC_WS_RECONNECT_INTERVAL=5000
NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS=20
NEXT_PUBLIC_WS_HEARTBEAT_INTERVAL=30000

# Feature Flags
NEXT_PUBLIC_ENABLE_MFA=true
NEXT_PUBLIC_ENABLE_OFFLINE=true
NEXT_PUBLIC_ENABLE_DEBUG_MODE=false
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_SENTRY=true
NEXT_PUBLIC_ENABLE_PWA=true

# External Services
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/production
NEXT_PUBLIC_GA_TRACKING_ID=G-PRODUCTION123
NEXT_PUBLIC_GTM_ID=GTM-XXXXX
NEXT_PUBLIC_HOTJAR_ID=1234567

# Authentication
NEXT_PUBLIC_SESSION_TIMEOUT=3600000
NEXT_PUBLIC_REFRESH_TOKEN_INTERVAL=900000
NEXT_PUBLIC_MFA_REQUIRED=true

# Security
NEXT_PUBLIC_ALLOWED_ORIGINS=https://boardroom.com,https://www.boardroom.com
NEXT_PUBLIC_CSP_REPORT_URI=https://api.boardroom.com/api/v1/security/csp-report
NEXT_PUBLIC_HSTS_MAX_AGE=31536000

# Performance
NEXT_PUBLIC_IMAGE_OPTIMIZATION=true
NEXT_PUBLIC_LAZY_LOAD_THRESHOLD=0.1
NEXT_PUBLIC_PREFETCH_LINKS=true

# Cache Configuration
NEXT_PUBLIC_CACHE_TTL=3600000
NEXT_PUBLIC_CACHE_STRATEGY=cache-first
NEXT_PUBLIC_CACHE_MAX_SIZE=52428800
```

### Backend Environment Variables

#### Development (.env.development)

```bash
# Application
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=DEBUG
RELOAD=True

# Database
DATABASE_URL=postgresql://boardroom_dev:devpass@localhost:5432/boardroom_dev
DB_ECHO=True
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=5
REDIS_DECODE_RESPONSES=True

# Security
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DELTA=3600
REFRESH_TOKEN_EXPIRATION_DELTA=604800
CORS_ORIGINS=["http://localhost:3000"]

# Email (Development)
EMAIL_BACKEND=console
DEFAULT_FROM_EMAIL=dev@boardroom.local

# File Storage (Local)
STORAGE_TYPE=local
MEDIA_ROOT=/app/media
MEDIA_URL=/media/

# Development Features
SHOW_DOCS=True
PROFILING_ENABLED=True
SQL_QUERY_LOGGING=True

# Rate Limiting (Disabled for dev)
RATE_LIMIT_ENABLED=False

# WebSocket
WS_HEARTBEAT_INTERVAL=30
WS_MESSAGE_QUEUE_SIZE=100
```

#### Staging (.env.staging)

```bash
# Application
ENVIRONMENT=staging
DEBUG=False
LOG_LEVEL=INFO
RELOAD=False

# Database
DATABASE_URL=postgresql://boardroom_stage:${DB_PASSWORD}@db-staging.boardroom.internal:5432/boardroom_staging
DB_ECHO=False
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_SSL_REQUIRE=True

# Redis
REDIS_URL=redis://:${REDIS_PASSWORD}@redis-staging.boardroom.internal:6379/0
REDIS_POOL_SIZE=10
REDIS_DECODE_RESPONSES=True
REDIS_SSL=True

# Security
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=RS256
JWT_EXPIRATION_DELTA=1800
REFRESH_TOKEN_EXPIRATION_DELTA=604800
CORS_ORIGINS=["https://staging.boardroom.com"]
ALLOWED_HOSTS=["staging-api.boardroom.com"]

# Email (SendGrid)
EMAIL_BACKEND=sendgrid
SENDGRID_API_KEY=${SENDGRID_API_KEY}
DEFAULT_FROM_EMAIL=noreply@staging.boardroom.com

# File Storage (S3)
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
S3_BUCKET_NAME=boardroom-staging
S3_REGION=us-west-2
S3_CUSTOM_DOMAIN=staging-cdn.boardroom.com

# Monitoring
SENTRY_DSN=${SENTRY_DSN}
SENTRY_ENVIRONMENT=staging
PROMETHEUS_ENABLED=True

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_DEFAULT=1000/hour
RATE_LIMIT_AUTH=10/minute

# WebSocket
WS_HEARTBEAT_INTERVAL=30
WS_MESSAGE_QUEUE_SIZE=1000
WS_SCALING_ENABLED=True

# Feature Flags
ENABLE_EXPERIMENTAL_FEATURES=True
ENABLE_BETA_FEATURES=True
```

#### Production (.env.production)

```bash
# Application
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING
RELOAD=False
WORKERS=4

# Database
DATABASE_URL=postgresql://boardroom_prod:${DB_PASSWORD}@db-primary.boardroom.internal:5432/boardroom_production
DATABASE_REPLICA_URLS=["postgresql://boardroom_prod:${DB_PASSWORD}@db-replica-1.boardroom.internal:5432/boardroom_production","postgresql://boardroom_prod:${DB_PASSWORD}@db-replica-2.boardroom.internal:5432/boardroom_production"]
DB_ECHO=False
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_SSL_REQUIRE=True
DB_STATEMENT_TIMEOUT=30000

# Redis Cluster
REDIS_URL=redis-cluster://:{REDIS_PASSWORD}@redis-cluster.boardroom.internal:6379/0
REDIS_POOL_SIZE=20
REDIS_DECODE_RESPONSES=True
REDIS_SSL=True
REDIS_RETRY_ON_TIMEOUT=True

# Security
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_PUBLIC_KEY=${JWT_PUBLIC_KEY}
JWT_ALGORITHM=RS256
JWT_EXPIRATION_DELTA=3600
REFRESH_TOKEN_EXPIRATION_DELTA=2592000
CORS_ORIGINS=["https://boardroom.com","https://www.boardroom.com"]
ALLOWED_HOSTS=["api.boardroom.com","boardroom.com"]
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email (Amazon SES)
EMAIL_BACKEND=ses
AWS_SES_REGION=us-west-2
AWS_SES_ACCESS_KEY_ID=${AWS_SES_ACCESS_KEY_ID}
AWS_SES_SECRET_ACCESS_KEY=${AWS_SES_SECRET_ACCESS_KEY}
DEFAULT_FROM_EMAIL=noreply@boardroom.com
EMAIL_RATE_LIMIT=14/second

# File Storage (S3 with CloudFront)
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
S3_BUCKET_NAME=boardroom-production
S3_REGION=us-west-2
S3_CUSTOM_DOMAIN=cdn.boardroom.com
S3_OBJECT_PARAMETERS={"CacheControl": "max-age=86400"}
CLOUDFRONT_DISTRIBUTION_ID=${CLOUDFRONT_DISTRIBUTION_ID}

# Monitoring
SENTRY_DSN=${SENTRY_DSN}
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
PROMETHEUS_ENABLED=True
STATSD_HOST=statsd.boardroom.internal
STATSD_PORT=8125

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_AUTH=5/15minutes
RATE_LIMIT_API_KEY=10000/hour

# WebSocket
WS_HEARTBEAT_INTERVAL=60
WS_MESSAGE_QUEUE_SIZE=10000
WS_SCALING_ENABLED=True
WS_REDIS_CHANNEL=boardroom:ws

# Performance
CACHE_TTL_DEFAULT=3600
CACHE_TTL_SESSION=1800
CACHE_TTL_STATIC=86400
QUERY_CACHE_SIZE=1000

# Backup
BACKUP_ENABLED=True
BACKUP_S3_BUCKET=boardroom-backups
BACKUP_RETENTION_DAYS=30

# Feature Flags
ENABLE_MAINTENANCE_MODE=False
ENABLE_READ_ONLY_MODE=False
ENABLE_FEATURE_FLAGS=True
LAUNCHDARKLY_SDK_KEY=${LAUNCHDARKLY_SDK_KEY}
```

## Configuration Files

### Docker Compose Configuration

#### Development (docker-compose.dev.yml)

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      - NODE_ENV=development
    env_file:
      - ./environments/development/.env.development
    ports:
      - "3000:3000"
    command: npm run dev

  backend:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
      - /app/.venv
    environment:
      - PYTHONUNBUFFERED=1
    env_file:
      - ./environments/development/.env.development
    ports:
      - "8000:8000"
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: boardroom_dev
      POSTGRES_USER: boardroom_dev
      POSTGRES_PASSWORD: devpass
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"
      - "8025:8025"

volumes:
  postgres_dev_data:
```

### Nginx Configuration

#### Production (nginx.conf)

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               application/rss+xml application/atom+xml image/svg+xml;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;

    # Upstreams
    upstream frontend {
        least_conn;
        server frontend:3000 max_fails=3 fail_timeout=30s;
    }

    upstream backend {
        least_conn;
        server backend-1:8000 weight=1 max_fails=3 fail_timeout=30s;
        server backend-2:8000 weight=1 max_fails=3 fail_timeout=30s;
        server backend-3:8000 weight=1 max_fails=3 fail_timeout=30s;
    }

    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name boardroom.com www.boardroom.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/boardroom.crt;
        ssl_certificate_key /etc/nginx/ssl/boardroom.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        ssl_stapling on;
        ssl_stapling_verify on;

        # HSTS
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Rate limiting
            limit_req zone=general burst=20 nodelay;
        }

        # API
        location /api {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
            
            # Rate limiting
            limit_req zone=general burst=50 nodelay;
        }

        # WebSocket
        location /ws {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket timeout
            proxy_read_timeout 3600s;
            proxy_send_timeout 3600s;
        }

        # Static files
        location /static {
            alias /usr/share/nginx/html/static;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Health check
        location /health {
            access_log off;
            return 200 "healthy\n";
        }
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name boardroom.com www.boardroom.com;
        return 301 https://$server_name$request_uri;
    }
}
```

## Secrets Management

### Using Environment Variables

```bash
# .env.secrets (never commit this file)
DB_PASSWORD=super-secret-password
REDIS_PASSWORD=another-secret-password
JWT_SECRET_KEY=jwt-secret-key-here
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENTRY_DSN=https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx@sentry.io/xxxxxxx
```

### Using AWS Secrets Manager

```python
# config/secrets.py
import boto3
import json
from functools import lru_cache

class SecretsManager:
    def __init__(self, region_name='us-west-2'):
        self.client = boto3.client('secretsmanager', region_name=region_name)
        self._cache = {}
    
    @lru_cache(maxsize=32)
    def get_secret(self, secret_name):
        """Get secret from AWS Secrets Manager with caching"""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except Exception as e:
            raise Exception(f"Error retrieving secret {secret_name}: {str(e)}")
    
    def get_database_credentials(self):
        """Get database credentials"""
        secrets = self.get_secret('boardroom/production/database')
        return {
            'host': secrets['host'],
            'port': secrets['port'],
            'database': secrets['database'],
            'username': secrets['username'],
            'password': secrets['password']
        }
    
    def get_api_keys(self):
        """Get external API keys"""
        return self.get_secret('boardroom/production/api-keys')

# Usage
secrets = SecretsManager()
db_config = secrets.get_database_credentials()
DATABASE_URL = f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
```

### Using Kubernetes Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: boardroom-secrets
  namespace: boardroom
type: Opaque
data:
  database-url: cG9zdGdyZXNxbDovL3VzZXI6cGFzc3dvcmRAaG9zdDo1NDMyL2RiCg==
  redis-url: cmVkaXM6Ly86cGFzc3dvcmRAcmVkaXM6NjM3OS8wCg==
  jwt-secret: c3VwZXItc2VjcmV0LWp3dC1rZXkK
  
---
# Using secrets in deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boardroom-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: boardroom-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: boardroom-secrets
              key: redis-url
```

### Using HashiCorp Vault

```python
# config/vault.py
import hvac
from functools import lru_cache

class VaultClient:
    def __init__(self, url, token):
        self.client = hvac.Client(url=url, token=token)
        if not self.client.is_authenticated():
            raise Exception("Vault authentication failed")
    
    @lru_cache(maxsize=32)
    def read_secret(self, path):
        """Read secret from Vault with caching"""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']
    
    def get_database_config(self):
        """Get dynamic database credentials"""
        response = self.client.read(
            'database/creds/boardroom-production'
        )
        return {
            'username': response['data']['username'],
            'password': response['data']['password']
        }

# Usage
vault = VaultClient(
    url='https://vault.boardroom.com',
    token=os.environ['VAULT_TOKEN']
)
db_creds = vault.get_database_config()
```

## Configuration Management

### Configuration Hierarchy

```python
# config/settings.py
import os
from pathlib import Path

class Config:
    """Base configuration"""
    BASE_DIR = Path(__file__).resolve().parent.parent
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = False
    TESTING = False
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL')
    
    # Security
    CORS_ORIGINS = []
    ALLOWED_HOSTS = []
    
    @classmethod
    def init_app(cls, app):
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DATABASE_URL = 'postgresql://dev:dev@localhost/boardroom_dev'
    REDIS_URL = 'redis://localhost:6379/0'
    CORS_ORIGINS = ['http://localhost:3000']
    
    @classmethod
    def init_app(cls, app):
        # Development specific initialization
        import logging
        logging.basicConfig(level=logging.DEBUG)

class StagingConfig(Config):
    """Staging configuration"""
    DEBUG = False
    TESTING = True
    
    @classmethod
    def init_app(cls, app):
        # Staging specific initialization
        pass

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        # Production specific initialization
        # Set up production logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler(
            'logs/boardroom.log',
            maxBytes=10485760,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

config = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('ENVIRONMENT', 'development')
    return config.get(env, config['default'])
```

### Feature Flags

```python
# config/features.py
import os
import ldclient
from ldclient.config import Config

class FeatureFlags:
    def __init__(self):
        self.env = os.environ.get('ENVIRONMENT', 'development')
        
        if self.env == 'production':
            # Use LaunchDarkly for production
            ldclient.set_config(Config(
                os.environ['LAUNCHDARKLY_SDK_KEY']
            ))
            self.client = ldclient.get()
        else:
            # Use environment variables for non-production
            self.client = None
    
    def is_enabled(self, flag_name, user=None, default=False):
        """Check if feature flag is enabled"""
        if self.env == 'production' and self.client:
            return self.client.variation(
                flag_name,
                user or {'key': 'anonymous'},
                default
            )
        else:
            # Check environment variable
            env_var = f"FEATURE_{flag_name.upper()}"
            return os.environ.get(env_var, str(default)).lower() == 'true'
    
    def get_variation(self, flag_name, user=None, default=None):
        """Get feature flag variation"""
        if self.env == 'production' and self.client:
            return self.client.variation(
                flag_name,
                user or {'key': 'anonymous'},
                default
            )
        else:
            env_var = f"FEATURE_{flag_name.upper()}"
            return os.environ.get(env_var, default)

# Usage
flags = FeatureFlags()

if flags.is_enabled('new_dashboard', user={'key': user_id}):
    # Show new dashboard
    pass

rate_limit = flags.get_variation('api_rate_limit', default=100)
```

## Environment-Specific Configurations

### Database Configuration

```python
# config/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool, QueuePool

def get_database_config():
    """Get database configuration based on environment"""
    env = os.environ.get('ENVIRONMENT', 'development')
    
    if env == 'development':
        return {
            'url': os.environ.get('DATABASE_URL'),
            'pool_class': NullPool,
            'echo': True
        }
    elif env == 'staging':
        return {
            'url': os.environ.get('DATABASE_URL'),
            'pool_class': QueuePool,
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'echo': False
        }
    elif env == 'production':
        return {
            'url': os.environ.get('DATABASE_URL'),
            'pool_class': QueuePool,
            'pool_size': 20,
            'max_overflow': 40,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'echo': False,
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 10
            }
        }

# Create engine
db_config = get_database_config()
engine = create_engine(**db_config)
```

### Cache Configuration

```python
# config/cache.py
import os
import redis
from functools import lru_cache

@lru_cache(maxsize=1)
def get_redis_client():
    """Get Redis client based on environment"""
    env = os.environ.get('ENVIRONMENT', 'development')
    
    if env == 'development':
        return redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
    elif env == 'staging':
        return redis.Redis.from_url(
            os.environ.get('REDIS_URL'),
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 1,  # TCP_KEEPINTVL
                3: 5,  # TCP_KEEPCNT
            }
        )
    elif env == 'production':
        # Redis Sentinel for production
        sentinel = redis.sentinel.Sentinel([
            ('sentinel1.boardroom.com', 26379),
            ('sentinel2.boardroom.com', 26379),
            ('sentinel3.boardroom.com', 26379),
        ])
        return sentinel.master_for(
            'boardroom-master',
            socket_timeout=0.1,
            password=os.environ.get('REDIS_PASSWORD')
        )
```

## Monitoring Configuration

### Prometheus Configuration

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: '${ENVIRONMENT}'
    region: '${AWS_REGION}'

scrape_configs:
  - job_name: 'boardroom-backend'
    static_configs:
      - targets: ${BACKEND_TARGETS}
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        regex: '([^:]+):.*'
        replacement: '$1'
    
  - job_name: 'boardroom-frontend'
    static_configs:
      - targets: ${FRONTEND_TARGETS}
      
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
      
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

remote_write:
  - url: ${PROMETHEUS_REMOTE_WRITE_URL}
    basic_auth:
      username: ${PROMETHEUS_REMOTE_WRITE_USERNAME}
      password: ${PROMETHEUS_REMOTE_WRITE_PASSWORD}
```

### Logging Configuration

```python
# config/logging.py
import os
import logging.config

def get_logging_config():
    """Get logging configuration based on environment"""
    env = os.environ.get('ENVIRONMENT', 'development')
    
    base_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'json': {
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    }
    
    if env == 'production':
        # Add production handlers
        base_config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'json',
            'filename': '/var/log/boardroom/app.log',
            'maxBytes': 10485760,
            'backupCount': 5
        }
        base_config['handlers']['sentry'] = {
            'class': 'sentry_sdk.integrations.logging.EventHandler',
            'level': 'ERROR'
        }
        base_config['root']['handlers'] = ['console', 'file', 'sentry']
    
    return base_config

# Apply configuration
logging.config.dictConfig(get_logging_config())
```

## Best Practices

### 1. Environment Variable Management

```bash
# Use a .env.example file
# .env.example
DATABASE_URL=postgresql://user:password@host:port/database
REDIS_URL=redis://host:port/db
SECRET_KEY=your-secret-key-here
# Add more examples...

# Script to validate environment
# scripts/validate_env.py
import os
import sys

required_vars = [
    'DATABASE_URL',
    'REDIS_URL',
    'SECRET_KEY',
    'JWT_SECRET_KEY'
]

missing = []
for var in required_vars:
    if not os.environ.get(var):
        missing.append(var)

if missing:
    print(f"Missing environment variables: {', '.join(missing)}")
    sys.exit(1)
```

### 2. Configuration Validation

```python
# config/validator.py
from pydantic import BaseSettings, validator, PostgresDsn, RedisDsn

class Settings(BaseSettings):
    # Application
    environment: str
    debug: bool = False
    
    # Database
    database_url: PostgresDsn
    db_pool_size: int = 20
    
    # Redis
    redis_url: RedisDsn
    
    # Security
    secret_key: str
    jwt_secret_key: str
    jwt_algorithm: str = 'HS256'
    
    @validator('secret_key')
    def secret_key_strength(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters')
        return v
    
    @validator('environment')
    def environment_valid(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Invalid environment')
        return v
    
    class Config:
        env_file = f".env.{os.environ.get('ENVIRONMENT', 'development')}"

# Validate on startup
settings = Settings()
```

### 3. Dynamic Configuration Updates

```python
# config/dynamic.py
import threading
import time
from typing import Dict, Any

class DynamicConfig:
    def __init__(self, refresh_interval: int = 300):
        self._config: Dict[str, Any] = {}
        self._refresh_interval = refresh_interval
        self._stop_event = threading.Event()
        self._refresh_thread = None
        
    def start(self):
        """Start configuration refresh thread"""
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True
        )
        self._refresh_thread.start()
    
    def stop(self):
        """Stop configuration refresh"""
        self._stop_event.set()
        if self._refresh_thread:
            self._refresh_thread.join()
    
    def _refresh_loop(self):
        """Refresh configuration periodically"""
        while not self._stop_event.is_set():
            try:
                self._refresh_config()
            except Exception as e:
                logger.error(f"Failed to refresh config: {e}")
            self._stop_event.wait(self._refresh_interval)
    
    def _refresh_config(self):
        """Refresh configuration from source"""
        # Fetch from API, database, or external service
        new_config = self._fetch_config()
        self._config.update(new_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)

# Usage
dynamic_config = DynamicConfig()
dynamic_config.start()

# Get dynamic value
rate_limit = dynamic_config.get('api_rate_limit', 100)
```

---

For more information, see the [Deployment Guide](./deployment-guide.md) or the [Security Checklist](./security-checklist.md).