# Development Setup Guide

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: Solo Developer  
**Next Review**: As needed  

## Overview

This guide provides step-by-step instructions for setting up the Boardroom AI development environment on your local machine. The project consists of a FastAPI backend with LangGraph integration and a Next.js frontend.

## Prerequisites

### Required Software
- **Python 3.13+** (backend)
- **Node.js 24.3.0+** with npm 11.4.2+ (frontend)
- **PostgreSQL 14+** (database)
- **Redis 7+** (caching)
- **Docker & Docker Compose** (optional but recommended)
- **Git** (version control)

### Recommended Tools
- **uv** - Fast Python package manager
- **nvm** - Node version management
- **VS Code** or similar IDE with Python and TypeScript support

## Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd boardroom-repo
```

### 2. Backend Setup

#### Option A: Using uv (Recommended)
```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

#### Option B: Using pip
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Return to root
cd ..
```

### 4. Environment Configuration

#### Backend Configuration
```bash
# Copy example environment file
cp .env.example .env.development

# Edit with your settings
nano .env.development
```

Essential environment variables:
```env
# Application
APP_ENV=development
PROJECT_NAME="Boardroom AI"
DEBUG=true

# Database
POSTGRES_URL="postgresql://user:password@localhost:5432/boardroom_dev"

# LLM Configuration
LLM_API_KEY="your-openai-api-key"
LLM_MODEL="gpt-4o-mini"

# Security
JWT_SECRET_KEY="your-secret-key-change-in-production"

# Optional: Monitoring
LANGFUSE_PUBLIC_KEY="your-langfuse-public-key"
LANGFUSE_SECRET_KEY="your-langfuse-secret-key"
```

#### Frontend Configuration
```bash
cd frontend
cp .env.example .env.local

# Edit frontend environment
nano .env.local
```

Frontend environment variables:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME="Boardroom AI"
```

### 5. Database Setup

#### Option A: Local PostgreSQL
```bash
# Create database
createdb boardroom_dev

# Run migrations
alembic upgrade head
```

#### Option B: Using Supabase
1. Create a project at https://supabase.com
2. Copy the connection string to your `.env.development`
3. Run migrations as above

### 6. Redis Setup (Optional for Development)

```bash
# Using Docker
docker run -d -p 6379:6379 --name redis-dev redis:7-alpine

# Or install locally
# Mac: brew install redis
# Ubuntu: sudo apt-get install redis-server
```

## Running the Application

### Using Docker (Recommended)

```bash
# Start all services
make docker-run-env ENV=development

# Or using docker-compose directly
docker-compose up
```

Services will be available at:
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

### Manual Start

#### Terminal 1: Backend
```bash
# Activate virtual environment
source .venv/bin/activate

# Start FastAPI
make dev
# Or directly:
# uvicorn app.main:app --reload --port 8000
```

#### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

## Verification

### 1. Check Backend Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.03",
  "timestamp": "2025-01-07T..."
}
```

### 2. Access API Documentation
Open http://localhost:8000/docs in your browser

### 3. Access Frontend
Open http://localhost:3000 in your browser

## Common Issues and Solutions

### Issue: Database Connection Failed
**Solution**: 
- Verify PostgreSQL is running
- Check connection string in `.env.development`
- Ensure database exists: `createdb boardroom_dev`

### Issue: Missing Python Dependencies
**Solution**:
```bash
# If using uv
uv sync

# If using pip
pip install -e .
```

### Issue: Frontend Port Already in Use
**Solution**:
- Check what's using port 3000: `lsof -i :3000`
- Stop the process or use a different port
- Frontend will auto-select port 3001 if 3000 is busy

### Issue: Redis Connection Error
**Solution**:
- Redis is optional for development
- To disable: Set `REDIS_URL=""` in `.env.development`
- To enable: Start Redis service

### Issue: LLM API Key Invalid
**Solution**:
- Verify your OpenAI API key is correct
- Check API key has sufficient credits
- For testing, you can use a dummy key but AI features won't work

## IDE Configuration

### VS Code Extensions
Recommended extensions:
- Python
- Pylance
- Black Formatter
- ESLint
- Prettier
- Thunder Client (API testing)

### Settings
`.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

## Next Steps

1. Review the [API Quick Start Guide](../api/quick_start.md)
2. Check [Coding Standards](./coding_standards.md)
3. Explore the [Testing Approach](./testing.md)
4. Set up your development workflow

## Additional Resources

- [System Architecture Overview](../architecture/system_overview.md)
- [Troubleshooting Guide](../operations/troubleshooting.md)
- [API Documentation](http://localhost:8000/docs)

---

**Need Help?** Check the [Troubleshooting Guide](../operations/troubleshooting.md) or review the project README.