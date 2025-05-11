# backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from .routers import users  # Import the users router we just created

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the UMADex API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# Include the users router
app.include_router(users.router, prefix="/api")


# Add this to your backend/app/main.py
import os

@app.get("/api/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables (remove in production)"""
    return {
        "supabase_url": os.environ.get("SUPABASE_URL", "Not set"),
        "supabase_keys_set": {
            "anon_key": bool(os.environ.get("SUPABASE_ANON_KEY")),
            "service_key": bool(os.environ.get("SUPABASE_SERVICE_KEY"))
        }
    }