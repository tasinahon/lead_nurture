#!/usr/bin/env python3
"""
Azure-friendly startup script for LinkedIn Scraper
"""

import os
import subprocess
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_chrome_dependencies():
    """Install Chrome and ChromeDriver for Azure Linux environment"""
    try:
        logger.info("🔧 Installing Chrome dependencies...")
        
        # Install Chrome
        commands = [
            "apt-get update",
            "apt-get install -y wget gnupg unzip",
            "wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -",
            "echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' > /etc/apt/sources.list.d/google.list",
            "apt-get update",
            "apt-get install -y google-chrome-stable"
        ]
        
        for cmd in commands:
            logger.info(f"Running: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Command failed: {cmd}")
                logger.warning(f"Error: {result.stderr}")
        
        # Install ChromeDriver via webdriver-manager (easier)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            driver_path = ChromeDriverManager().install()
            logger.info(f"✅ ChromeDriver installed at: {driver_path}")
        except Exception as e:
            logger.error(f"Failed to install ChromeDriver: {e}")
        
        logger.info("✅ Chrome dependencies installation complete")
        
    except Exception as e:
        logger.error(f"❌ Error installing Chrome dependencies: {e}")

def start_application():
    """Start the FastAPI application"""
    try:
        logger.info("🚀 Starting FastAPI application...")
        
        # Create output directory
        os.makedirs("./output", exist_ok=True)
        
        # Start uvicorn server
        import uvicorn
        uvicorn.run(
            "fastapi_app:app",
            host="0.0.0.0", 
            port=int(os.environ.get("PORT", 8000)),
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Only install Chrome dependencies if we're in Azure (Linux environment)
    if os.path.exists("/etc/debian_version"):
        install_chrome_dependencies()
    
    start_application()