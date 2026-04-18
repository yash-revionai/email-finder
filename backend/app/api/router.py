from fastapi import APIRouter, Depends

from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.lookup import router as lookup_router
from app.core.security import get_current_user

api_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_current_user)])

protected_router.include_router(health_router)
protected_router.include_router(lookup_router)
protected_router.include_router(history_router)
protected_router.include_router(analytics_router)

api_router.include_router(auth_router)
api_router.include_router(protected_router)
