from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import auth, admin_simple as admin, teacher, student, umaread_simple as umaread, tests, umaread_hybrid, student_tests, teacher_settings, test_schedule, student_debate, writing, umalecture, teacher_umatest, student_umatest
from app.core.redis import redis_client

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
app.include_router(student_tests.router, prefix="/api/v1/student", tags=["student-tests"])
app.include_router(teacher_settings.router, prefix="/api/v1/teacher", tags=["teacher-settings"])
app.include_router(test_schedule.router, prefix="/api/v1", tags=["test-schedule"])
app.include_router(student_debate.router, prefix="/api/v1/student/debate", tags=["student-debate"])
app.include_router(writing.router, prefix="/api/v1", tags=["writing"])
app.include_router(umalecture.router, prefix="/api/v1", tags=["umalecture"])
app.include_router(teacher_umatest.router, prefix="/api/v1", tags=["teacher-umatest"])
app.include_router(student_umatest.router, prefix="/api/v1/student/umatest", tags=["student-umatest"])

@app.get("/")
async def root():
    return {"message": "UmaDex API is running"}

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "umadex-api"}

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including database and redis connectivity"""
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal
    
    health_status = {
        "status": "healthy",
        "service": "umadex-api",
        "environment": settings.ENVIRONMENT,
        "checks": {}
    }
    
    # Check database connectivity
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            await session.commit()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"
    
    # Check Redis connectivity
    try:
        await redis_client.redis.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = f"error: {str(e)}"
    
    # Check Supabase config
    if settings.SUPABASE_URL:
        health_status["checks"]["supabase_config"] = "configured"
    else:
        health_status["checks"]["supabase_config"] = "not configured"
    
    return health_status