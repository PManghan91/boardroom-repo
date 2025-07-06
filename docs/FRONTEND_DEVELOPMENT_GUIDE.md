# Frontend Development Guide

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Purpose**: Step-by-step guide for completing the Next.js frontend  
**Target**: New Claude Code instance for systematic frontend fixes  

## Overview

This guide provides a structured approach to completing the Boardroom AI frontend. The frontend has a solid foundation with beautiful UI components but needs backend integration and missing features implemented.

## Current State Summary

### ✅ What's Working
- Complete UI component library (shadcn/ui)
- Dark mode support
- Internationalization (en/tr)
- TypeScript throughout
- Mock data implementations
- Error boundaries and loading states

### ❌ What's Broken
- No real backend API connections (all mock data)
- Auth system not fully integrated
- Missing route pages (/dashboard, /meetings, /ai, /profile)
- Auth redirect to non-existent dashboard

### 🚧 What's Incomplete
- Backend API integration
- WebSocket/realtime features
- File upload functionality
- Voice input implementation
- Token refresh mechanism

## Development Priority Order

Follow this order for maximum efficiency and minimal rework:

### Phase 1: Foundation (Days 1-2)
Fix core infrastructure before adding features.

1. **Backend Connection**
2. **Authentication Flow**
3. **Protected Routes**
4. **Error Handling**

### Phase 2: Core Pages (Days 3-4)
Create missing pages with basic functionality.

1. **Dashboard Page**
2. **Fix Navigation**
3. **Profile Page**
4. **404 Page**

### Phase 3: API Integration (Days 5-7)
Connect all components to real backend.

1. **Chat Integration**
2. **Session Management**
3. **Data Persistence**
4. **Loading States**

### Phase 4: Features (Days 8-10)
Add remaining functionality.

1. **Meetings Page**
2. **AI Features Page**
3. **Real-time Updates**
4. **File Uploads**

### Phase 5: Polish (Days 11-12)
Final touches and optimization.

1. **Performance**
2. **Accessibility**
3. **Mobile Experience**
4. **Testing**

## Detailed Implementation Guide

### Phase 1: Foundation

#### 1.1 Backend Connection Setup

**Location**: `frontend/.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME="Boardroom AI"
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

**Tasks**:
```markdown
- [ ] Verify backend is running on port 8000
- [ ] Test API health endpoint: GET http://localhost:8000/health
- [ ] Update axios base URL in api-helper
- [ ] Add request/response logging for debugging
```

**Code to modify**: `src/helpers/api-helper/axios-instance.ts`
```typescript
// Add request logging
axiosInstance.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url);
    return config;
  }
);

// Add response logging
axiosInstance.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  }
);
```

#### 1.2 Fix Authentication Flow

**Priority Issues**:
1. Auth service and auth store are disconnected
2. Token refresh throws "not implemented" error
3. Redirect goes to non-existent /dashboard

**Location**: `src/services/auth.service.ts`

**Tasks**:
```markdown
- [ ] Connect auth service to auth store
- [ ] Implement token refresh
- [ ] Fix redirect to go to home page
- [ ] Add server-side session check
- [ ] Test login/logout flow
```

**Key changes needed**:
```typescript
// In auth.service.ts
import { useAuthStore } from '@/stores/auth.store';

// Update login method
async login(credentials: LoginCredentials): Promise<LoginResponse> {
  const response = await apiClient.post('/auth/login', credentials);
  const { user, token } = response.data;
  
  // Update auth store
  useAuthStore.getState().setAuth(user, token.access_token);
  
  // Redirect to home instead of dashboard
  router.push('/');
  
  return response.data;
}

// Implement refresh
async refreshToken(): Promise<void> {
  try {
    const refreshToken = this.getRefreshToken();
    const response = await apiClient.post('/auth/refresh', {
      refresh_token: refreshToken
    });
    this.setTokens(response.data);
  } catch (error) {
    this.logout();
    throw error;
  }
}
```

#### 1.3 Protected Routes Middleware

**Create**: `src/middleware.ts`
```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token');
  const isAuthPage = request.nextUrl.pathname.startsWith('/login');
  
  if (!token && !isAuthPage) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/meetings/:path*', '/profile/:path*']
};
```

### Phase 2: Core Pages

#### 2.1 Create Dashboard Page

**Create**: `src/app/[locale]/dashboard/page.tsx`
```typescript
import { Metadata } from "next"
import { StatsOverview } from "@/widgets/StatsOverview"
import { RecentActivity } from "@/components/dashboard/RecentActivity"
import { QuickActions } from "@/components/dashboard/QuickActions"

export const metadata: Metadata = {
  title: "Dashboard | Boardroom AI",
  description: "Your meeting and decision hub",
}

export default function DashboardPage() {
  return (
    <div className="container mx-auto py-6 space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>
      
      <StatsOverview />
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentActivity />
        </div>
        <div>
          <QuickActions />
        </div>
      </div>
    </div>
  )
}
```

**Tasks**:
```markdown
- [ ] Create dashboard page structure
- [ ] Add stats overview widget
- [ ] Create recent activity component
- [ ] Add quick actions panel
- [ ] Connect to real data
```

#### 2.2 Fix Navigation

**Location**: `src/components/shared/Header.tsx`

**Current Issues**:
- Links go to non-existent pages
- No active state indication
- Missing mobile menu

**Tasks**:
```markdown
- [ ] Update navigation links to valid routes
- [ ] Add active state highlighting
- [ ] Implement mobile responsive menu
- [ ] Add user menu dropdown
- [ ] Show/hide based on auth state
```

### Phase 3: API Integration

#### 3.1 Chat Integration

**Location**: `src/components/ai/ChatInterface.tsx`

**Current State**: Uses mock responses
**Goal**: Connect to real backend

**Tasks**:
```markdown
- [ ] Replace mock chat with real API call
- [ ] Implement streaming responses
- [ ] Add error handling
- [ ] Show typing indicators
- [ ] Persist chat history
```

**Implementation**:
```typescript
// In ChatInterface.tsx
const sendMessage = async (message: string) => {
  setIsLoading(true);
  
  try {
    // For streaming
    const response = await fetch('/api/v1/chatbot/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ message, session_id: sessionId })
    });
    
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      // Process streaming chunk
      appendToResponse(chunk);
    }
  } catch (error) {
    toast.error('Failed to send message');
  } finally {
    setIsLoading(false);
  }
};
```

### Phase 4: Features

#### 4.1 Meetings Page

**Create**: `src/app/[locale]/meetings/page.tsx`

**Features needed**:
```markdown
- [ ] Meeting list/calendar view
- [ ] Create meeting form
- [ ] Meeting details modal
- [ ] Participant management
- [ ] Integration with chat
```

#### 4.2 Real-time Updates

**Implement WebSocket connection**:
```typescript
// src/hooks/useWebSocket.ts
export function useWebSocket(url: string) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  
  useEffect(() => {
    const ws = new WebSocket(url);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setSocket(ws);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleRealtimeUpdate(data);
    };
    
    return () => ws.close();
  }, [url]);
  
  return socket;
}
```

### Phase 5: Polish

#### 5.1 Performance Optimization

**Tasks**:
```markdown
- [ ] Implement lazy loading for routes
- [ ] Optimize images with next/image
- [ ] Add service worker for offline
- [ ] Implement virtual scrolling for lists
- [ ] Minimize bundle size
```

#### 5.2 Accessibility

**Checklist**:
```markdown
- [ ] ARIA labels on interactive elements
- [ ] Keyboard navigation support
- [ ] Focus management in modals
- [ ] Color contrast compliance
- [ ] Screen reader testing
```

## Common Issues and Solutions

### Issue: "Cannot connect to backend"
**Solution**: 
1. Verify backend is running: `docker-compose ps`
2. Check CORS settings in backend
3. Verify API URL in .env.local

### Issue: "Authentication not persisting"
**Solution**:
1. Check token storage in localStorage
2. Verify cookie settings
3. Check token expiration

### Issue: "Page not found after login"
**Solution**:
1. Create missing /dashboard page
2. Or redirect to home page instead

### Issue: "Mock data still showing"
**Solution**:
1. Check API integration in component
2. Verify backend endpoints match frontend
3. Check network tab for API calls

## Testing Checklist

### After Each Phase:
```markdown
- [ ] All pages load without errors
- [ ] API calls succeed (check network tab)
- [ ] Error states display correctly
- [ ] Loading states work
- [ ] Mobile responsive
- [ ] Dark mode works
- [ ] No console errors
```

## Quick Commands

```bash
# Start frontend development
cd frontend
npm run dev

# Check for TypeScript errors
npm run type-check

# Run linting
npm run lint

# Build for production
npm run build

# Run tests
npm test
```

## File Structure Reference

```
frontend/src/
├── app/[locale]/          # Pages (Next.js App Router)
│   ├── page.tsx          # Home page
│   ├── dashboard/        # Create this
│   ├── meetings/         # Create this
│   ├── ai/              # Create this
│   └── profile/         # Create this
├── components/           # Reusable components
├── services/            # API services
├── stores/              # Zustand stores
├── hooks/               # Custom React hooks
└── types/               # TypeScript types
```

## Priority Bug Fixes

1. **Auth redirect** - Change from /dashboard to /
2. **Token refresh** - Implement the method
3. **API base URL** - Ensure it points to backend
4. **Missing pages** - Create basic versions
5. **Navigation links** - Update to valid routes

## Success Criteria

The frontend is complete when:
- [ ] All navigation links work
- [ ] User can register, login, and logout
- [ ] Chat with AI works with real backend
- [ ] All pages exist and load
- [ ] No console errors in development
- [ ] Mobile responsive throughout
- [ ] Dark mode consistent
- [ ] Loading states for all async operations
- [ ] Error handling for all API calls

---

**Remember**: Fix foundation issues first, then add features. Test frequently. Keep the backend running while developing the frontend.