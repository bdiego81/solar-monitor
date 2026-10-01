from fastapi import Depends
from app.config import Settings, get_settings
from app.services.shinemonitor import ShineMonitorService


def get_shinemonitor_service(
    settings: Settings = Depends(get_settings)
) -> ShineMonitorService:
    """
    Proveedor de inyección de dependencias para ShineMonitorService.
    """
    return ShineMonitorService(settings=settings)
