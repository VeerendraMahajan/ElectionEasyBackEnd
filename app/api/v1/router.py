from fastapi import APIRouter
from app.api.v1.documents import router as documents_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.records import router as records_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(documents_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(records_router)
