-- Boardroom AI Database Schema
-- Updated to align with SQLModel definitions and include proper relationships

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table with enhanced constraints
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT users_full_name_check CHECK (full_name IS NULL OR LENGTH(TRIM(full_name)) > 0)
);

-- Boardrooms table with enhanced constraints and relationships
CREATE TABLE boardrooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    max_participants INTEGER DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Foreign key constraints
    CONSTRAINT fk_boardrooms_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Check constraints
    CONSTRAINT boardrooms_name_check CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT boardrooms_max_participants_check CHECK (max_participants > 0 AND max_participants <= 100)
);

-- Sessions table with enhanced constraints and relationships
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    boardroom_id UUID NOT NULL,
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Foreign key constraints
    CONSTRAINT fk_sessions_boardroom FOREIGN KEY (boardroom_id) REFERENCES boardrooms(id) ON DELETE CASCADE,
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Check constraints
    CONSTRAINT sessions_title_check CHECK (LENGTH(TRIM(title)) > 0),
    CONSTRAINT sessions_status_check CHECK (status IN ('active', 'completed', 'paused', 'cancelled')),
    CONSTRAINT sessions_dates_check CHECK (ended_at IS NULL OR ended_at >= started_at)
);

-- Threads table with enhanced constraints and relationships
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    thread_type VARCHAR(50) NOT NULL DEFAULT 'discussion',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Foreign key constraints
    CONSTRAINT fk_threads_session FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_threads_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Check constraints
    CONSTRAINT threads_title_check CHECK (LENGTH(TRIM(title)) > 0),
    CONSTRAINT threads_type_check CHECK (thread_type IN ('discussion', 'decision', 'action_item', 'note')),
    CONSTRAINT threads_status_check CHECK (status IN ('active', 'closed', 'archived')),
    CONSTRAINT threads_priority_check CHECK (priority >= 1 AND priority <= 5)
);

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at);

CREATE INDEX idx_boardrooms_owner ON boardrooms(owner_id);
CREATE INDEX idx_boardrooms_active ON boardrooms(is_active);
CREATE INDEX idx_boardrooms_created_at ON boardrooms(created_at);

CREATE INDEX idx_sessions_boardroom ON sessions(boardroom_id);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_started_at ON sessions(started_at);

CREATE INDEX idx_threads_session ON threads(session_id);
CREATE INDEX idx_threads_user ON threads(user_id);
CREATE INDEX idx_threads_status ON threads(status);
CREATE INDEX idx_threads_type ON threads(thread_type);
CREATE INDEX idx_threads_created_at ON threads(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers to all tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_boardrooms_updated_at BEFORE UPDATE ON boardrooms FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_threads_updated_at BEFORE UPDATE ON threads FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing (optional)
-- This can be removed in production
/*
INSERT INTO users (email, hashed_password, full_name, is_verified) VALUES
('admin@boardroom.ai', '$2b$12$dummy_hash', 'System Admin', true),
('user@example.com', '$2b$12$dummy_hash', 'Test User', true);

INSERT INTO boardrooms (name, description, owner_id) VALUES
('Main Boardroom', 'Primary meeting space for strategic discussions', (SELECT id FROM users WHERE email = 'admin@boardroom.ai'));
*/