#!/usr/bin/env python3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test logging
logger = logging.getLogger(__name__)
logger.info("Test logging message")

# Test with the same logger name as our service
service_logger = logging.getLogger("app.services.vocabulary_practice")
service_logger.info("Test service logging message")

print("Logging test complete")