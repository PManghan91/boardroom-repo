# Testing Approach

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: Developers  
**Next Review**: As testing needs evolve  

## Overview

This document outlines the testing strategy for Boardroom AI, covering both backend (Python/FastAPI) and frontend (TypeScript/Next.js) testing approaches. Our goal is to maintain high code quality while keeping testing practical for solo development.

## Testing Philosophy

### Core Principles
1. **Test what matters**: Focus on critical business logic and user paths
2. **Fast feedback**: Quick test execution for rapid development
3. **Maintainable tests**: Clear, simple tests that are easy to update
4. **Progressive coverage**: Start with critical paths, expand over time

### Testing Pyramid

```
        E2E Tests (Future)
       /                \
      /  Integration     \
     /      Tests         \
    /                      \
   /     Unit Tests         \
  /__________________________\
```

- **Unit Tests**: 60% - Fast, isolated component testing
- **Integration Tests**: 30% - API and service interaction testing
- **E2E Tests**: 10% - Critical user journey validation (future)

## Backend Testing (Python/FastAPI)

### Test Structure

```
tests/
├── unit/              # Isolated component tests
│   ├── test_auth.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/       # API endpoint tests
│   ├── test_api_auth.py
│   ├── test_api_chatbot.py
│   └── test_api_health.py
├── performance/       # Load and performance tests
│   └── test_performance.py
├── fixtures/          # Shared test data
│   └── data_fixtures.py
├── conftest_basic.py  # Basic fixtures (no DB)
├── conftest_full.py   # Full fixtures (with DB)
└── run_tests.py       # Test runner utility
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests

# Run with coverage
pytest --cov=app --cov-report=html

# Run tests in parallel
pytest -n auto

# Run specific test file
pytest tests/unit/test_auth.py
```

### Writing Unit Tests

```python
import pytest
from unittest.mock import Mock, AsyncMock

from app.services.user_service import UserService
from tests.fixtures.data_fixtures import UserFactory

@pytest.mark.unit
class TestUserService:
    """Test user service operations."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def user_service(self, mock_db):
        """Create user service instance."""
        return UserService(db=mock_db)
    
    async def test_create_user_success(self, user_service, mock_db):
        """Test successful user creation."""
        # Arrange
        user_data = UserFactory.build()
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        
        # Act
        result = await user_service.create_user(user_data)
        
        # Assert
        assert result.email == user_data.email
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
```

### Writing Integration Tests

```python
import pytest
from httpx import AsyncClient

from app.main import app
from tests.fixtures.data_fixtures import UserFactory

@pytest.mark.integration
class TestAuthAPI:
    """Test authentication API endpoints."""
    
    async def test_register_user(self, client: AsyncClient):
        """Test user registration endpoint."""
        # Arrange
        user_data = UserFactory.build()
        
        # Act
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": user_data.email,
                "password": "SecurePass123!",
                "full_name": user_data.full_name
            }
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == user_data.email
        assert "access_token" in data["token"]
```

### Test Fixtures

We use fixtures for common test setup:

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from httpx import AsyncClient

from app.main import app
from app.services.database import database_service

@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    # Setup test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()

@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

### Performance Testing

```python
import pytest
import asyncio
from locust import HttpUser, task, between

@pytest.mark.slow
@pytest.mark.performance
async def test_api_performance():
    """Test API response time under load."""
    async def make_request():
        async with AsyncClient(app=app) as client:
            response = await client.get("/api/v1/health")
            return response.elapsed.total_seconds()
    
    # Run 100 concurrent requests
    tasks = [make_request() for _ in range(100)]
    response_times = await asyncio.gather(*tasks)
    
    # Assert 95th percentile < 200ms
    sorted_times = sorted(response_times)
    p95 = sorted_times[int(len(sorted_times) * 0.95)]
    assert p95 < 0.2
```

## Frontend Testing (TypeScript/Next.js)

### Test Structure

```
src/
├── components/
│   └── auth/
│       ├── LoginModal.tsx
│       └── __tests__/
│           └── LoginModal.test.tsx
├── hooks/
│   ├── useBoardroom.ts
│   └── __tests__/
│       └── useBoardroom.test.ts
└── test/
    └── setup.ts
```

### Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run specific test file
npm test LoginModal.test.tsx
```

### Writing Component Tests

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { LoginModal } from "@/components/auth/LoginModal"

describe("LoginModal", () => {
  const mockOnSuccess = jest.fn()
  
  beforeEach(() => {
    mockOnSuccess.mockClear()
  })
  
  it("should handle successful login", async () => {
    // Arrange
    const user = userEvent.setup()
    render(<LoginModal onSuccess={mockOnSuccess} />)
    
    // Act
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole("button", { name: /login/i })
    
    await user.type(emailInput, "test@example.com")
    await user.type(passwordInput, "password123")
    await user.click(submitButton)
    
    // Assert
    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled()
    })
  })
  
  it("should display validation errors", async () => {
    // Arrange
    const user = userEvent.setup()
    render(<LoginModal onSuccess={mockOnSuccess} />)
    
    // Act - submit without filling form
    const submitButton = screen.getByRole("button", { name: /login/i })
    await user.click(submitButton)
    
    // Assert
    expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/password is required/i)).toBeInTheDocument()
  })
})
```

### Writing Hook Tests

```typescript
import { renderHook, act } from "@testing-library/react"
import { useBoardroom } from "@/hooks/useBoardroom"

describe("useBoardroom", () => {
  it("should fetch boardroom data", async () => {
    // Arrange
    const { result } = renderHook(() => useBoardroom("room-123"))
    
    // Initial state
    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
    
    // Wait for data
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    
    // Assert
    expect(result.current.data).toEqual({
      id: "room-123",
      name: "Test Room",
      // ... other properties
    })
  })
})
```

## Test Data Management

### Backend Test Data

Use factories for consistent test data:

```python
# tests/fixtures/data_fixtures.py
from faker import Faker
from datetime import datetime

fake = Faker()

class UserFactory:
    @staticmethod
    def build(**kwargs):
        return {
            "email": kwargs.get("email", fake.email()),
            "full_name": kwargs.get("full_name", fake.name()),
            "is_active": kwargs.get("is_active", True),
            "created_at": kwargs.get("created_at", datetime.utcnow())
        }
```

### Frontend Test Data

```typescript
// src/test/factories.ts
export const createMockUser = (overrides = {}) => ({
  id: "user-123",
  email: "test@example.com",
  fullName: "Test User",
  isActive: true,
  ...overrides
})

export const createMockBoardroom = (overrides = {}) => ({
  id: "room-123",
  name: "Test Boardroom",
  maxParticipants: 10,
  ...overrides
})
```

## Mocking Strategies

### Backend Mocking

```python
# Mock external services
@pytest.fixture
def mock_openai():
    with patch("app.services.ai_service.openai") as mock:
        mock.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="AI response"))]
        )
        yield mock

# Mock database
@pytest.fixture
def mock_db_session():
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session
```

### Frontend Mocking

```typescript
// Mock API calls
jest.mock("@/lib/api", () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn()
  }
}))

// Mock Next.js navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn()
  }),
  useSearchParams: () => ({
    get: jest.fn()
  })
}))
```

## Coverage Requirements

### Minimum Coverage: 70%

**Backend Coverage Goals:**
- Unit tests: 80% coverage
- Integration tests: 60% coverage
- Critical paths: 90% coverage

**Frontend Coverage Goals:**
- Components: 70% coverage
- Hooks: 80% coverage
- Services: 75% coverage

### Coverage Reports

```bash
# Backend coverage report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html

# Frontend coverage report
npm run test:coverage
# Open coverage/index.html
```

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Pull requests
- Pushes to main/develop branches
- Scheduled daily runs

### Test Stages

1. **Quick Tests** (< 2 min)
   - Linting and formatting
   - Unit tests
   - Type checking

2. **Full Tests** (< 10 min)
   - All unit tests
   - Integration tests
   - Coverage reporting

3. **Extended Tests** (nightly)
   - Performance tests
   - Security scanning
   - Full E2E suite (future)

## Best Practices

### Do's
1. ✅ Write tests before fixing bugs
2. ✅ Use descriptive test names
3. ✅ Keep tests focused and small
4. ✅ Use fixtures for common setup
5. ✅ Test edge cases and errors
6. ✅ Mock external dependencies
7. ✅ Run tests before committing

### Don'ts
1. ❌ Test implementation details
2. ❌ Write overly complex tests
3. ❌ Ignore flaky tests
4. ❌ Share state between tests
5. ❌ Test framework code
6. ❌ Skip error scenarios

## Test Maintenance

### Regular Tasks
- Review and update slow tests monthly
- Refactor duplicate test code
- Update test data to match production
- Review coverage reports quarterly

### Dealing with Flaky Tests
1. Identify flaky tests in CI logs
2. Add retry logic for network calls
3. Increase timeouts for async operations
4. Use explicit waits instead of sleep
5. Mark as `@pytest.mark.flaky` temporarily

## Future Improvements

1. **E2E Testing**: Playwright for critical user journeys
2. **Visual Regression**: Screenshot comparison
3. **Contract Testing**: API contract validation
4. **Mutation Testing**: Test quality validation
5. **Load Testing**: Locust for stress testing

## Related Documentation

- [Development Setup](./setup.md)
- [Coding Standards](./coding_standards.md)
- [CI/CD Pipeline](../deployment/ci_cd.md)
- [API Documentation](../api/quick_start.md)

---

**Testing Help**: Run `pytest --help` or check test examples in the codebase.