# api/main.py
"""
FastAPI backend for RepoIntegrator.
Separates UI concerns from business logic.
"""
from dotenv import load_dotenv; load_dotenv()


from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import logging
import os
from typing import Optional

from repofactor.application.services.repo_integrator_service import (
    RepoIntegratorService
)


# Setup
app = FastAPI(title="RepoIntegrator API", version="0.1.0")
logger = logging.getLogger(__name__)

# Initialize service (singleton)
repo_service = RepoIntegratorService()

@app.get("/")
def root():
    return {"status": "API is running!", "endpoints": ["/api/v1/analyze-repo", "/api/v1/health", "..."]}


# Request/Response models
class AnalyzeRepoRequest(BaseModel):
    repo_url: str
    target_file: Optional[str] = None
    instructions: str = ""
    model: str = "GEMINI_2_5_FLASH"


class AnalyzeRepoResponse(BaseModel):
    success: bool
    data: dict
    error: Optional[str] = None
    quota_remaining: int


# Endpoints
@app.post("/api/v1/analyze-repo")
async def analyze_repo(request: AnalyzeRepoRequest) -> AnalyzeRepoResponse:
    """
    POST /api/v1/analyze-repo
    
    Analyze repository and return integration plan.
    """
    
    try:
        logger.info(f"Analyzing repo: {request.repo_url}")
        
        result = await repo_service.analyze_repository(
            repo_url=request.repo_url,
            target_file=request.target_file,
            user_instructions=request.instructions
        )
        
        # Get remaining quota
        quota = repo_service.lightning_client.get_remaining_quota() \
            if repo_service.lightning_client else -1
        
        return AnalyzeRepoResponse(
            success=True,
            data={
                "repo_name": result.repo_name,
                "affected_files": result.affected_files,
                "dependencies": result.dependencies,
                "risks": result.risks,
                "estimated_time": result.estimated_time,
                "implementation_steps": result.implementation_steps
            },
            quota_remaining=quota
        )
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

