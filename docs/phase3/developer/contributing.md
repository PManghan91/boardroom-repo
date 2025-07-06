# Contributing Guidelines

## Welcome Contributors!

Thank you for your interest in contributing to the Boardroom platform. This guide will help you get started with contributing to our Phase 3 codebase, which includes advanced features like real-time collaboration, enhanced security, and performance optimizations.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Development Workflow](#development-workflow)
5. [Code Standards](#code-standards)
6. [Testing Requirements](#testing-requirements)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Review Process](#review-process)
10. [Release Process](#release-process)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. We pledge to:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Expected Behavior

- Demonstrate respect and empathy in all interactions
- Provide constructive feedback
- Accept responsibility for mistakes
- Focus on resolution rather than blame
- Help maintain a positive environment

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Technical Requirements**
   - Node.js 18.x or 20.x LTS
   - Python 3.11+
   - Docker 20.10+
   - Git 2.30+
   - Your favorite code editor (we recommend VS Code)

2. **Knowledge Requirements**
   - TypeScript/JavaScript for frontend
   - Python for backend
   - React and Next.js basics
   - FastAPI fundamentals
   - Git workflow understanding

### First-Time Contributors

1. **Find an Issue**
   ```bash
   # Look for good first issues
   # Labels: "good first issue", "help wanted", "beginner friendly"
   ```

2. **Comment on the Issue**
   - Express your interest
   - Ask clarifying questions
   - Propose your approach

3. **Get Assigned**
   - Wait for maintainer assignment
   - Start working once assigned

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/boardroom.git
cd boardroom

# Add upstream remote
git remote add upstream https://github.com/boardroom/boardroom.git

# Verify remotes
git remote -v
```

### 2. Environment Setup

```bash
# Copy environment files
cp .env.example .env.development

# Frontend setup
cd frontend
npm install
npm run dev

# Backend setup (in another terminal)
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Database Setup

```bash
# Start PostgreSQL and Redis
docker-compose -f docker-compose.dev.yml up -d db redis

# Run migrations
alembic upgrade head

# Seed development data (optional)
python scripts/seed_dev_data.py
```

### 4. Verify Setup

```bash
# Run tests to verify setup
npm test
pytest

# Check services
curl http://localhost:3000  # Frontend
curl http://localhost:8000/api/v1/health  # Backend
```

## Development Workflow

### 1. Branch Strategy

```bash
# Always branch from main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# OR
git checkout -b fix/issue-description
# OR
git checkout -b docs/documentation-update
```

**Branch Naming Convention:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates
- `perf/` - Performance improvements

### 2. Making Changes

```bash
# Make your changes
# ... edit files ...

# Stage changes
git add .

# Commit with conventional commits
git commit -m "feat: add real-time notification system"
# OR
git commit -m "fix: resolve WebSocket connection timeout"
# OR
git commit -m "docs: update API documentation"
```

**Commit Message Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions/changes
- `chore`: Maintenance tasks

### 3. Keeping Up to Date

```bash
# Regularly sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Rebase your feature branch
git checkout feature/your-feature
git rebase main
```

## Code Standards

### TypeScript/JavaScript (Frontend)

```typescript
// Use explicit types
interface User {
  id: string
  name: string
  email: string
  roles: Role[]
}

// Use functional components with proper typing
const UserCard: React.FC<{ user: User }> = ({ user }) => {
  // Use hooks at the top
  const [isLoading, setIsLoading] = useState(false)
  const { t } = useTranslation()
  
  // Use early returns for guard clauses
  if (!user) return null
  
  // Use async/await over promises
  const handleUpdate = async () => {
    setIsLoading(true)
    try {
      await updateUser(user.id)
    } catch (error) {
      console.error('Failed to update user:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>{user.name}</CardTitle>
      </CardHeader>
      {/* Component content */}
    </Card>
  )
}

// Export components properly
export default UserCard
```

### Python (Backend)

```python
# Use type hints
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel

class UserResponse(BaseModel):
    """User response model with proper documentation"""
    id: str
    name: str
    email: str
    created_at: datetime
    roles: List[str]
    
    class Config:
        orm_mode = True

# Use async/await for I/O operations
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Retrieve user by ID.
    
    Args:
        user_id: The user's unique identifier
        db: Database session
        
    Returns:
        User object if found, None otherwise
        
    Raises:
        HTTPException: If user not found
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    return user

# Use dependency injection
@router.get("/users/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Get user details endpoint"""
    # Check permissions
    if not current_user.can_read_user(user_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    user = await get_user(user_id, db)
    return UserResponse.from_orm(user)
```

### CSS/Styling

```scss
// Use CSS modules or styled-components
// Prefer Tailwind CSS classes for consistency

// Component-specific styles
.user-card {
  @apply bg-white dark:bg-gray-800 rounded-lg shadow-md p-4;
  
  &__header {
    @apply flex justify-between items-center mb-4;
  }
  
  &__title {
    @apply text-lg font-semibold text-gray-900 dark:text-white;
  }
  
  // Use CSS variables for theming
  --card-bg: theme('colors.white');
  --card-border: theme('colors.gray.200');
  
  @media (prefers-color-scheme: dark) {
    --card-bg: theme('colors.gray.800');
    --card-border: theme('colors.gray.700');
  }
}
```

## Testing Requirements

### Frontend Testing

```typescript
// UserCard.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UserCard } from './UserCard'

describe('UserCard', () => {
  const mockUser = {
    id: '123',
    name: 'John Doe',
    email: 'john@example.com',
    roles: ['user']
  }
  
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks()
  })
  
  it('renders user information correctly', () => {
    render(<UserCard user={mockUser} />)
    
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('john@example.com')).toBeInTheDocument()
  })
  
  it('handles update action', async () => {
    const onUpdate = jest.fn()
    render(<UserCard user={mockUser} onUpdate={onUpdate} />)
    
    const updateButton = screen.getByRole('button', { name: /update/i })
    await userEvent.click(updateButton)
    
    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith(mockUser.id)
    })
  })
  
  it('handles error states gracefully', () => {
    render(<UserCard user={null} />)
    expect(screen.queryByText('John Doe')).not.toBeInTheDocument()
  })
})
```

### Backend Testing

```python
# test_user_endpoints.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.tests.factories import UserFactory

@pytest.mark.asyncio
async def test_get_user(
    client: AsyncClient,
    db_session: AsyncSession,
    authenticated_user: User
):
    """Test retrieving user details"""
    # Create test user
    user = await UserFactory.create()
    await db_session.commit()
    
    # Make request
    response = await client.get(
        f"/api/v1/users/{user.id}",
        headers={"Authorization": f"Bearer {authenticated_user.token}"}
    )
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["name"] == user.name
    assert data["email"] == user.email

@pytest.mark.asyncio
async def test_get_user_not_found(
    client: AsyncClient,
    authenticated_user: User
):
    """Test retrieving non-existent user"""
    response = await client.get(
        "/api/v1/users/non-existent-id",
        headers={"Authorization": f"Bearer {authenticated_user.token}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_user_unauthorized(client: AsyncClient):
    """Test accessing user without authentication"""
    response = await client.get("/api/v1/users/some-id")
    assert response.status_code == 401
```

### Test Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Critical Paths**: 90%+ coverage
- **New Features**: 85%+ coverage
- **Bug Fixes**: Include regression tests

## Documentation

### Code Documentation

```typescript
/**
 * UserCard component displays user information in a card format
 * 
 * @component
 * @example
 * ```tsx
 * <UserCard 
 *   user={userData} 
 *   onUpdate={handleUpdate}
 *   showActions={true}
 * />
 * ```
 */
interface UserCardProps {
  /** User data to display */
  user: User
  /** Callback when user is updated */
  onUpdate?: (userId: string) => void
  /** Whether to show action buttons */
  showActions?: boolean
}
```

### API Documentation

```python
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    summary="Create a new user",
    description="Creates a new user account with the provided information",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid user data"},
        409: {"description": "User already exists"}
    }
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> UserResponse:
    """
    Create a new user account.
    
    Required permissions: admin
    
    - **name**: User's full name
    - **email**: Valid email address (must be unique)
    - **password**: Strong password (min 12 characters)
    - **roles**: List of role IDs to assign
    """
    # Implementation
```

### README Updates

When adding new features, update relevant README files:

```markdown
## New Feature: Real-time Notifications

### Overview
Real-time notifications keep users informed of important events...

### Usage
```typescript
import { useNotifications } from '@/hooks/useNotifications'

const MyComponent = () => {
  const { notifications, markAsRead } = useNotifications()
  // ...
}
```

### Configuration
- `NEXT_PUBLIC_ENABLE_NOTIFICATIONS`: Enable/disable notifications
- `NOTIFICATION_POLLING_INTERVAL`: Polling interval in ms

### API Endpoints
- `GET /api/v1/notifications` - Get user notifications
- `PUT /api/v1/notifications/:id/read` - Mark as read
```

## Pull Request Process

### 1. Before Creating PR

```bash
# Run all tests
npm test
pytest

# Check code quality
npm run lint
npm run type-check
black .
mypy .

# Update documentation
# ... update relevant docs ...

# Commit all changes
git add .
git commit -m "feat: complete feature implementation"
```

### 2. Create Pull Request

**PR Title Format:**
```
feat(scope): Brief description
fix(api): Resolve timeout issue in WebSocket connections
docs(readme): Update installation instructions
```

**PR Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added/updated
- [ ] All tests passing

## Screenshots (if applicable)
[Add screenshots for UI changes]

## Related Issues
Fixes #123
```

### 3. After Creating PR

1. **Wait for CI/CD**
   - All tests must pass
   - Code coverage maintained
   - No security vulnerabilities

2. **Address Review Comments**
   - Respond to all comments
   - Make requested changes
   - Re-request review when ready

3. **Keep PR Updated**
   ```bash
   git fetch upstream
   git rebase upstream/main
   git push --force-with-lease origin feature/your-feature
   ```

## Review Process

### For Reviewers

1. **Code Review Checklist**
   - [ ] Code follows project standards
   - [ ] Tests are adequate
   - [ ] Documentation is updated
   - [ ] No security vulnerabilities
   - [ ] Performance implications considered
   - [ ] Breaking changes documented

2. **Review Comments**
   ```typescript
   // Use constructive feedback
   // ❌ Bad: "This is wrong"
   // ✅ Good: "Consider using useMemo here to prevent unnecessary re-renders"
   
   // Provide examples
   // ✅ "You could simplify this with: const result = data?.user?.name ?? 'Unknown'"
   ```

3. **Approval Process**
   - Approve: All requirements met
   - Request Changes: Significant issues found
   - Comment: Minor suggestions, not blocking

### For Contributors

1. **Responding to Reviews**
   - Address all comments
   - Ask for clarification if needed
   - Mark conversations as resolved
   - Thank reviewers for their time

2. **Making Changes**
   ```bash
   # Make requested changes
   git add .
   git commit -m "address review comments"
   
   # Or amend if preferred
   git commit --amend
   git push --force-with-lease
   ```

## Release Process

### Version Management

We follow Semantic Versioning (SemVer):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

1. **Pre-release**
   - [ ] All PRs merged
   - [ ] Tests passing
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated
   - [ ] Version bumped

2. **Release**
   ```bash
   # Tag release
   git tag -a v3.1.0 -m "Release version 3.1.0"
   git push upstream v3.1.0
   
   # Create GitHub release
   # Include changelog and migration notes
   ```

3. **Post-release**
   - [ ] Deploy to staging
   - [ ] Run smoke tests
   - [ ] Deploy to production
   - [ ] Monitor for issues
   - [ ] Announce release

## Getting Help

### Resources

1. **Documentation**
   - [API Documentation](../api/)
   - [Architecture Guide](../features/)
   - [Testing Guide](./testing-procedures.md)

2. **Communication**
   - GitHub Issues: Bug reports and features
   - Discussions: Questions and ideas
   - Discord: Real-time chat (coming soon)

3. **Office Hours**
   - Weekly contributor calls
   - Pair programming sessions
   - Code review workshops

### Maintainers

| Name | Role | GitHub | Timezone |
|------|------|--------|----------|
| John Doe | Lead Maintainer | @johndoe | PST |
| Jane Smith | Frontend Lead | @janesmith | EST |
| Bob Johnson | Backend Lead | @bobjohnson | GMT |

---

Thank you for contributing to Boardroom! Your efforts help make our platform better for everyone. 🚀