"""
Temporary file showing how to integrate both auth routers during migration.
Add this to your main.py during the testing phase.
"""

# In your main.py, add both routers:

from app.api.v1 import auth, auth_supabase

# Existing auth router (keep for now)
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["auth-legacy"]
)

# New Supabase auth router (for testing)
app.include_router(
    auth_supabase.router,
    prefix="/api/v1/auth-supabase",
    tags=["auth-supabase"]
)

# During migration, you can also create a feature flag approach:
import os

USE_SUPABASE_AUTH = os.getenv("USE_SUPABASE_AUTH", "false").lower() == "true"

if USE_SUPABASE_AUTH:
    # Use Supabase auth as primary
    app.include_router(
        auth_supabase.router,
        prefix="/api/v1/auth",
        tags=["auth"]
    )
else:
    # Use legacy auth
    app.include_router(
        auth.router,
        prefix="/api/v1/auth",
        tags=["auth"]
    )