#!/usr/bin/env python3
"""
Startup script for FastAPI server on port 8004.
Run with: python3 run_server.py
Or use uvicorn directly: uvicorn main:app --host 0.0.0.0 --port 8004
"""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    # Get port from environment or default to 8004
    port = int(os.getenv("PORT", "8004"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting FastAPI server on {host}:{port}")
    print("Scheduler will start automatically and run daily at 5 AM (GMT+1)")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Set to True for development
        log_level="info"
    )

