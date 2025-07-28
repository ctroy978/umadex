# Phase 2: Configuration Changes Documentation

## Overview
This document details all configuration changes made to migrate the UMA Educational Platform from local PostgreSQL to Supabase cloud database.

## Files Modified

### 1. Backend Configuration Files

#### `/backend/app/core/config.py`
- **Added Supabase configuration variables:**
  - `SUPABASE_URL`: Supabase project URL
  - `SUPABASE_ANON_KEY`: Public anonymous key for frontend use
  - `SUPABASE_SERVICE_ROLE_KEY`: Service role key for backend operations

#### `/backend/app/core/database.py`
- **Updated database connection settings for cloud database:**
  - Added connection pooling configuration optimized for cloud databases
  - Set `pool_pre_ping=True` to handle connection drops
  - Added connection timeouts (60 seconds)
  - Added pool recycling (5 minutes)
  - Increased pool size limits for better concurrency

#### `/backend/main.py`
- **Enhanced health check endpoints:**
  - Added `/health/detailed` endpoint for monitoring database and Redis connectivity
  - Health checks now report Supabase configuration status

### 2. Docker Configuration

#### `/docker-compose.yml`
- **Removed PostgreSQL service** - Now using Supabase cloud database
- **Updated backend service:**
  - Added Supabase environment variables
  - Removed dependency on local PostgreSQL
  - Added comprehensive environment variable list
- **Kept Redis, MailHog, Frontend, and Nginx services** unchanged

#### `/docker-compose.production.yml` (NEW)
- Created production-specific Docker Compose configuration
- Optimized for production deployment with health checks
- Configured for multiple workers and production commands
- Excluded development services (MailHog)

### 3. Environment Files

#### `/.env.supabase` (NEW)
- Template for Supabase configuration
- Contains Supabase connection details
- Includes instructions for obtaining database password

#### `/.env.example`
- Updated to reflect Supabase configuration
- Removed local PostgreSQL variables
- Added Supabase-specific variables
- Added comprehensive documentation

#### `/.env.production.template` (NEW)
- Production environment template
- Includes all required variables with descriptions
- Security best practices documented
- Deployment notes included

### 4. Test and Migration Scripts

#### `/backend/test_supabase_connection.py` (NEW)
- Comprehensive connection testing script
- Verifies database connectivity
- Checks table existence
- Validates Supabase configuration

#### `/backend/update_rls_for_supabase.py` (NEW)
- Prepares RLS policies for Supabase Auth migration
- Creates helper functions for smooth transition
- Documents Phase 3 integration points

## Environment Variables Changed/Added

### Removed Variables
- `POSTGRES_DB`
- `POSTGRES_USER`  
- `POSTGRES_PASSWORD`

### Added Variables
- `DATABASE_URL` - Full Supabase database connection string
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Public key for frontend
- `SUPABASE_SERVICE_ROLE_KEY` - Admin key for backend

### Modified Variables
- `DATABASE_URL` now points to Supabase instead of local PostgreSQL

## Docker Services Changes

### Removed Services
- `postgres` - PostgreSQL database container

### Modified Services
- `backend` - Updated environment variables and removed PostgreSQL dependency

### Unchanged Services
- `redis` - Still needed for caching and session management
- `mailhog` - Development email testing
- `frontend` - React application
- `nginx` - Reverse proxy

## Connection String Formats

### Development (with Docker)
```
DATABASE_URL=postgresql://postgres.wssmxlqloncdhonzssbj:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

### Production Options
1. **Transaction Mode (Recommended for auto-scaling)**
   - Port: 6543
   - Best for: Serverless, Edge Functions, Auto-scaling containers

2. **Session Mode**
   - Port: 5432  
   - Best for: Long-running connections, IPv4-only environments

3. **Direct Connection**
   - Port: 5432
   - Best for: VMs with IPv6 support
   - Requires IPv4 add-on for IPv4-only environments

## Performance Optimizations

### Connection Pool Settings
```python
pool_size=10              # Base pool size
max_overflow=20           # Additional connections when needed
pool_pre_ping=True        # Verify connections before use
pool_recycle=300          # Recycle connections after 5 minutes
timeout=60                # Connection timeout
command_timeout=60        # Query timeout
```

### Why These Settings?
- **pool_pre_ping**: Essential for cloud databases to handle network interruptions
- **pool_recycle**: Prevents long-idle connections from timing out
- **Timeouts**: Generous timeouts for cloud database latency

## Security Considerations

1. **Never commit actual credentials** to version control
2. **Use environment variable injection** in deployment platforms
3. **Rotate keys regularly**
4. **Monitor connection usage** in Supabase dashboard
5. **Use transaction mode** for better connection efficiency

## Migration Checklist

Before deploying with Supabase:

- [ ] Obtain database password from Supabase dashboard
- [ ] Update DATABASE_URL in environment file
- [ ] Test connection with `test_supabase_connection.py`
- [ ] Verify all tables exist (from Phase 1 migration)
- [ ] Test application startup with new configuration
- [ ] Monitor connection pool usage in Supabase dashboard
- [ ] Set up Redis for production (or keep local for development)
- [ ] Configure production email service (or keep MailHog for dev)

## Common Issues and Solutions

### Connection Refused
- Check DATABASE_URL format
- Verify password is correct
- Ensure Supabase project is active

### Connection Timeouts
- Check network connectivity
- Verify connection string uses correct pooler mode
- Consider using transaction mode (port 6543)

### Too Many Connections
- Monitor pool size settings
- Use transaction mode for better efficiency
- Check for connection leaks in application code

## Next Steps (Phase 3)

1. **Replace custom authentication with Supabase Auth**
2. **Update RLS policies to use auth.uid()**
3. **Migrate user sessions to Supabase Auth**
4. **Update frontend to use Supabase client libraries**
5. **Remove custom OTP and session management**

## Rollback Plan

If issues arise:
1. Keep backup of original `.env` file
2. Original `docker-compose.yml` can be restored
3. Local PostgreSQL data volume still exists
4. Switch back by changing DATABASE_URL to local PostgreSQL

## Resources

- [Supabase Dashboard](https://supabase.com/dashboard/project/wssmxlqloncdhonzssbj)
- [Connection Strings](https://supabase.com/dashboard/project/wssmxlqloncdhonzssbj/settings/database)
- [Supabase Docs](https://supabase.com/docs)
- [Connection Pooling Guide](https://supabase.com/docs/guides/database/connecting-to-postgres)