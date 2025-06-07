# UmaDex Frontend

Educational assignment management application built with Next.js, TypeScript, and Tailwind CSS.

## Getting Started

### Development
```bash
npm run dev
```

### Build
```bash
npm run build
npm start
```

## Project Structure

```
src/
├── app/                    # Next.js app router pages
│   ├── student/           # Student-only routes (protected)
│   ├── teacher/           # Teacher-only routes (protected)
│   └── login/             # Public authentication
├── components/            # Reusable UI components
│   ├── *Guard.tsx         # Authentication guards
│   ├── student/           # Student-specific components
│   └── teacher/           # Teacher-specific components
├── hooks/                 # Custom React hooks
├── lib/                   # Utility libraries and services
├── types/                 # TypeScript type definitions
└── docs/                  # Documentation
```

## 🔒 Security Architecture

This application implements a comprehensive role-based access control (RBAC) system with multiple security layers.

### Quick Security Reference

- **Authentication:** JWT-based with refresh tokens
- **Authorization:** Role-based (student, teacher, admin)
- **Route Protection:** Layout-level guards for each user type
- **Token Management:** Automatic refresh with secure storage

### Key Security Files

| File | Purpose |
|------|---------|
| `SECURITY.md` | Complete security architecture documentation |
| `docs/ROLE_PATTERNS.md` | Templates for adding new user roles |
| `src/hooks/useAuth.ts` | Central authentication state management |
| `src/components/*Guard.tsx` | Route protection components |
| `src/app/*/layout.tsx` | Layout-level security implementation |

### Adding New User Roles

When adding new user roles or protected routes:

1. **Read the Documentation First**
   ```bash
   # Essential reading for security implementation
   cat SECURITY.md
   cat docs/ROLE_PATTERNS.md
   ```

2. **Follow the Established Patterns**
   - Use layout-level guards (not page-level)
   - Update type definitions
   - Follow the guard component template
   - Update existing guard redirect logic

3. **Security Checklist**
   - [ ] Updated user role types
   - [ ] Created role-specific guard component
   - [ ] Implemented layout-level protection
   - [ ] Updated existing guards' redirect logic
   - [ ] Tested unauthorized access attempts
   - [ ] Verified backend API permissions

### Security Best Practices

✅ **DO:**
- Use layout-level guards for route protection
- Validate permissions on both frontend and backend
- Clear all user data on logout
- Handle token expiry gracefully

❌ **DON'T:**
- Use page-level guards when layout-level guards exist
- Rely solely on frontend security checks
- Store sensitive data in component state
- Skip server-side permission validation

## Development Guidelines

### Authentication Flow
1. User enters email → OTP sent
2. User enters OTP → JWT tokens issued
3. Tokens stored in localStorage
4. Auto-refresh before expiry
5. Route guards check auth state
6. API calls include auth headers

### Component Patterns
```tsx
// ✅ Correct: Use the auth hook
const { user, isLoading } = useAuth()

// ✅ Correct: Check role permissions
if (user?.role === 'teacher') {
  return <TeacherFeature />
}

// ✅ Correct: Handle loading states
if (isLoading) {
  return <LoadingSpinner />
}
```

### Common Pitfalls
- Don't add individual guards to pages that have layout guards
- Always check `isLoading` before making auth decisions
- Remember that frontend security is UX - backend must validate everything

## Contributing

Before making security-related changes:

1. Review `SECURITY.md` for architecture overview
2. Check `docs/ROLE_PATTERNS.md` for implementation patterns
3. Follow existing guard component patterns
4. Test both authorized and unauthorized access scenarios

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State Management:** Zustand (auth state)
- **Authentication:** JWT with refresh tokens
- **API Client:** Axios

---

**Security Documentation:** See `SECURITY.md` and `docs/ROLE_PATTERNS.md` for comprehensive security implementation guidelines.