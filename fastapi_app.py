#!/usr/bin/env python3
"""
LinkedIn Profile Scraper API - FastAPI Version
High-performance REST API with automatic documentation
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Try to import the scraper with error handling
try:
    from simple_linkedin_scraper import SimpleLinkedInScraper
    SCRAPER_AVAILABLE = True
    SCRAPER_ERROR = None
    print("✅ SimpleLinkedInScraper imported successfully")
except Exception as e:
    SCRAPER_AVAILABLE = False
    SCRAPER_ERROR = str(e)
    print(f"❌ Failed to import SimpleLinkedInScraper: {e}")
    # Create a dummy class to prevent errors
    class SimpleLinkedInScraper:
        def __init__(self):
            raise Exception("Scraper not available due to import error")

# FastAPI app instance
app = FastAPI(
    title="LinkedIn Profile Scraper API",
    description="High-performance LinkedIn profile scraping API with automatic documentation",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc"  # ReDoc at /redoc
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global scraper instance
scraper_instance = None
scraper_lock = threading.Lock()

# Pydantic models for request/response validation
class ScrapeRequest(BaseModel):
    profile_url: str = Field(..., description="LinkedIn profile URL to scrape")
    save_to_file: bool = Field(default=False, description="Whether to save the scraped data to a file")
    
    @validator('profile_url')
    def validate_profile_url(cls, v):
        if not v.startswith('https://www.linkedin.com/in/'):
            raise ValueError('Invalid LinkedIn profile URL. Must start with https://www.linkedin.com/in/')
        return v

class BatchScrapeRequest(BaseModel):
    profile_urls: List[str] = Field(..., description="List of LinkedIn profile URLs to scrape", min_items=1, max_items=10)
    save_to_file: bool = Field(default=False, description="Whether to save the scraped data to files")
    
    @validator('profile_urls')
    def validate_profile_urls(cls, v):
        for url in v:
            if not url.startswith('https://www.linkedin.com/in/'):
                raise ValueError(f'Invalid LinkedIn profile URL: {url}')
        return v

class ProfileData(BaseModel):
    name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    followers: Optional[str] = None
    about: Optional[str] = None
    experience: Optional[List[Dict[str, Any]]] = []
    education: Optional[List[Dict[str, Any]]] = []
    skills: Optional[List[str]] = []

class ScrapeResponse(BaseModel):
    status: str
    message: str
    data: Optional[ProfileData] = None
    metadata: Dict[str, Any]

class BatchScrapeResponse(BaseModel):
    status: str
    message: str
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class StatusResponse(BaseModel):
    scraper_initialized: bool
    logged_in: bool
    platform: str
    timestamp: str

class FileInfo(BaseModel):
    filename: str
    size_bytes: int
    created_at: str
    modified_at: str

def get_scraper():
    """Get or create scraper instance (thread-safe)"""
    global scraper_instance
    with scraper_lock:
        if scraper_instance is None:
            scraper_instance = SimpleLinkedInScraper()
        return scraper_instance

@app.get("/", response_model=Dict[str, Any], tags=["Health"])
async def health_check():
    """
    Health check endpoint
    
    Returns basic API information and available endpoints.
    """
    return {
        "status": "success",
        "message": "LinkedIn Profile Scraper API (FastAPI) is running",
        "version": "2.0.0",
        "framework": "FastAPI",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        },
        "endpoints": {
            "health": "GET / - Health check",
            "scrape": "POST /api/scrape - Scrape a LinkedIn profile",
            "batch_scrape": "POST /api/scrape/batch - Scrape multiple profiles",
            "status": "GET /api/status - Get scraper status",
            "files": "GET /api/files - List output files",
            "download": "GET /api/files/{filename} - Download specific file"
        },
        "features": [
            "Automatic API documentation",
            "Request/response validation",
            "Type hints and IntelliSense support",
            "High performance async handling",
            "CORS enabled",
            "Background task processing"
        ]
    }

@app.get("/api/test", tags=["Debug"])
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {"message": "Test endpoint working", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/status", response_model=Dict[str, Any], tags=["Status"])
async def get_status():
    """
    Get scraper status
    
    Returns information about the scraper initialization and login status.
    """
    global scraper_instance
    
    status_data = StatusResponse(
        scraper_initialized=scraper_instance is not None,
        logged_in=False,
        platform="FastAPI",
        timestamp=datetime.utcnow().isoformat()
    )
    
    if scraper_instance:
        status_data.logged_in = scraper_instance.is_logged_in
    
    # Add debug info about imports
    try:
        from simple_linkedin_scraper import SimpleLinkedInScraper
        import_status = "success"
        import_error = None
    except Exception as e:
        import_status = "failed"
        import_error = str(e)
    
    return {
        "status": "success",
        "data": status_data.dict(),
        "debug": {
            "scraper_import_status": import_status,
            "scraper_import_error": import_error,
            "chromedriver_check": "Will test during scraping"
        }
    }

@app.post("/api/scrape-simple", tags=["Debug"])
async def scrape_profile_simple(request: ScrapeRequest):
    """Simple scrape endpoint for testing"""
    return {
        "status": "debug",
        "message": "Simple scrape endpoint reached",
        "profile_url": request.profile_url,
        "scraper_available": SCRAPER_AVAILABLE,
        "scraper_error": SCRAPER_ERROR
    }

@app.post("/api/scrape", response_model=ScrapeResponse, tags=["Scraping"])
async def scrape_profile(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Scrape a LinkedIn profile
    
    - **profile_url**: LinkedIn profile URL (must start with https://www.linkedin.com/in/)
    - **save_to_file**: Whether to save the scraped data to a JSON file
    
    Returns the scraped profile data including basic info, experience, education, and skills.
    """
    try:
        # Check if scraper is available
        if not SCRAPER_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"Scraper not available: {SCRAPER_ERROR}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Get scraper instance
        scraper = get_scraper()
        
        # Scrape the profile
        start_time = time.time()
        profile_data = scraper.scrape_profile(request.profile_url)
        scraping_time = round(time.time() - start_time, 2)
        
        if not profile_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "message": "Failed to scrape profile. Please check the URL and try again.",
                    "profile_url": request.profile_url,
                    "scraping_time_seconds": scraping_time
                }
            )
        
        # Create response
        response = ScrapeResponse(
            status="success",
            message="Profile scraped successfully",
            data=ProfileData(**profile_data),
            metadata={
                "profile_url": request.profile_url,
                "scraping_time_seconds": scraping_time,
                "timestamp": datetime.utcnow().isoformat(),
                "framework": "FastAPI",
                "extracted_sections": {
                    "basic_info": bool(profile_data.get('name')),
                    "about": bool(profile_data.get('about') and profile_data['about'] != 'Not found'),
                    "experience": len(profile_data.get('experience', [])),
                    "education": len(profile_data.get('education', [])),
                    "skills": len(profile_data.get('skills', []))
                }
            }
        )
        
        # Save to file if requested (background task)
        if request.save_to_file:
            def save_file():
                try:
                    filepath = scraper.save_data(profile_data)
                    if filepath:
                        response.metadata["saved_to_file"] = filepath
                except Exception as e:
                    response.metadata["file_save_error"] = str(e)
            
            background_tasks.add_task(save_file)
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Internal server error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.post("/api/scrape/batch", response_model=BatchScrapeResponse, tags=["Scraping"])
async def scrape_multiple_profiles(request: BatchScrapeRequest, background_tasks: BackgroundTasks):
    """
    Scrape multiple LinkedIn profiles
    
    - **profile_urls**: List of LinkedIn profile URLs (1-10 profiles)
    - **save_to_file**: Whether to save each scraped profile to a JSON file
    
    Returns the scraped data for all profiles with individual success/error status.
    """
    try:
        # Get scraper instance
        scraper = get_scraper()
        
        # Scrape all profiles
        start_time = time.time()
        results = []
        
        for i, profile_url in enumerate(request.profile_urls):
            try:
                print(f"🔍 Scraping profile {i+1}/{len(request.profile_urls)}: {profile_url}")
                profile_data = scraper.scrape_profile(profile_url)
                
                if profile_data:
                    result_item = {
                        "profile_url": profile_url,
                        "status": "success",
                        "data": profile_data
                    }
                    
                    # Save to file if requested (background task)
                    if request.save_to_file:
                        def save_file(data=profile_data):
                            try:
                                filepath = scraper.save_data(data)
                                if filepath:
                                    result_item["saved_to_file"] = filepath
                            except Exception as e:
                                result_item["file_save_error"] = str(e)
                        
                        background_tasks.add_task(save_file)
                else:
                    result_item = {
                        "profile_url": profile_url,
                        "status": "error",
                        "message": "Failed to scrape profile"
                    }
                
                results.append(result_item)
                
                # Add delay between requests
                if i < len(request.profile_urls) - 1:
                    time.sleep(3)
            
            except Exception as e:
                results.append({
                    "profile_url": profile_url,
                    "status": "error",
                    "message": str(e)
                })
        
        total_time = round(time.time() - start_time, 2)
        successful_scrapes = sum(1 for r in results if r["status"] == "success")
        
        return BatchScrapeResponse(
            status="success",
            message=f"Batch scraping completed. {successful_scrapes}/{len(request.profile_urls)} profiles scraped successfully.",
            data=results,
            metadata={
                "total_profiles": len(request.profile_urls),
                "successful_scrapes": successful_scrapes,
                "failed_scrapes": len(request.profile_urls) - successful_scrapes,
                "total_time_seconds": total_time,
                "framework": "FastAPI",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Internal server error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/api/files", response_model=Dict[str, Any], tags=["Files"])
async def list_output_files():
    """
    List all scraped profile files
    
    Returns a list of all JSON files in the output directory with metadata.
    """
    try:
        output_dir = './output'
        if not os.path.exists(output_dir):
            return {
                "status": "success",
                "data": [],
                "count": 0,
                "message": "No output directory found"
            }
        
        files = []
        for filename in os.listdir(output_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(output_dir, filename)
                file_stats = os.stat(filepath)
                files.append(FileInfo(
                    filename=filename,
                    size_bytes=file_stats.st_size,
                    created_at=datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    modified_at=datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                ))
        
        # Sort by creation time (newest first)
        files.sort(key=lambda x: x.created_at, reverse=True)
        
        return {
            "status": "success",
            "data": [file.dict() for file in files],
            "count": len(files),
            "framework": "FastAPI"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": str(e)
            }
        )

@app.get("/api/files/{filename}", tags=["Files"])
async def get_output_file(filename: str):
    """
    Download a specific output file
    
    - **filename**: Name of the file to download (with or without .json extension)
    
    Returns the JSON file as a download.
    """
    try:
        output_dir = './output'
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = os.path.join(output_dir, filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "message": f"File {filename} not found"
                }
            )
        
        return FileResponse(
            filepath,
            media_type='application/json',
            filename=filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": str(e)
            }
        )

# Custom error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "message": "Endpoint not found",
            "framework": "FastAPI",
            "documentation": {
                "swagger_ui": "/docs",
                "redoc": "/redoc"
            },
            "available_endpoints": [
                "GET / - Health check",
                "GET /api/status - Scraper status",
                "POST /api/scrape - Scrape single profile",
                "POST /api/scrape/batch - Scrape multiple profiles",
                "GET /api/files - List output files",
                "GET /api/files/{filename} - Download file",
                "GET /docs - API documentation (Swagger UI)",
                "GET /redoc - API documentation (ReDoc)"
            ]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "framework": "FastAPI",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == '__main__':
    print("🚀 Starting LinkedIn Profile Scraper API with FastAPI...")
    print("📋 Available endpoints:")
    print("  - GET  /              - Health check")
    print("  - GET  /docs          - Swagger UI documentation")
    print("  - GET  /redoc         - ReDoc documentation")
    print("  - GET  /api/status    - Scraper status")
    print("  - POST /api/scrape    - Scrape single profile")
    print("  - POST /api/scrape/batch - Scrape multiple profiles")
    print("  - GET  /api/files     - List output files")
    print("  - GET  /api/files/{filename} - Download file")
    print("🌐 Framework: FastAPI with automatic documentation")
    print()
    
    # Run with uvicorn
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )