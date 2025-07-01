"""Common test data fixtures for consistent test data generation.

This module provides reusable fixtures for generating test data that
maintains consistency across different test modules while allowing
for customization when needed.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any
from faker import Faker
from uuid import uuid4

fake = Faker()


@pytest.fixture
def user_factory():
    """Factory for creating user test data with customizable attributes."""
    def _create_user(
        email: str = None,
        username: str = None,
        role: str = "user",
        is_active: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "email": email or fake.email(),
            "username": username or fake.user_name(),
            "full_name": fake.name(),
            "password": "TestPassword123!",
            "role": role,
            "is_active": is_active,
            "is_locked": False,
            "failed_login_attempts": 0,
            "last_login": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **kwargs
        }
    return _create_user


@pytest.fixture
def boardroom_factory():
    """Factory for creating boardroom test data with customizable attributes."""
    def _create_boardroom(
        name: str = None,
        owner_id: str = None,
        is_active: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "name": name or fake.company(),
            "description": fake.text(max_nb_chars=200),
            "owner_id": owner_id or str(uuid4()),
            "is_active": is_active,
            "settings": {
                "max_participants": fake.random_int(min=2, max=20),
                "voting_enabled": fake.boolean(),
                "public": fake.boolean(),
                "moderation_enabled": False,
                "ai_assistance": True
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **kwargs
        }
    return _create_boardroom


@pytest.fixture
def session_factory():
    """Factory for creating session test data with customizable attributes."""
    def _create_session(
        boardroom_id: str = None,
        owner_id: str = None,
        status: str = "active",
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "boardroom_id": boardroom_id or str(uuid4()),
            "owner_id": owner_id or str(uuid4()),
            "title": fake.sentence(nb_words=4),
            "description": fake.text(max_nb_chars=300),
            "status": status,
            "session_type": fake.random_element(elements=["discussion", "decision", "brainstorm"]),
            "metadata": {
                "duration_minutes": fake.random_int(min=30, max=180),
                "participant_limit": fake.random_int(min=2, max=15),
                "recording_enabled": fake.boolean(),
                "ai_moderation": fake.boolean()
            },
            "started_at": datetime.utcnow() if status == "active" else None,
            "ended_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **kwargs
        }
    return _create_session


@pytest.fixture
def thread_factory():
    """Factory for creating thread test data with customizable attributes."""
    def _create_thread(
        session_id: str = None,
        author_id: str = None,
        thread_type: str = "discussion",
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "session_id": session_id or str(uuid4()),
            "author_id": author_id or str(uuid4()),
            "title": fake.sentence(nb_words=6),
            "content": fake.text(max_nb_chars=500),
            "thread_type": thread_type,
            "is_private": fake.boolean(),
            "metadata": {
                "tags": [fake.word() for _ in range(fake.random_int(min=1, max=5))],
                "priority": fake.random_element(elements=["low", "medium", "high"]),
                "estimated_time": fake.random_int(min=5, max=60),
                "requires_vote": fake.boolean()
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **kwargs
        }
    return _create_thread


@pytest.fixture
def message_factory():
    """Factory for creating message test data with customizable attributes."""
    def _create_message(
        thread_id: str = None,
        user_id: str = None,
        message_type: str = "user",
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "thread_id": thread_id or str(uuid4()),
            "user_id": user_id or str(uuid4()),
            "content": fake.text(max_nb_chars=1000),
            "message_type": message_type,
            "metadata": {
                "edited": False,
                "reply_to": None,
                "attachments": [],
                "mentions": [],
                "reactions": {}
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **kwargs
        }
    return _create_message


@pytest.fixture
def decision_factory():
    """Factory for creating decision test data with customizable attributes."""
    def _create_decision(
        session_id: str = None,
        created_by: str = None,
        decision_type: str = "vote",
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "session_id": session_id or str(uuid4()),
            "created_by": created_by or str(uuid4()),
            "title": fake.sentence(nb_words=4),
            "description": fake.text(max_nb_chars=300),
            "decision_type": decision_type,
            "options": [
                {"id": str(uuid4()), "text": fake.sentence(nb_words=3), "votes": 0}
                for _ in range(fake.random_int(min=2, max=5))
            ],
            "voting_deadline": datetime.utcnow() + timedelta(days=1),
            "is_anonymous": fake.boolean(),
            "requires_unanimous": fake.boolean(),
            "status": "open",
            "metadata": {
                "min_participation": fake.random_int(min=1, max=10),
                "allow_abstain": fake.boolean(),
                "change_vote": fake.boolean()
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **kwargs
        }
    return _create_decision


@pytest.fixture
def auth_token_factory():
    """Factory for creating authentication token test data."""
    def _create_token(
        user_id: str = None,
        token_type: str = "access",
        expires_in: int = 3600,
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "token": f"test_{token_type}_token_{fake.uuid4()}",
            "token_type": token_type,
            "user_id": user_id or str(uuid4()),
            "expires_at": datetime.utcnow() + timedelta(seconds=expires_in),
            "created_at": datetime.utcnow(),
            "is_revoked": False,
            **kwargs
        }
    return _create_token


@pytest.fixture
def api_response_factory():
    """Factory for creating consistent API response test data."""
    def _create_response(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        **kwargs
    ) -> Dict[str, Any]:
        response = {
            "message": message,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        if data is not None:
            response["data"] = data
            
        return response
    return _create_response


@pytest.fixture
def error_response_factory():
    """Factory for creating error response test data."""
    def _create_error(
        error_code: str = "VALIDATION_ERROR",
        message: str = "Validation failed",
        status_code: int = 400,
        details: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        return {
            "error": {
                "code": status_code,
                "message": message,
                "type": error_code.lower(),
                "details": details or [],
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        }
    return _create_error


@pytest.fixture
def bulk_test_data():
    """Generate bulk test data for performance and load testing."""
    def _generate_bulk_data(
        count: int,
        data_type: str,
        factory_func,
        **factory_kwargs
    ) -> List[Dict[str, Any]]:
        """Generate a list of test data using the specified factory."""
        return [factory_func(**factory_kwargs) for _ in range(count)]
    
    return _generate_bulk_data


@pytest.fixture
def realistic_test_scenario():
    """Create a realistic test scenario with related data."""
    def _create_scenario(
        num_users: int = 5,
        num_boardrooms: int = 2,
        num_sessions: int = 3,
        num_threads_per_session: int = 4
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Create a complete test scenario with interrelated data."""
        
        # Create users
        users = []
        for i in range(num_users):
            users.append({
                "id": str(uuid4()),
                "email": f"user{i}@test.com",
                "username": f"testuser{i}",
                "full_name": fake.name(),
                "role": "admin" if i == 0 else "user",
                "is_active": True
            })
        
        # Create boardrooms
        boardrooms = []
        for i in range(num_boardrooms):
            boardrooms.append({
                "id": str(uuid4()),
                "name": f"Test Boardroom {i+1}",
                "description": fake.text(max_nb_chars=200),
                "owner_id": users[0]["id"],  # First user owns all boardrooms
                "is_active": True
            })
        
        # Create sessions
        sessions = []
        for i in range(num_sessions):
            boardroom = boardrooms[i % len(boardrooms)]
            sessions.append({
                "id": str(uuid4()),
                "boardroom_id": boardroom["id"],
                "owner_id": users[i % len(users)]["id"],
                "title": f"Test Session {i+1}",
                "status": "active",
                "session_type": "discussion"
            })
        
        # Create threads
        threads = []
        for session in sessions:
            for j in range(num_threads_per_session):
                threads.append({
                    "id": str(uuid4()),
                    "session_id": session["id"],
                    "author_id": users[j % len(users)]["id"],
                    "title": f"Thread {j+1} for {session['title']}",
                    "content": fake.text(max_nb_chars=500),
                    "thread_type": "discussion"
                })
        
        return {
            "users": users,
            "boardrooms": boardrooms,
            "sessions": sessions,
            "threads": threads
        }
    
    return _create_scenario