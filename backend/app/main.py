# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import logging
from .routers import users  # Make sure this import is correct

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request received: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.get("/")
async def root():
    return {"message": "Welcome to the UMADex API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/test")
async def test_api():
    """Test endpoint with /api prefix"""
    logger.info("/api/test endpoint called")
    return {"message": "Test endpoint with api prefix"}

# IMPORTANT: Include the router with the CORRECT prefix
# This is the key change - the prefix should be "/api/users" NOT "/users"
app.include_router(users.router, prefix="/api/users")

# Log all routes at startup
@app.on_event("startup")
async def log_routes():
    logger.info("=== Registered Routes ===")
    for route in app.routes:
        logger.info(f"Path: {route.path}, Methods: {route.methods}")
    logger.info("========================")