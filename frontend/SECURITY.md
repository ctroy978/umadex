# Frontend Security Architecture

## Overview

This document outlines the security architecture for the UmaDex frontend application, providing guidelines for consistent security implementation as the application grows.

## Core Security Principles

### 1. Authentication Architecture

**Current Implementation:**
- JWT-based authentication with access/refresh token system
- Tokens stored in localStorage via `tokenStorage` service
- Automatic token refresh when near expiry
- Centralized auth state management with Zustand

**Key Files:**
- `/src/lib/auth.ts` - Authentication service
- `/src/lib/tokenStorage.ts` - Token management
- `/src/hooks/useAuth.ts` - Auth state hook

### 2. Role-Based Access Control (RBAC)

**Current Roles:**
- `student` - Limited access to assignments and tests
- `teacher` - Classroom management, assignment creation
- `admin` - Full system access

**Access Control Pattern:**
```
Layout-Level Guards → Route Protection → Component-Level Checks
```

## Security Layers

### Layer 1: Layout-Level Route Protection

**Pattern:** Each user role has a dedicated layout with authentication guard.

**Current Implementation:**
```
/app/student/layout.tsx  → StudentGuard → All student routes
/app/teacher/layout.tsx  → TeacherGuard → All teacher routes
/app/admin/layout.tsx    → AdminGuard   → All admin routes (if needed)
```

**Benefits:**
- Single point of auth control per role
- Prevents unauthorized access to entire route sections
- Consistent UX with unified loading states
- Harder to bypass than page-level guards

### Layer 2: API Authorization

**Pattern:** All API calls include authentication headers and validate permissions server-side.

**Implementation:**
- Automatic token inclusion via API interceptors
- Server validates JWT and role permissions
- Frontend handles 401/403 responses gracefully

### Layer 3: Component-Level Protection

**Pattern:** Sensitive UI components check user permissions before rendering.

**Example:**
```tsx
const { user } = useAuth();
if (user?.role !== 'teacher') return null;
return <TeacherOnlyComponent />;
```

## Adding New User Roles

### Step 1: Define Role
1. Add role to backend user model
2. Update frontend `User` type in `/src/types/auth.ts`
3. Add role validation to auth guards

### Step 2: Create Role-Specific Layout
```tsx
// /app/newrole/layout.tsx
'use client'
import NewRoleGuard from '@/components/NewRoleGuard'

export default function NewRoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <NewRoleGuard>
      {children}
    </NewRoleGuard>
  )
}
```

### Step 3: Create Role Guard Component
```tsx
// /components/NewRoleGuard.tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

export default function NewRoleGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading, loadUser } = useAuth()
  const router = useRouter()

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!isLoading && (!user || user.role !== 'newrole')) {
      router.push('/login')
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return <div>Loading...</div>
  }

  if (!user || user.role !== 'newrole') {
    return null
  }

  return <>{children}</>
}
```

### Step 4: Update Existing Guards (if needed)
- Modify redirect logic in existing guards to handle new role
- Update role checks in shared components

## Security Best Practices

### DO ✅
- Use layout-level guards for route protection
- Validate permissions on both frontend and backend
- Use TypeScript for type safety
- Store tokens securely in localStorage (or httpOnly cookies for enhanced security)
- Handle token expiry gracefully with refresh mechanism
- Clear sensitive data on logout

### DON'T ❌
- Rely solely on frontend checks for security
- Store sensitive data in component state
- Skip server-side permission validation
- Use page-level guards when layout-level guards suffice
- Expose admin functionality to non-admin users
- Trust user role from localStorage without server validation

## File Structure

```
src/
├── components/
│   ├── AuthGuard.tsx          # Generic auth guard
│   ├── StudentGuard.tsx       # Student role guard
│   ├── TeacherGuard.tsx       # Teacher role guard
│   └── AdminGuard.tsx         # Admin role guard (future)
├── hooks/
│   └── useAuth.ts             # Auth state management
├── lib/
│   ├── auth.ts                # Auth service
│   ├── tokenStorage.ts        # Token management
│   └── api.ts                 # API client with auth
├── types/
│   └── auth.ts                # Auth type definitions
└── app/
    ├── student/
    │   ├── layout.tsx         # Student route protection
    │   └── [pages]            # Student pages (unguarded)
    ├── teacher/
    │   ├── layout.tsx         # Teacher route protection
    │   └── [pages]            # Teacher pages (unguarded)
    └── login/
        └── page.tsx           # Public login page
```

## Common Patterns

### Route Protection
```tsx
// Layout-level protection (PREFERRED)
<UserRoleGuard>
  {children}
</UserRoleGuard>

// Page-level protection (AVOID if layout exists)
<UserRoleGuard>
  <PageContent />
</UserRoleGuard>
```

### Conditional Rendering
```tsx
const { user } = useAuth();

// Simple role check
if (user?.role === 'teacher') {
  return <TeacherComponent />;
}

// Multi-role check
if (['teacher', 'admin'].includes(user?.role)) {
  return <PrivilegedComponent />;
}
```

### API Error Handling
```tsx
try {
  const data = await api.get('/protected-endpoint');
} catch (error) {
  if (error.response?.status === 401) {
    // Token expired, redirect to login
    await authService.logout();
  } else if (error.response?.status === 403) {
    // Insufficient permissions, show error
    setError('Access denied');
  }
}
```

## Testing Security

### Unit Tests
- Test guard components with different user roles
- Verify token storage and refresh logic
- Test API error handling

### Integration Tests
- Verify route protection works end-to-end
- Test role transitions (student → teacher login)
- Validate logout clears all sensitive data

### Security Checklist
- [ ] New routes have appropriate guards
- [ ] API endpoints validate permissions server-side
- [ ] Error states don't leak sensitive information
- [ ] Token expiry is handled gracefully
- [ ] Logout clears all user data
- [ ] Role changes are reflected immediately

## Future Considerations

### Enhanced Security
- Consider httpOnly cookies for token storage
- Implement CSRF protection
- Add rate limiting on sensitive operations
- Consider session management improvements

### Multi-Factor Authentication
- Design hooks/components to support MFA flows
- Plan token structure for MFA sessions

### Audit Logging
- Plan frontend event tracking for security events
- Consider user action logging for compliance

---

**Last Updated:** 2024-06-07  
**Version:** 1.0  
**Maintainer:** Development Team