import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import get_job_repository
from app.repositories.job_repository import JobRepository
from app.schemas.job import ExtractionJobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=ExtractionJobResponse)
async def get_job_status(
    job_id: uuid.UUID,
    repo: JobRepository = Depends(get_job_repository),
):
    """Retrieve current status, progress, and record counts for an extraction job."""
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found.")
    return ExtractionJobResponse.model_validate(job)
