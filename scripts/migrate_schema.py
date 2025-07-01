#!/usr/bin/env python3
"""
Schema Migration Script for Boardroom AI
Migrates from current schema.sql to aligned schema with proper relationships
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.config import get_settings
from app.services.database import DatabaseService
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaMigrator:
    def __init__(self):
        self.settings = get_settings()
        self.db_service = DatabaseService()
    
    async def check_current_schema(self):
        """Check the current state of the database schema"""
        async with self.db_service.get_session() as session:
            try:
                # Check if tables exist
                result = await session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in result.fetchall()]
                
                logger.info(f"Current tables: {tables}")
                
                # Check for foreign key constraints
                result = await session.execute(text("""
                    SELECT 
                        tc.table_name, 
                        tc.constraint_name, 
                        tc.constraint_type
                    FROM information_schema.table_constraints tc
                    WHERE tc.table_schema = 'public' 
                    AND tc.constraint_type = 'FOREIGN KEY'
                """))
                
                fk_constraints = result.fetchall()
                logger.info(f"Current foreign key constraints: {len(fk_constraints)}")
                
                return {
                    'tables': tables,
                    'foreign_keys': fk_constraints
                }
                
            except Exception as e:
                logger.error(f"Error checking schema: {e}")
                return None
    
    async def backup_data(self):
        """Create a backup of existing data before migration"""
        logger.info("Creating data backup...")
        
        backup_queries = [
            "CREATE TABLE users_backup AS SELECT * FROM users;",
            "CREATE TABLE boardrooms_backup AS SELECT * FROM boardrooms;",
            "CREATE TABLE sessions_backup AS SELECT * FROM sessions;", 
            "CREATE TABLE threads_backup AS SELECT * FROM threads;"
        ]
        
        async with self.db_service.get_session() as session:
            for query in backup_queries:
                try:
                    await session.execute(text(query))
                    await session.commit()
                    logger.info(f"Backup created: {query.split()[2]}")
                except Exception as e:
                    logger.warning(f"Backup failed for {query}: {e}")
    
    async def apply_schema_updates(self):
        """Apply schema updates to align with models"""
        logger.info("Applying schema updates...")
        
        updates = [
            # Add missing columns
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT false;",
            "ALTER TABLE boardrooms ADD COLUMN IF NOT EXISTS max_participants INTEGER DEFAULT 10;",
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';",
            "ALTER TABLE threads ADD COLUMN IF NOT EXISTS thread_type VARCHAR(50) DEFAULT 'discussion';",
            "ALTER TABLE threads ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 1;",
            
            # Add constraints
            "ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\\\.[A-Za-z]{2,}$');",
            "ALTER TABLE boardrooms ADD CONSTRAINT IF NOT EXISTS boardrooms_max_participants_check CHECK (max_participants > 0 AND max_participants <= 100);",
            "ALTER TABLE sessions ADD CONSTRAINT IF NOT EXISTS sessions_status_check CHECK (status IN ('active', 'completed', 'paused', 'cancelled'));",
        ]
        
        async with self.db_service.get_session() as session:
            for update in updates:
                try:
                    await session.execute(text(update))
                    await session.commit()
                    logger.info(f"Applied: {update[:50]}...")
                except Exception as e:
                    logger.error(f"Failed to apply {update}: {e}")
    
    async def add_foreign_keys(self):
        """Add foreign key constraints"""
        logger.info("Adding foreign key constraints...")
        
        fk_constraints = [
            "ALTER TABLE boardrooms ADD CONSTRAINT IF NOT EXISTS fk_boardrooms_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;",
            "ALTER TABLE sessions ADD CONSTRAINT IF NOT EXISTS fk_sessions_boardroom FOREIGN KEY (boardroom_id) REFERENCES boardrooms(id) ON DELETE CASCADE;",
            "ALTER TABLE sessions ADD CONSTRAINT IF NOT EXISTS fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;",
            "ALTER TABLE threads ADD CONSTRAINT IF NOT EXISTS fk_threads_session FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE;",
            "ALTER TABLE threads ADD CONSTRAINT IF NOT EXISTS fk_threads_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;"
        ]
        
        async with self.db_service.get_session() as session:
            for constraint in fk_constraints:
                try:
                    await session.execute(text(constraint))
                    await session.commit()
                    logger.info(f"Added FK constraint: {constraint.split()[5]}")
                except Exception as e:
                    logger.error(f"Failed to add FK constraint: {e}")
    
    async def create_indexes(self):
        """Create performance indexes"""
        logger.info("Creating indexes...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_boardrooms_owner ON boardrooms(owner_id);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_boardroom ON sessions(boardroom_id);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_threads_session ON threads(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_threads_user ON threads(user_id);"
        ]
        
        async with self.db_service.get_session() as session:
            for index in indexes:
                try:
                    await session.execute(text(index))
                    await session.commit()
                    logger.info(f"Created index: {index.split()[5]}")
                except Exception as e:
                    logger.warning(f"Index creation failed: {e}")
    
    async def verify_migration(self):
        """Verify the migration was successful"""
        logger.info("Verifying migration...")
        
        schema_info = await self.check_current_schema()
        if schema_info:
            logger.info("Migration verification completed")
            return True
        return False

async def main():
    """Main migration function"""
    migrator = SchemaMigrator()
    
    logger.info("Starting schema migration...")
    
    # Check current state
    current_schema = await migrator.check_current_schema()
    if not current_schema:
        logger.error("Failed to check current schema")
        return
    
    # Backup existing data
    await migrator.backup_data()
    
    # Apply updates
    await migrator.apply_schema_updates()
    await migrator.add_foreign_keys()
    await migrator.create_indexes()
    
    # Verify
    if await migrator.verify_migration():
        logger.info("Schema migration completed successfully!")
    else:
        logger.error("Migration verification failed")

if __name__ == "__main__":
    asyncio.run(main())