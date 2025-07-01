#!/bin/bash
# Database Migration Script for Boardroom AI

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Alembic is available
if ! command -v uv &> /dev/null; then
    print_error "UV is not installed. Please install UV package manager"
    exit 1
fi

# Function to show help
show_help() {
    echo "Database Migration Script for Boardroom AI"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  init      Initialize Alembic (first time setup)"
    echo "  check     Check current migration status"
    echo "  generate  Generate new migration from model changes"
    echo "  upgrade   Apply pending migrations"
    echo "  downgrade Downgrade to previous migration"
    echo "  history   Show migration history"
    echo "  current   Show current migration revision"
    echo "  schema    Apply manual schema migration"
    echo "  offline   Generate offline migration SQL"
    echo "  help      Show this help message"
}

# Function to check database connection
check_db_connection() {
    print_status "Checking database connection..."
    python -c "
import asyncio
import sys
from app.services.database import DatabaseService

async def test_connection():
    try:
        db = DatabaseService()
        async with db.get_session() as session:
            print('✓ Database connection successful')
            return True
    except Exception as e:
        print(f'✗ Database connection failed: {e}')
        return False

result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
" 2>/dev/null
}

# Main command handling
case "$1" in
    "init")
        print_status "Initializing Alembic..."
        if [ -d "alembic" ]; then
            print_warning "Alembic already initialized"
        else
            uv run alembic init alembic
            print_status "Alembic initialized successfully"
        fi
        ;;
    
    "check")
        print_status "Checking migration status..."
        if check_db_connection; then
            uv run alembic current
            uv run alembic show head
        else
            print_warning "Database not available. Check offline migration files in alembic/versions/"
        fi
        ;;
    
    "generate")
        if [ -z "$2" ]; then
            print_error "Please provide a migration message"
            echo "Usage: $0 generate 'migration message'"
            exit 1
        fi
        print_status "Generating migration: $2"
        if check_db_connection; then
            uv run alembic revision --autogenerate -m "$2"
        else
            print_warning "Database not available. Generating offline migration..."
            uv run alembic revision -m "$2"
        fi
        ;;
    
    "upgrade")
        print_status "Applying migrations..."
        if check_db_connection; then
            uv run alembic upgrade head
            print_status "Migrations applied successfully"
        else
            print_error "Database not available. Cannot apply migrations."
            print_status "To apply manually, run the SQL files in alembic/versions/ on your database"
        fi
        ;;
    
    "downgrade")
        REVISION=${2:-"-1"}
        print_warning "Downgrading to revision: $REVISION"
        if check_db_connection; then
            uv run alembic downgrade "$REVISION"
        else
            print_error "Database not available. Cannot downgrade migrations."
        fi
        ;;
    
    "history")
        print_status "Migration history:"
        uv run alembic history 2>/dev/null || {
            print_warning "Cannot connect to database. Listing migration files:"
            find alembic/versions/ -name "*.py" -type f | sort
        }
        ;;
    
    "current")
        print_status "Current migration:"
        if check_db_connection; then
            uv run alembic current
        else
            print_warning "Database not available. Check latest migration file in alembic/versions/"
        fi
        ;;
    
    "offline")
        print_status "Generating offline SQL migration..."
        uv run alembic upgrade head --sql > migration_script.sql 2>/dev/null || {
            print_warning "Generating manual migration from schema_new.sql"
            cp schema_new.sql migration_script.sql
            print_status "Manual migration script created: migration_script.sql"
        }
        ;;
    
    "schema")
        print_status "Applying manual schema migration..."
        if check_db_connection; then
            python scripts/migrate_schema.py
        else
            print_error "Database not available. Use 'offline' command to generate SQL script"
        fi
        ;;
    
    "help"|"")
        show_help
        ;;
    
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac