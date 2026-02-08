#!/usr/bin/env python3
"""
Test script to trigger the scheduler immediately.
Run this to test if the scheduler is working without waiting for 5 AM.

Usage:
    python3 test_scheduler.py
"""

import sys
import os
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from scheduler import daily_job_search
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
)

logger = logging.getLogger("test_scheduler")

if __name__ == "__main__":
    print("=" * 70)
    print("Testing Scheduler - Triggering Daily Job Search Now")
    print("=" * 70)
    print()
    
    try:
        logger.info("Starting daily job search test...")
        daily_job_search()
        print()
        print("=" * 70)
        print("✅ Scheduler test completed!")
        print("=" * 70)
        print()
        print("Check:")
        print("  1. Logs above for any errors")
        print("  2. Email inbox for job opportunities (if any were found)")
        print("  3. Make sure emails are configured in job_config.py")
        print()
    except Exception as e:
        logger.error(f"❌ Scheduler test failed: {str(e)}", exc_info=True)
        print()
        print("=" * 70)
        print("❌ Test failed! Check the error above.")
        print("=" * 70)
        sys.exit(1)

