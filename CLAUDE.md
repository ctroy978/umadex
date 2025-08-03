# Claude Code Project Guidelines

## Project Context

### Architecture Overview
- **Application runs in Docker Compose** - The entire application stack runs in Docker containers managed by docker-compose
- **Database Migration in Progress** - We are transitioning from local PostgreSQL to Supabase database
- **Authentication Migration in Progress** - We are transitioning from local authentication to Supabase Auth

### Current State
- Some features may still use local auth/db while others use Supabase
- Both authentication systems may be active during the transition period
- Check `SUPABASE_URL` and `DATABASE_URL` environment variables to understand current configuration

## Database Migration Rules

### Supabase Migration Requirements

When working with database schema changes in this project:

1. **ALWAYS use Supabase migrations** - Since we're using Supabase as our database, all schema changes MUST be applied using `mcp__supabase__apply_migration` to ensure they persist through database resets.

2. **DO NOT rely on local Alembic migrations alone** - The local Alembic migration files in `backend/alembic/versions/` are for reference but won't automatically apply to Supabase.

3. **Migration procedure**:
   - First, create the migration SQL using `mcp__supabase__apply_migration`
   - Optionally, create a corresponding Alembic migration file for local documentation
   - Always verify the migration was applied using `mcp__supabase__list_migrations`

4. **Example**:
   ```
   # Good - Migration will persist
   mcp__supabase__apply_migration(
     name="add_new_column_to_table",
     query="ALTER TABLE my_table ADD COLUMN new_column TEXT;"
   )
   
   # Bad - Local file only, won't apply to Supabase
   # Just creating a file in backend/alembic/versions/
   ```

5. **Check migration status** - Use `mcp__supabase__list_migrations` to verify all migrations are properly tracked in Supabase.

## Docker Commands

### Common Operations
- **View logs**: `docker-compose logs [service_name]`
- **Restart service**: `docker-compose restart [service_name]`
- **Execute commands**: `docker-compose exec [service_name] [command]`
- **Services**: backend, frontend, redis, mailhog

## Authentication Notes

### Dual Auth System
During the transition period:
- Check for `supabase_auth_id` in the users table to identify Supabase-authenticated users
- Legacy users may still use local authentication
- New features should use Supabase Auth
- API endpoints may need to handle both auth types

## Other Project Rules

(Add other project-specific rules here as needed)