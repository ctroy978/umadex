"""Supabase client configuration for authentication"""
from supabase import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Supabase client with service role key for backend operations
supabase_admin: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

# Create Supabase client with anon key for user-facing operations
supabase_anon: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)

def get_supabase_admin() -> Client:
    """Get Supabase client with admin privileges"""
    return supabase_admin

def get_supabase_anon() -> Client:
    """Get Supabase client with anon privileges"""
    return supabase_anon