#!/usr/bin/env python3
"""Test OTP authentication flow"""
import asyncio
from app.core.supabase import get_supabase_anon

async def test_otp():
    supabase = get_supabase_anon()
    test_email = "test@example.com"
    
    print("Testing OTP Authentication Flow...")
    print("=" * 50)
    
    try:
        # Test sending OTP
        response = supabase.auth.sign_in_with_otp({
            "email": test_email,
            "options": {
                "should_create_user": True  # Allow creating user if doesn't exist
            }
        })
        print(f"✅ OTP sent successfully to {test_email}")
        print("   (Note: In development, check MailHog at http://localhost:8025)")
        
    except Exception as e:
        print(f"❌ OTP failed: {e}")
        if "Signups not allowed" in str(e):
            print("\n⚠️  Email provider is disabled in Supabase")
            print("   Go to Authentication → Providers → Enable Email provider")

if __name__ == "__main__":
    asyncio.run(test_otp())