from fastapi import APIRouter
from backend.api.v1.roads import router as roads_router
from backend.api.v1.projects import router as projects_router
from backend.api.v1.tenders import router as tenders_router
from backend.api.v1.contractors import router as contractors_router
from backend.api.v1.authorities import router as authorities_router
from backend.api.v1.sources import router as sources_router
from backend.api.v1.intelligence import router as intelligence_router
from backend.api.v1.research import router as research_router
from backend.api.v1.research_merge import router as research_merge_router
from backend.api.v1.data_quality import router as data_quality_router
from backend.auth.router import router as auth_router
from backend.api.v1.system import router as system_router

api_v1_router = APIRouter()
api_v1_router.include_router(system_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(roads_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(tenders_router)
api_v1_router.include_router(contractors_router)
api_v1_router.include_router(authorities_router)
api_v1_router.include_router(sources_router)
api_v1_router.include_router(intelligence_router)
api_v1_router.include_router(research_router)
api_v1_router.include_router(research_merge_router)
api_v1_router.include_router(data_quality_router)



