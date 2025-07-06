# Testing Procedures Guide

## Overview

This guide provides comprehensive testing procedures for the Boardroom Phase 3 platform. It covers unit testing, integration testing, end-to-end testing, performance testing, and security testing to ensure high-quality, reliable software delivery.

## Testing Philosophy

### Core Principles

1. **Test Early and Often**: Write tests as you develop features
2. **Test at Multiple Levels**: Unit, integration, and end-to-end tests
3. **Focus on Behavior**: Test what the code does, not how it does it
4. **Maintain Test Quality**: Tests should be as maintainable as production code
5. **Automate Everything**: All tests should run automatically in CI/CD

### Testing Pyramid

```
        /\
       /E2E\      <- End-to-End Tests (10%)
      /------\
     /  INT   \   <- Integration Tests (30%)
    /----------\
   /    UNIT    \ <- Unit Tests (60%)
  /--------------\
```

## Test Environment Setup

### Frontend Testing Setup

```bash
# Install testing dependencies
cd frontend
npm install --save-dev @testing-library/react @testing-library/jest-dom
npm install --save-dev @testing-library/user-event jest-environment-jsdom
npm install --save-dev msw whatwg-fetch

# Configure Vitest
# vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData.ts'
      ]
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
```

### Backend Testing Setup

```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov
pip install httpx faker factory-boy
pip install pytest-mock pytest-env

# Configure pytest
# pytest.ini
[tool:pytest]
minversion = 6.0
addopts = -ra -q --strict-markers --cov=app --cov-report=html
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

[tool:pytest:markers]
slow: marks tests as slow (deselect with '-m "not slow"')
integration: marks tests as integration tests
unit: marks tests as unit tests
```

### Test Database Setup

```python
# tests/conftest.py
import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base

# Override database URL for tests
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/boardroom_test"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    """Create database session for tests"""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()
```

## Unit Testing

### Frontend Unit Tests

#### Component Testing

```typescript
// UserCard.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UserCard } from '@/components/UserCard'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Test utilities
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  })
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('UserCard', () => {
  const mockUser = {
    id: '123',
    name: 'John Doe',
    email: 'john@example.com',
    avatar: 'https://example.com/avatar.jpg',
    role: 'admin'
  }
  
  it('renders user information correctly', () => {
    render(<UserCard user={mockUser} />, { wrapper: createWrapper() })
    
    expect(screen.getByText(mockUser.name)).toBeInTheDocument()
    expect(screen.getByText(mockUser.email)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: mockUser.name })).toHaveAttribute(
      'src',
      mockUser.avatar
    )
  })
  
  it('handles click events', async () => {
    const handleClick = jest.fn()
    const user = userEvent.setup()
    
    render(
      <UserCard user={mockUser} onClick={handleClick} />,
      { wrapper: createWrapper() }
    )
    
    await user.click(screen.getByRole('article'))
    
    expect(handleClick).toHaveBeenCalledWith(mockUser)
  })
  
  it('shows loading state', () => {
    render(<UserCard isLoading />, { wrapper: createWrapper() })
    
    expect(screen.getByTestId('user-card-skeleton')).toBeInTheDocument()
  })
  
  it('handles error state gracefully', () => {
    render(<UserCard error="Failed to load user" />, { wrapper: createWrapper() })
    
    expect(screen.getByText('Failed to load user')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
```

#### Hook Testing

```typescript
// useAuth.test.ts
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAuth } from '@/hooks/useAuth'
import { authService } from '@/services/auth.service'

jest.mock('@/services/auth.service')

describe('useAuth', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })
  
  it('handles login successfully', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    authService.login = jest.fn().mockResolvedValue({
      user: mockUser,
      token: 'mock-token'
    })
    
    const { result } = renderHook(() => useAuth())
    
    await act(async () => {
      await result.current.login('test@example.com', 'password')
    })
    
    expect(result.current.user).toEqual(mockUser)
    expect(result.current.isAuthenticated).toBe(true)
    expect(authService.login).toHaveBeenCalledWith('test@example.com', 'password')
  })
  
  it('handles login failure', async () => {
    const error = new Error('Invalid credentials')
    authService.login = jest.fn().mockRejectedValue(error)
    
    const { result } = renderHook(() => useAuth())
    
    await act(async () => {
      await expect(
        result.current.login('test@example.com', 'wrong-password')
      ).rejects.toThrow('Invalid credentials')
    })
    
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })
  
  it('handles logout', async () => {
    authService.logout = jest.fn().mockResolvedValue(undefined)
    
    const { result } = renderHook(() => useAuth())
    
    // Set initial authenticated state
    act(() => {
      result.current.setUser({ id: '123', email: 'test@example.com' })
    })
    
    await act(async () => {
      await result.current.logout()
    })
    
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(authService.logout).toHaveBeenCalled()
  })
})
```

### Backend Unit Tests

#### Service Testing

```python
# test_user_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from app.models.user import User
from app.schemas.user import UserCreate

@pytest.fixture
def mock_db():
    """Create mock database session"""
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def user_service(mock_db):
    """Create user service instance"""
    return UserService(db=mock_db)

class TestUserService:
    async def test_create_user_success(self, user_service, mock_db):
        """Test successful user creation"""
        # Arrange
        user_data = UserCreate(
            email="test@example.com",
            name="Test User",
            password="SecurePassword123!"
        )
        
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Act
        result = await user_service.create_user(user_data)
        
        # Assert
        assert result.email == user_data.email
        assert result.name == user_data.name
        assert result.hashed_password != user_data.password
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    async def test_get_user_by_email(self, user_service, mock_db):
        """Test retrieving user by email"""
        # Arrange
        email = "test@example.com"
        mock_user = User(id="123", email=email, name="Test User")
        
        mock_db.execute = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none = Mock(
            return_value=mock_user
        )
        
        # Act
        result = await user_service.get_user_by_email(email)
        
        # Assert
        assert result == mock_user
        assert result.email == email
    
    async def test_authenticate_user_success(self, user_service):
        """Test successful user authentication"""
        # Arrange
        email = "test@example.com"
        password = "correct_password"
        mock_user = User(
            email=email,
            hashed_password="$2b$12$..."  # Mock bcrypt hash
        )
        
        user_service.get_user_by_email = AsyncMock(return_value=mock_user)
        user_service.verify_password = Mock(return_value=True)
        
        # Act
        result = await user_service.authenticate_user(email, password)
        
        # Assert
        assert result == mock_user
        user_service.verify_password.assert_called_with(
            password, 
            mock_user.hashed_password
        )
```

#### API Endpoint Testing

```python
# test_auth_endpoints.py
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.models.user import User

@pytest.fixture
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login"""
        with patch('app.services.auth_service.authenticate_user') as mock_auth:
            mock_user = User(
                id="123",
                email="test@example.com",
                name="Test User"
            )
            mock_auth.return_value = mock_user
            
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "password123"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        with patch('app.services.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "wrong_password"
                }
            )
            
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid credentials"
    
    @pytest.mark.asyncio
    async def test_protected_route_with_token(self, client):
        """Test accessing protected route with valid token"""
        token = "valid_jwt_token"
        
        with patch('app.core.auth.decode_token') as mock_decode:
            mock_decode.return_value = {"sub": "user123"}
            
            response = await client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
```

## Integration Testing

### Frontend Integration Tests

```typescript
// BoardroomFlow.integration.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { rest } from 'msw'
import { setupServer } from 'msw/node'
import { BoardroomDashboard } from '@/pages/BoardroomDashboard'
import { TestProviders } from '@/test/utils'

// Setup MSW server
const server = setupServer(
  rest.get('/api/v1/boardrooms', (req, res, ctx) => {
    return res(
      ctx.json({
        data: [
          {
            id: '1',
            name: 'Executive Board',
            memberCount: 10,
            nextMeeting: '2024-01-20T10:00:00Z'
          }
        ]
      })
    )
  }),
  
  rest.post('/api/v1/boardrooms', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        data: {
          id: '2',
          name: req.body.name,
          memberCount: 0
        }
      })
    )
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('Boardroom Dashboard Integration', () => {
  it('loads and displays boardrooms', async () => {
    render(
      <TestProviders>
        <BoardroomDashboard />
      </TestProviders>
    )
    
    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    })
    
    // Check boardroom is displayed
    expect(screen.getByText('Executive Board')).toBeInTheDocument()
    expect(screen.getByText('10 members')).toBeInTheDocument()
  })
  
  it('creates new boardroom', async () => {
    const user = userEvent.setup()
    
    render(
      <TestProviders>
        <BoardroomDashboard />
      </TestProviders>
    )
    
    // Click create button
    await user.click(screen.getByRole('button', { name: 'Create Boardroom' }))
    
    // Fill form
    await user.type(
      screen.getByLabelText('Boardroom Name'),
      'Marketing Committee'
    )
    await user.type(
      screen.getByLabelText('Description'),
      'Marketing strategy discussions'
    )
    
    // Submit form
    await user.click(screen.getByRole('button', { name: 'Create' }))
    
    // Verify success
    await waitFor(() => {
      expect(screen.getByText('Boardroom created successfully')).toBeInTheDocument()
    })
  })
  
  it('handles error scenarios', async () => {
    // Override handler to return error
    server.use(
      rest.get('/api/v1/boardrooms', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Server error' }))
      })
    )
    
    render(
      <TestProviders>
        <BoardroomDashboard />
      </TestProviders>
    )
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load boardrooms')).toBeInTheDocument()
    })
    
    // Test retry
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Retry' }))
  })
})
```

### Backend Integration Tests

```python
# test_boardroom_flow.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import User, Boardroom
from tests.factories import UserFactory, BoardroomFactory

@pytest.mark.integration
class TestBoardroomFlow:
    @pytest.mark.asyncio
    async def test_complete_boardroom_workflow(
        self, 
        client: AsyncClient,
        db_session: AsyncSession,
        authenticated_headers: dict
    ):
        """Test complete boardroom creation and management flow"""
        # Create boardroom
        create_response = await client.post(
            "/api/v1/boardrooms",
            json={
                "name": "Engineering Board",
                "description": "Technical decisions",
                "settings": {
                    "isPublic": False,
                    "requiresApproval": True
                }
            },
            headers=authenticated_headers
        )
        
        assert create_response.status_code == 201
        boardroom_data = create_response.json()["data"]
        boardroom_id = boardroom_data["id"]
        
        # Get boardroom details
        get_response = await client.get(
            f"/api/v1/boardrooms/{boardroom_id}",
            headers=authenticated_headers
        )
        
        assert get_response.status_code == 200
        assert get_response.json()["data"]["name"] == "Engineering Board"
        
        # Update boardroom
        update_response = await client.patch(
            f"/api/v1/boardrooms/{boardroom_id}",
            json={"description": "Updated description"},
            headers=authenticated_headers
        )
        
        assert update_response.status_code == 200
        assert update_response.json()["data"]["description"] == "Updated description"
        
        # Add member
        member = await UserFactory.create(db_session)
        add_member_response = await client.post(
            f"/api/v1/boardrooms/{boardroom_id}/members",
            json={"userId": str(member.id), "role": "member"},
            headers=authenticated_headers
        )
        
        assert add_member_response.status_code == 201
        
        # List members
        members_response = await client.get(
            f"/api/v1/boardrooms/{boardroom_id}/members",
            headers=authenticated_headers
        )
        
        assert members_response.status_code == 200
        members = members_response.json()["data"]
        assert len(members) == 2  # Owner + new member
        
        # Delete boardroom
        delete_response = await client.delete(
            f"/api/v1/boardrooms/{boardroom_id}",
            headers=authenticated_headers
        )
        
        assert delete_response.status_code == 204
        
        # Verify deletion
        get_deleted_response = await client.get(
            f"/api/v1/boardrooms/{boardroom_id}",
            headers=authenticated_headers
        )
        
        assert get_deleted_response.status_code == 404
```

## End-to-End Testing

### Playwright Setup

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] }
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] }
    }
  ],
  webServer: {
    command: 'npm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI
  }
})
```

### E2E Test Examples

```typescript
// e2e/auth-flow.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test('user can sign up, login, and logout', async ({ page }) => {
    // Navigate to signup
    await page.goto('/register')
    
    // Fill signup form
    await page.fill('[name="name"]', 'Test User')
    await page.fill('[name="email"]', 'test@example.com')
    await page.fill('[name="password"]', 'SecurePassword123!')
    await page.fill('[name="confirmPassword"]', 'SecurePassword123!')
    
    // Submit form
    await page.click('button[type="submit"]')
    
    // Wait for redirect to login
    await expect(page).toHaveURL('/login')
    await expect(page.locator('.success-message')).toContainText(
      'Account created successfully'
    )
    
    // Login
    await page.fill('[name="email"]', 'test@example.com')
    await page.fill('[name="password"]', 'SecurePassword123!')
    await page.click('button[type="submit"]')
    
    // Verify dashboard
    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('h1')).toContainText('Dashboard')
    
    // Logout
    await page.click('[data-testid="user-menu"]')
    await page.click('text=Logout')
    
    // Verify redirect to home
    await expect(page).toHaveURL('/')
  })
  
  test('MFA flow works correctly', async ({ page }) => {
    // Login with MFA-enabled account
    await page.goto('/login')
    await page.fill('[name="email"]', 'mfa@example.com')
    await page.fill('[name="password"]', 'password')
    await page.click('button[type="submit"]')
    
    // Should show MFA prompt
    await expect(page.locator('h2')).toContainText('Two-Factor Authentication')
    
    // Enter MFA code
    await page.fill('[name="code"]', '123456')
    await page.click('button[type="submit"]')
    
    // Verify successful login
    await expect(page).toHaveURL('/dashboard')
  })
})

// e2e/meeting-flow.spec.ts
test.describe('Meeting Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('[name="email"]', 'user@example.com')
    await page.fill('[name="password"]', 'password')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/dashboard')
  })
  
  test('create and join meeting', async ({ page }) => {
    // Navigate to meetings
    await page.click('a[href="/meetings"]')
    
    // Create meeting
    await page.click('text=Create Meeting')
    await page.fill('[name="title"]', 'Quarterly Review')
    await page.fill('[name="description"]', 'Q4 2024 Review Meeting')
    await page.fill('[name="date"]', '2024-12-31')
    await page.fill('[name="time"]', '14:00')
    
    // Select participants
    await page.click('[data-testid="add-participants"]')
    await page.click('text=John Doe')
    await page.click('text=Jane Smith')
    await page.click('button:has-text("Add Selected")')
    
    // Submit
    await page.click('button:has-text("Create Meeting")')
    
    // Verify creation
    await expect(page.locator('.success-toast')).toContainText(
      'Meeting created successfully'
    )
    
    // Join meeting
    await page.click('text=Quarterly Review')
    await page.click('button:has-text("Join Meeting")')
    
    // Verify in meeting
    await expect(page.locator('[data-testid="meeting-status"]')).toContainText(
      'In Progress'
    )
  })
})
```

## Performance Testing

### Frontend Performance Tests

```typescript
// performance/bundle-size.test.ts
import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'

test.describe('Bundle Size', () => {
  test('main bundle is within size limit', () => {
    const buildDir = path.join(process.cwd(), '.next/static/chunks')
    const mainBundle = fs.readdirSync(buildDir).find(f => f.startsWith('main-'))
    const stats = fs.statSync(path.join(buildDir, mainBundle))
    const sizeInKB = stats.size / 1024
    
    expect(sizeInKB).toBeLessThan(250) // 250KB limit
  })
})

// performance/load-time.test.ts
test.describe('Page Load Performance', () => {
  test('homepage loads within performance budget', async ({ page }) => {
    const metrics = await page.goto('/', { waitUntil: 'networkidle' })
      .then(() => page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0]
        return {
          domContentLoaded: navigation.domContentLoadedEventEnd,
          loadComplete: navigation.loadEventEnd,
          firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime,
          firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime
        }
      }))
    
    expect(metrics.firstContentfulPaint).toBeLessThan(1500) // 1.5s FCP
    expect(metrics.domContentLoaded).toBeLessThan(3000) // 3s DOM ready
    expect(metrics.loadComplete).toBeLessThan(5000) // 5s full load
  })
  
  test('dashboard renders within performance budget', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('[name="email"]', 'perf@example.com')
    await page.fill('[name="password"]', 'password')
    await page.click('button[type="submit"]')
    
    // Measure dashboard performance
    await page.waitForURL('/dashboard')
    
    const renderTime = await page.evaluate(() => {
      return performance.now()
    })
    
    expect(renderTime).toBeLessThan(2000) // 2s to interactive
  })
})
```

### Backend Performance Tests

```python
# test_performance.py
import pytest
import asyncio
import time
from locust import HttpUser, task, between
from httpx import AsyncClient

class BoardroomUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before running tasks"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "loadtest@example.com",
            "password": "password"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def list_boardrooms(self):
        """Test listing boardrooms"""
        with self.client.get(
            "/api/v1/boardrooms",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.elapsed.total_seconds() > 0.5:
                response.failure(f"Request took {response.elapsed.total_seconds()}s")
    
    @task(2)
    def get_boardroom_details(self):
        """Test getting boardroom details"""
        boardroom_id = "test-boardroom-id"
        self.client.get(
            f"/api/v1/boardrooms/{boardroom_id}",
            headers=self.headers
        )
    
    @task(1)
    def create_meeting(self):
        """Test creating meeting"""
        self.client.post(
            "/api/v1/meetings",
            json={
                "boardroomId": "test-boardroom-id",
                "title": "Performance Test Meeting",
                "date": "2024-12-31T14:00:00Z"
            },
            headers=self.headers
        )

@pytest.mark.performance
class TestAPIPerformance:
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client: AsyncClient):
        """Test handling concurrent requests"""
        async def make_request():
            start = time.time()
            response = await client.get("/api/v1/health")
            return time.time() - start, response.status_code
        
        # Make 100 concurrent requests
        tasks = [make_request() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        response_times = [r[0] for r in results]
        status_codes = [r[1] for r in results]
        
        # All requests should succeed
        assert all(code == 200 for code in status_codes)
        
        # 95th percentile should be under 200ms
        sorted_times = sorted(response_times)
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        assert p95 < 0.2
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self, db_session):
        """Test database query performance"""
        from app.models import Boardroom
        
        # Create test data
        boardrooms = [
            Boardroom(name=f"Boardroom {i}", description=f"Test {i}")
            for i in range(1000)
        ]
        db_session.add_all(boardrooms)
        await db_session.commit()
        
        # Test query performance
        start = time.time()
        result = await db_session.execute(
            select(Boardroom)
            .options(selectinload(Boardroom.members))
            .limit(100)
        )
        boardrooms = result.scalars().all()
        query_time = time.time() - start
        
        assert len(boardrooms) == 100
        assert query_time < 0.1  # Should complete in under 100ms
```

## Security Testing

### Security Test Suite

```python
# test_security.py
import pytest
from httpx import AsyncClient
import jwt
from datetime import datetime, timedelta

@pytest.mark.security
class TestSecurity:
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, client: AsyncClient):
        """Test SQL injection prevention"""
        # Try SQL injection in search parameter
        malicious_input = "'; DROP TABLE users; --"
        response = await client.get(
            f"/api/v1/boardrooms?search={malicious_input}"
        )
        
        # Should handle safely
        assert response.status_code in [200, 400]
        # Database should still be intact
        health_response = await client.get("/api/v1/health")
        assert health_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_xss_prevention(self, client: AsyncClient, auth_headers):
        """Test XSS prevention"""
        # Try to inject script
        malicious_name = "<script>alert('XSS')</script>"
        response = await client.post(
            "/api/v1/boardrooms",
            json={"name": malicious_name, "description": "Test"},
            headers=auth_headers
        )
        
        if response.status_code == 201:
            boardroom_id = response.json()["data"]["id"]
            get_response = await client.get(
                f"/api/v1/boardrooms/{boardroom_id}",
                headers=auth_headers
            )
            
            # Should be escaped
            returned_name = get_response.json()["data"]["name"]
            assert "<script>" not in returned_name
            assert returned_name == "&lt;script&gt;alert('XSS')&lt;/script&gt;"
    
    @pytest.mark.asyncio
    async def test_authentication_required(self, client: AsyncClient):
        """Test endpoints require authentication"""
        protected_endpoints = [
            "/api/v1/users/me",
            "/api/v1/boardrooms",
            "/api/v1/meetings"
        ]
        
        for endpoint in protected_endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_jwt_expiration(self, client: AsyncClient):
        """Test JWT token expiration"""
        # Create expired token
        expired_token = jwt.encode(
            {
                "sub": "user123",
                "exp": datetime.utcnow() - timedelta(hours=1)
            },
            "secret",
            algorithm="HS256"
        )
        
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client: AsyncClient):
        """Test rate limiting protection"""
        # Make many requests quickly
        responses = []
        for _ in range(10):
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrong"}
            )
            responses.append(response)
        
        # Should hit rate limit
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes  # Too Many Requests
```

### Frontend Security Tests

```typescript
// security.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PasswordInput } from '@/components/PasswordInput'
import { sanitizeHtml } from '@/utils/security'

describe('Security Features', () => {
  describe('Password Strength', () => {
    it('validates password strength correctly', async () => {
      const user = userEvent.setup()
      const onPasswordChange = jest.fn()
      
      render(
        <PasswordInput 
          onChange={onPasswordChange}
          showStrength={true}
        />
      )
      
      // Weak password
      await user.type(screen.getByLabelText('Password'), 'weak')
      expect(screen.getByText('Weak')).toBeInTheDocument()
      expect(screen.getByRole('progressbar')).toHaveAttribute(
        'aria-valuenow',
        '25'
      )
      
      // Strong password
      await user.clear(screen.getByLabelText('Password'))
      await user.type(
        screen.getByLabelText('Password'),
        'StrongP@ssw0rd123!'
      )
      expect(screen.getByText('Strong')).toBeInTheDocument()
      expect(screen.getByRole('progressbar')).toHaveAttribute(
        'aria-valuenow',
        '100'
      )
    })
  })
  
  describe('XSS Prevention', () => {
    it('sanitizes user input', () => {
      const maliciousInput = '<script>alert("XSS")</script><p>Hello</p>'
      const sanitized = sanitizeHtml(maliciousInput)
      
      expect(sanitized).not.toContain('<script>')
      expect(sanitized).toContain('<p>Hello</p>')
    })
    
    it('prevents dangerous attributes', () => {
      const maliciousInput = '<img src="x" onerror="alert(\'XSS\')">'
      const sanitized = sanitizeHtml(maliciousInput)
      
      expect(sanitized).not.toContain('onerror')
    })
  })
  
  describe('CSRF Protection', () => {
    it('includes CSRF token in requests', async () => {
      const mockFetch = jest.fn()
      global.fetch = mockFetch
      
      // Make authenticated request
      await apiClient.post('/api/v1/boardrooms', { name: 'Test' })
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-CSRF-Token': expect.any(String)
          })
        })
      )
    })
  })
})
```

## Test Data Management

### Test Factories

```python
# tests/factories.py
import factory
from factory import Faker, SubFactory, LazyAttribute
from factory.alchemy import SQLAlchemyModelFactory
from datetime import datetime, timedelta

from app.models import User, Boardroom, Meeting

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: f"user_{n}")
    email = Faker("email")
    name = Faker("name")
    hashed_password = "$2b$12$default_hash"
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)
    
    @classmethod
    def create_batch_with_boardrooms(cls, size, **kwargs):
        """Create users with associated boardrooms"""
        users = []
        for _ in range(size):
            user = cls.create(**kwargs)
            BoardroomFactory.create_batch(
                3, 
                owner=user,
                members=[user]
            )
            users.append(user)
        return users

class BoardroomFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Boardroom
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: f"boardroom_{n}")
    name = Faker("company")
    description = Faker("text", max_nb_chars=200)
    owner = SubFactory(UserFactory)
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)

class MeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Meeting
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: f"meeting_{n}")
    title = Faker("catch_phrase")
    description = Faker("text", max_nb_chars=500)
    boardroom = SubFactory(BoardroomFactory)
    scheduled_at = LazyAttribute(
        lambda obj: datetime.utcnow() + timedelta(days=7)
    )
    duration_minutes = 60
    status = "scheduled"
```

### Frontend Test Data

```typescript
// test/fixtures/testData.ts
import { User, Boardroom, Meeting } from '@/types'

export const createMockUser = (overrides?: Partial<User>): User => ({
  id: 'user_1',
  email: 'test@example.com',
  name: 'Test User',
  avatar: 'https://example.com/avatar.jpg',
  role: 'member',
  createdAt: new Date().toISOString(),
  ...overrides
})

export const createMockBoardroom = (overrides?: Partial<Boardroom>): Boardroom => ({
  id: 'boardroom_1',
  name: 'Executive Board',
  description: 'Main decision-making body',
  memberCount: 10,
  owner: createMockUser(),
  isActive: true,
  createdAt: new Date().toISOString(),
  ...overrides
})

export const createMockMeeting = (overrides?: Partial<Meeting>): Meeting => ({
  id: 'meeting_1',
  title: 'Quarterly Review',
  description: 'Q4 2024 performance review',
  boardroom: createMockBoardroom(),
  scheduledAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  duration: 60,
  status: 'scheduled',
  participants: [createMockUser()],
  ...overrides
})

// Bulk data generators
export const generateMockUsers = (count: number): User[] => {
  return Array.from({ length: count }, (_, i) => 
    createMockUser({
      id: `user_${i}`,
      email: `user${i}@example.com`,
      name: `User ${i}`
    })
  )
}
```

## Continuous Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  frontend-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18.x, 20.x]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Run linting
        working-directory: ./frontend
        run: npm run lint
      
      - name: Run type checking
        working-directory: ./frontend
        run: npm run type-check
      
      - name: Run unit tests
        working-directory: ./frontend
        run: npm run test:unit -- --coverage
      
      - name: Run integration tests
        working-directory: ./frontend
        run: npm run test:integration
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./frontend/coverage/coverage-final.json
          flags: frontend
  
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: boardroom_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run linting
        run: |
          black --check .
          flake8 .
          mypy app
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/boardroom_test
          REDIS_URL: redis://localhost:6379
        run: |
          pytest --cov=app --cov-report=xml --cov-report=html
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: backend
  
  e2e-tests:
    runs-on: ubuntu-latest
    needs: [frontend-tests, backend-tests]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: docker-compose -f docker-compose.test.yml up -d
      
      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:3000; do sleep 1; done'
          timeout 60 bash -c 'until curl -f http://localhost:8000/api/v1/health; do sleep 1; done'
      
      - name: Run E2E tests
        working-directory: ./frontend
        run: npm run test:e2e
      
      - name: Upload test artifacts
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-test-results
          path: |
            frontend/test-results/
            frontend/playwright-report/
```

## Test Reporting

### Coverage Reports

```bash
# Generate coverage reports
npm run test:coverage
pytest --cov=app --cov-report=html

# View reports
open coverage/index.html           # Frontend
open htmlcov/index.html           # Backend
```

### Test Results Dashboard

```typescript
// test-reporter.ts
import { Reporter } from '@playwright/test/reporter'

class CustomReporter implements Reporter {
  onBegin(config, suite) {
    console.log(`Starting test run with ${suite.allTests().length} tests`)
  }
  
  onTestEnd(test, result) {
    const status = result.status
    const duration = result.duration
    
    // Send to monitoring system
    fetch('https://monitoring.boardroom.com/api/test-results', {
      method: 'POST',
      body: JSON.stringify({
        test: test.title,
        status,
        duration,
        timestamp: new Date().toISOString()
      })
    })
  }
  
  onEnd(result) {
    console.log(`Finished with status: ${result.status}`)
    
    // Generate summary
    const summary = {
      total: result.stats.total,
      passed: result.stats.expected,
      failed: result.stats.unexpected,
      skipped: result.stats.skipped,
      duration: result.duration
    }
    
    // Save summary
    fs.writeFileSync('test-summary.json', JSON.stringify(summary, null, 2))
  }
}

export default CustomReporter
```

---

Following these testing procedures ensures high-quality, reliable software delivery. Remember: good tests are as important as good code!