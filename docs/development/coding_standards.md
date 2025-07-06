# Coding Standards

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: Developers  
**Next Review**: As needed  

## Overview

This document defines the coding standards for the Boardroom AI project. Following these standards ensures code consistency, maintainability, and quality across both backend (Python/FastAPI) and frontend (TypeScript/Next.js) codebases.

## Python Code Standards (Backend)

### Code Style

**Formatting:**
- Use Black formatter with line length of 119 characters
- Use isort with Black profile for import sorting
- 4-space indentation (no tabs)
- No trailing whitespace
- No semicolons at line ends

**Configuration** (`pyproject.toml`):
```toml
[tool.black]
line-length = 119

[tool.isort]
profile = "black"
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
line_length = 119
```

### Import Organization

Order imports as follows:
1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

# Local application
from app.core.config import settings
from app.core.logging import logger
```

### Naming Conventions

- **Files**: snake_case (e.g., `user_service.py`)
- **Classes**: PascalCase (e.g., `UserService`)
- **Functions/Variables**: snake_case (e.g., `get_user_by_id`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_ATTEMPTS`)
- **Private methods**: Leading underscore (e.g., `_validate_input`)

### Type Hints

Always use type hints for function parameters and return values:

```python
def create_user(
    user_data: UserCreate,
    db: Session,
    send_email: bool = True
) -> User:
    """Create a new user in the database."""
    # Implementation
```

### Docstrings

Use Google-style docstrings for all modules, classes, and functions:

```python
"""Module for user authentication and management.

This module provides functionality for user registration,
authentication, and profile management.
"""

class UserService:
    """Service for managing user operations.
    
    Attributes:
        db: Database session
        cache: Redis cache client
    """
    
    def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticate a user by email and password.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
            
        Raises:
            DatabaseError: If database connection fails
        """
```

### Error Handling

Use structured exception handling with proper logging:

```python
try:
    result = await perform_operation()
except ValidationError as e:
    logger.warning(
        "validation_failed",
        error=str(e),
        field=e.field_name
    )
    raise HTTPException(
        status_code=422,
        detail={"field": e.field_name, "message": str(e)}
    )
except Exception as e:
    logger.error(
        "operation_failed",
        error=str(e),
        exc_info=True
    )
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

### Async Best Practices

- Use `async/await` for all I/O operations
- Properly close resources with async context managers
- Avoid blocking operations in async functions

```python
async def get_user_data(user_id: str) -> Dict[str, Any]:
    async with get_db_session() as db:
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(404, "User not found")
        return user.dict()
```

## TypeScript/JavaScript Standards (Frontend)

### Code Style

**Formatting:**
- No semicolons
- Double quotes for strings
- 2-space indentation
- 80-character line width
- Arrow functions with parentheses

**Configuration** (`.prettierrc`):
```json
{
  "singleQuote": false,
  "semi": false,
  "tabWidth": 2,
  "printWidth": 80,
  "arrowParens": "always"
}
```

### Import Organization

Use the import sorter plugin with this order:
1. React imports
2. Next.js imports
3. Third-party libraries
4. Local imports (types, configs, components, etc.)

```typescript
import React, { useState, useEffect } from "react"
import { useRouter } from "next/navigation"

import { Button } from "@radix-ui/react-button"
import { z } from "zod"

import type { User } from "@/types/auth"
import { apiClient } from "@/lib/api"
import { UserCard } from "@/components/user"
```

### Naming Conventions

- **Files**: camelCase for non-components (e.g., `apiHelper.ts`)
- **Components**: PascalCase (e.g., `UserProfile.tsx`)
- **Functions/Variables**: camelCase (e.g., `getUserData`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `API_BASE_URL`)
- **Types/Interfaces**: PascalCase (e.g., `UserResponse`)

### TypeScript Usage

Always use strict type checking:

```typescript
// Define interfaces for all data structures
interface UserData {
  id: string
  email: string
  fullName: string
  isActive: boolean
}

// Use type imports
import type { NextPage } from "next"

// Generic types for reusable components
interface ButtonProps<T = HTMLButtonElement> {
  onClick: (event: React.MouseEvent<T>) => void
  children: React.ReactNode
  variant?: "primary" | "secondary"
}
```

### Component Structure

Follow this consistent structure for React components:

```typescript
// 1. Imports
import React, { useState } from "react"

// 2. Type definitions
interface UserCardProps {
  user: User
  onEdit?: (user: User) => void
}

// 3. Component definition
export function UserCard({ user, onEdit }: UserCardProps) {
  // 4. State and hooks
  const [isEditing, setIsEditing] = useState(false)
  
  // 5. Event handlers
  const handleEdit = () => {
    setIsEditing(true)
    onEdit?.(user)
  }
  
  // 6. Render
  return (
    <div className="user-card">
      {/* Component JSX */}
    </div>
  )
}
```

### Error Handling

Implement proper error handling in API calls:

```typescript
try {
  const response = await apiClient.get<UserData>("/users/me")
  return response.data
} catch (error) {
  console.error("Failed to fetch user data:", error)
  
  if (error instanceof ApiError) {
    throw new Error(error.message)
  }
  
  throw new Error("An unexpected error occurred")
}
```

## Common Standards (Both Frontend & Backend)

### Git Commit Messages

Follow conventional commits format:
```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build/tooling changes

Examples:
```
feat(auth): add password reset functionality
fix(api): handle null values in user response
docs(readme): update installation instructions
```

### Code Comments

- Write self-documenting code that needs minimal comments
- Use comments to explain "why" not "what"
- Keep comments up-to-date with code changes
- Remove commented-out code before committing

```python
# Good: Explains why
# We need to retry 3 times because the external API
# occasionally returns transient errors
for attempt in range(3):
    try:
        result = await external_api.call()
        break
    except TransientError:
        if attempt == 2:
            raise

# Bad: Explains what (obvious from code)
# Loop 3 times
for i in range(3):
    # Call the API
    result = api.call()
```

### Security Standards

1. **Never commit secrets**: Use environment variables
2. **Sanitize inputs**: Validate and sanitize all user inputs
3. **Use parameterized queries**: Prevent SQL injection
4. **Implement rate limiting**: Protect against abuse
5. **Log security events**: Track authentication failures

### Performance Guidelines

1. **Use caching**: Cache expensive operations
2. **Optimize queries**: Use select with specific columns
3. **Async operations**: Don't block the event loop
4. **Lazy loading**: Load data only when needed
5. **Monitor performance**: Track response times

## Code Review Checklist

Before submitting code for review:

- [ ] Code follows formatting standards (run Black/Prettier)
- [ ] All functions have type hints/annotations
- [ ] Complex logic has appropriate comments
- [ ] Error handling is comprehensive
- [ ] Security considerations addressed
- [ ] Tests written for new functionality
- [ ] No hardcoded values or secrets
- [ ] Performance impact considered
- [ ] Documentation updated if needed

## Enforcement

### Automated Tools

1. **Pre-commit hooks**: Run formatters and linters
2. **CI/CD checks**: Validate code style in pipeline
3. **IDE configuration**: Share workspace settings

### Manual Review

1. Code reviews required for all changes
2. Focus on logic, security, and maintainability
3. Suggest improvements constructively
4. Share knowledge and best practices

## Exceptions

Deviations from these standards may be acceptable when:
1. Working with third-party code
2. Performance critical sections
3. Maintaining backwards compatibility

Document any exceptions with clear comments explaining the rationale.

## Related Documentation

- [Development Setup](./setup.md)
- [Testing Approach](./testing.md)
- [API Design Patterns](../architecture/api_design.md)
- [System Architecture](../architecture/system_overview.md)

---

**Questions?** Discuss in code reviews or update these standards through a pull request.