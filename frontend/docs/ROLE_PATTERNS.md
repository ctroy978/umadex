# Role-Based Access Control Patterns

This document provides copy-paste templates and patterns for implementing consistent role-based access control as the UmaDex application grows.

## Quick Reference

### Current Role Hierarchy
```
admin (highest privileges)
  ↓
teacher (moderate privileges)
  ↓  
student (basic privileges)
```

## Adding a New User Role

### Step 1: Update Type Definitions

**File:** `/src/types/auth.ts`
```typescript
// Add your new role to the UserRole type
export type UserRole = 'student' | 'teacher' | 'admin' | 'newrole'

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: UserRole  // This will now include your new role
  is_admin: boolean
  created_at: string
}
```

### Step 2: Create Role Guard Component

**File:** `/src/components/NewRoleGuard.tsx`
```typescript
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

/**
 * SECURITY COMPONENT: NewRole Route Guard
 * 
 * This component protects all newrole routes via layout-level implementation.
 * It ensures only authenticated users with 'newrole' role can access newrole pages.
 * 
 * SECURITY FEATURES:
 * 1. Prevents access before authentication completes (isLoading check)
 * 2. Redirects non-newrole users to appropriate dashboards based on role
 * 3. Graceful handling of unauthenticated users
 * 
 * IMPLEMENTATION PATTERN:
 * Used in /app/newrole/layout.tsx to protect ALL newrole routes.
 * Do NOT use this component on individual pages - use layout-level protection.
 */

interface NewRoleGuardProps {
  children: React.ReactNode
}

export default function NewRoleGuard({ children }: NewRoleGuardProps) {
  const { user, isLoading, loadUser } = useAuth()
  const router = useRouter()

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.push('/login')
        return
      }
      
      // Redirect based on actual role
      if (user.role !== 'newrole') {
        if (user.role === 'student') {
          router.push('/student/dashboard')
        } else if (user.role === 'teacher') {
          router.push('/teacher/dashboard')
        } else if (user.role === 'admin') {
          router.push('/admin/dashboard')
        } else {
          router.push('/login')
        }
        return
      }
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!user || user.role !== 'newrole') {
    return null
  }

  return <>{children}</>
}
```

### Step 3: Create Role Layout

**File:** `/src/app/newrole/layout.tsx`
```typescript
'use client'

import NewRoleGuard from '@/components/NewRoleGuard'

/**
 * SECURITY LAYOUT: NewRole Route Protection
 * 
 * This layout provides authentication protection for ALL newrole routes.
 * It wraps every page under /newrole/* with the NewRoleGuard component.
 * 
 * SECURITY BENEFITS:
 * - Single point of auth control for all newrole functionality
 * - Prevents unauthorized access to any newrole page
 * - Consistent loading states and redirects
 * - Better performance than page-level guards
 * 
 * IMPORTANT: Do NOT add additional NewRoleGuard components to individual
 * newrole pages - they inherit protection from this layout.
 */

export default function NewRoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <NewRoleGuard>
      {children}
    </NewRoleGuard>
  )
}
```

### Step 4: Update Existing Guards

Update the redirect logic in existing guards to handle the new role:

**Files to Update:**
- `/src/components/StudentGuard.tsx`
- `/src/components/TeacherGuard.tsx`
- Any other existing guards

**Pattern to Add:**
```typescript
if (user.role !== 'expectedrole') {
  // Add new role to redirect logic
  if (user.role === 'newrole') {
    router.push('/newrole/dashboard')
  } else if (user.role === 'student') {
    router.push('/student/dashboard')
  }
  // ... other existing redirects
  return
}
```

## Common Access Control Patterns

### Pattern 1: Simple Role Check
```typescript
const { user } = useAuth()

// Single role access
if (user?.role === 'teacher') {
  return <TeacherOnlyComponent />
}

// Multiple role access
if (['teacher', 'admin'].includes(user?.role)) {
  return <PrivilegedComponent />
}

return <AccessDeniedMessage />
```

### Pattern 2: Hierarchical Access (Higher Roles Include Lower)
```typescript
const { user } = useAuth()

const hasMinimumRole = (userRole: string, requiredRole: string) => {
  const hierarchy = ['student', 'teacher', 'admin']
  const userLevel = hierarchy.indexOf(userRole)
  const requiredLevel = hierarchy.indexOf(requiredRole)
  return userLevel >= requiredLevel
}

// Teacher access (teachers and admins can access)
if (hasMinimumRole(user?.role, 'teacher')) {
  return <TeacherFeature />
}
```

### Pattern 3: Conditional UI Elements
```typescript
const { user } = useAuth()

return (
  <div>
    <h1>Dashboard</h1>
    
    {/* Show only to teachers and admins */}
    {['teacher', 'admin'].includes(user?.role) && (
      <AdminSection />
    )}
    
    {/* Show only to admins */}
    {user?.role === 'admin' && (
      <SuperAdminControls />
    )}
    
    {/* Show to everyone except students */}
    {user?.role !== 'student' && (
      <StaffTools />
    )}
  </div>
)
```

### Pattern 4: Hook for Role Checking
```typescript
// /src/hooks/usePermissions.ts
import { useAuth } from './useAuth'

export const usePermissions = () => {
  const { user } = useAuth()
  
  return {
    isStudent: user?.role === 'student',
    isTeacher: user?.role === 'teacher',
    isAdmin: user?.role === 'admin',
    isAuthenticated: !!user,
    hasRole: (role: string) => user?.role === role,
    hasAnyRole: (roles: string[]) => roles.includes(user?.role),
    hasMinimumRole: (requiredRole: string) => {
      const hierarchy = ['student', 'teacher', 'admin']
      const userLevel = hierarchy.indexOf(user?.role || '')
      const requiredLevel = hierarchy.indexOf(requiredRole)
      return userLevel >= requiredLevel
    }
  }
}

// Usage in components:
const { isTeacher, hasMinimumRole } = usePermissions()

if (isTeacher) {
  return <TeacherDashboard />
}

if (hasMinimumRole('teacher')) {
  return <StaffPanel />
}
```

## Security Checklist for New Roles

When implementing a new role, ensure you:

### Frontend Checklist
- [ ] Updated `UserRole` type in `/src/types/auth.ts`
- [ ] Created new role guard component
- [ ] Created role-specific layout with guard
- [ ] Updated existing guards to handle new role redirects
- [ ] Added appropriate navigation/UI for new role
- [ ] Created role-specific dashboard/landing page
- [ ] Added role checks to relevant components
- [ ] Updated permission hooks if using

### Backend Checklist (Reference)
- [ ] Updated user model with new role
- [ ] Added role to authentication middleware
- [ ] Created role-specific route protections
- [ ] Updated API documentation
- [ ] Added database migration for role changes
- [ ] Updated seed data if applicable

### Testing Checklist
- [ ] Test new role can access intended routes
- [ ] Test new role is blocked from unauthorized routes
- [ ] Test role transitions (login/logout scenarios)
- [ ] Test existing roles still work correctly
- [ ] Test edge cases (invalid roles, etc.)

## Common Pitfalls to Avoid

### ❌ Don't: Page-Level Guards
```typescript
// AVOID: Individual page guards when layout exists
export default function SomePage() {
  return (
    <NewRoleGuard>  {/* Don't do this! */}
      <PageContent />
    </NewRoleGuard>
  )
}
```

### ✅ Do: Layout-Level Guards
```typescript
// CORRECT: Guard at layout level
// /app/newrole/layout.tsx
export default function Layout({ children }) {
  return (
    <NewRoleGuard>
      {children}  {/* All pages automatically protected */}
    </NewRoleGuard>
  )
}
```

### ❌ Don't: Role Hardcoding
```typescript
// AVOID: Hardcoded role strings throughout app
if (user.role === 'teacher') { } // Scattered everywhere
```

### ✅ Do: Centralized Role Logic
```typescript
// CORRECT: Centralized permission checking
const { isTeacher } = usePermissions()
if (isTeacher) { }
```

### ❌ Don't: Client-Side Only Security
```typescript
// AVOID: Only checking permissions on frontend
const { isAdmin } = usePermissions()
if (isAdmin) {
  await api.deleteUser(userId) // Backend must also verify!
}
```

### ✅ Do: Defense in Depth
```typescript
// CORRECT: Frontend + backend validation
const { isAdmin } = usePermissions()
if (isAdmin) {
  try {
    await api.deleteUser(userId) // Backend verifies admin role
  } catch (error) {
    if (error.status === 403) {
      // Handle insufficient permissions
    }
  }
}
```

---

**See Also:**
- [SECURITY.md](./SECURITY.md) - Complete security architecture
- [/src/types/auth.ts](../src/types/auth.ts) - Auth type definitions
- [/src/hooks/useAuth.ts](../src/hooks/useAuth.ts) - Auth state management