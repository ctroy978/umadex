from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import auth, admin, teacher, student, umaread_simple as umaread, tests, umaread_hybrid
from app.core.redis import redis_client

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await redis_client.initialize()
    yield
    # Shutdown
    await redis_client.close()

app = FastAPI(
    title="UmaDex API",
    description="Educational Assignment App API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(teacher.router, prefix="/api/v1/teacher", tags=["teacher"])
app.include_router(student.router, prefix="/api/v1/student", tags=["student"])
app.include_router(umaread.router, prefix="/api/v1/student", tags=["umaread"])
app.include_router(umaread_hybrid.router, prefix="/api/v1/student", tags=["umaread-v2"])
app.include_router(tests.router, prefix="/api/v1", tags=["tests"])

@app.get("/")
async def root():
    return {"message": "UmaDex API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}