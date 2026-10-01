from fastapi import APIRouter
from app.api.v1.endpoints import status, history, alerts, config

api_router = APIRouter()

api_router.include_router(status.router, tags=["Status"])
api_router.include_router(history.router, tags=["History"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(config.router, prefix="/config", tags=["Config"])

