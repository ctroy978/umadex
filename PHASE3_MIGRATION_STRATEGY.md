# Phase 3: Authentication Migration Strategy

## Overview
This document outlines the strategy for migrating from your custom JWT/OTP authentication to Supabase Auth while maintaining zero downtime and preserving the existing user experience.

## Migration Approach: Parallel Implementation

We'll implement Supabase Auth alongside the existing system, allowing for gradual migration and easy rollback if needed.

### Phase 3A: Parallel Implementation (Current Step)

1. **Backend Setup**
   - ✅ Created Supabase client configuration
   - ✅ Added `supabase_auth_id` field to users table
   - ✅ Created new auth service using Supabase
   - ✅ Created new auth endpoints with `/auth-supabase` prefix
   - ✅ Created new authentication dependencies

2. **Frontend Setup**
   - ✅ Created Supabase client configuration
   - ✅ Created new auth service using Supabase
   - ✅ Created new API client with Supabase interceptors
   - ✅ Created new auth hook for Supabase

3. **User Migration**
   - Created migration script to sync existing users to Supabase Auth
   - Users will maintain their existing sessions during migration

### Phase 3B: Testing Phase

1. **Create Test Environment**
   ```bash
   # Backend: Update main.py to include both auth routers
   # Add to your route configuration:
   app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
   app.include_router(auth_supabase_router, prefix="/api/v1/auth-supabase", tags=["auth-supabase"])
   ```

2. **Test with Feature Flag**
   ```typescript
   // In your frontend, create a feature flag
   const USE_SUPABASE_AUTH = process.env.NEXT_PUBLIC_USE_SUPABASE_AUTH === 'true'
   
   // Import the appropriate modules
   const auth = USE_SUPABASE_AUTH ? authSupabase : authLegacy
   const api = USE_SUPABASE_AUTH ? apiSupabase : apiLegacy
   const useAuth = USE_SUPABASE_AUTH ? useAuthSupabase : useAuthLegacy
   ```

3. **Test All User Flows**
   - New user registration with whitelist
   - Existing user login
   - OTP delivery and verification
   - Session persistence
   - Token refresh
   - Logout
   - Role-based access (student/teacher/admin)

### Phase 3C: Gradual Rollout

1. **Run User Migration**
   ```bash
   cd backend
   python migrate_users_to_supabase_auth.py
   ```

2. **Update Dependencies Gradually**
   - Start by updating non-critical endpoints
   - Monitor for any issues
   - Gradually update all endpoints to use `supabase_deps`

3. **Frontend Cutover**
   - Enable Supabase auth for internal testing
   - Roll out to a percentage of users
   - Monitor and fix any issues
   - Complete rollout

### Phase 3D: Cleanup

Once stable:
1. Remove old auth endpoints
2. Remove Redis OTP caching
3. Remove custom JWT generation
4. Remove old auth dependencies
5. Clean up unused code

## Environment Variables

### Backend (.env)
```bash
# Existing (from Phase 2)
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Can be removed after migration
REDIS_URL=redis://redis:6379  # Only if not used elsewhere
SECRET_KEY=...  # Still needed for other purposes
```

### Frontend (.env.local)
```bash
# Add these
NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT-REF].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here

# Feature flag for testing
NEXT_PUBLIC_USE_SUPABASE_AUTH=false  # Set to true when testing
```

## Testing Checklist

### Authentication Flow
- [ ] User can request OTP
- [ ] OTP email is received within 1 minute
- [ ] OTP can be verified successfully
- [ ] Invalid OTP is rejected
- [ ] Expired OTP is rejected

### Session Management
- [ ] User stays logged in on page refresh
- [ ] Token automatically refreshes before expiry
- [ ] Session persists for expected duration
- [ ] Logout clears all sessions

### Role-Based Access
- [ ] Students can only access student routes
- [ ] Teachers can access teacher dashboard
- [ ] Admins can access admin panel
- [ ] Unauthorized access is blocked

### User Management
- [ ] New users can register (if whitelisted)
- [ ] Existing users can login
- [ ] User profile data is correct
- [ ] Admin can promote users
- [ ] Soft-deleted users cannot login

### Integration
- [ ] All API endpoints work with new auth
- [ ] File uploads work correctly
- [ ] Real-time features work (if any)
- [ ] No CORS issues

## Rollback Plan

If issues arise:
1. Set `NEXT_PUBLIC_USE_SUPABASE_AUTH=false`
2. Revert backend to use old auth dependencies
3. Monitor and fix issues
4. Retry migration

## Common Issues and Solutions

### Issue: Email delivery delays
**Solution**: Configure Supabase to use your production SMTP provider (SendGrid)

### Issue: Token expiration mismatches
**Solution**: Ensure Supabase session duration matches your current settings

### Issue: CORS errors
**Solution**: Add your domains to Supabase URL configuration

### Issue: Users can't login after migration
**Solution**: Check that whitelist logic is properly implemented in new auth service

### Issue: RLS policies failing
**Solution**: Ensure RLS policies are updated to work with Supabase JWT format

## Next Steps

1. **Configure Supabase Auth** in the dashboard (Step 1)
2. **Run migrations** to add supabase_auth_id field
3. **Test the parallel implementation** with a test user
4. **Run user migration script** 
5. **Gradually roll out** to all users
6. **Clean up** old authentication code

## Important Notes

- Keep the old auth system running until fully migrated
- Test thoroughly with each user role
- Monitor error logs during migration
- Have a rollback plan ready
- Communicate with users about any expected downtime