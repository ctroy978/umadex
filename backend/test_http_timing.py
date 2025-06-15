#!/usr/bin/env python3
"""
Test HTTP endpoint timing to identify where hangs occur
"""
import asyncio
import aiohttp
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_endpoint_timing():
    """Test various endpoints to see timing"""
    
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Simple health check
        logger.info("Testing health endpoint...")
        start_time = time.time()
        try:
            async with session.get(f"{base_url}/", timeout=30) as resp:
                logger.info(f"Health check: {resp.status} in {time.time() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        
        # Test 2: Auth request (should be fast)
        logger.info("Testing auth request...")
        start_time = time.time()
        try:
            async with session.post(
                f"{base_url}/api/v1/auth/request-otp",
                json={"email": "acoop@csd8.info"},
                timeout=30
            ) as resp:
                logger.info(f"Auth request: {resp.status} in {time.time() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"Auth request failed: {e}")
        
        # Test 3: Non-existent endpoint (should be fast 404)
        logger.info("Testing 404 endpoint...")
        start_time = time.time()
        try:
            async with session.get(f"{base_url}/nonexistent", timeout=30) as resp:
                logger.info(f"404 test: {resp.status} in {time.time() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"404 test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoint_timing())