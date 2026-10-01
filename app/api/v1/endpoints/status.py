from fastapi import APIRouter, Depends
from app.api.deps import get_shinemonitor_service
from app.services.shinemonitor import ShineMonitorService
from app.schemas.status import StatusResponse

router = APIRouter()


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Obtener estado y telemetría en tiempo real",
    description="Retorna las métricas del inversor solar, estado de red, batería y alertas activas."
)
def get_status(
    service: ShineMonitorService = Depends(get_shinemonitor_service)
) -> StatusResponse:
    """Endpoint para consultar la telemetría actual del sistema solar."""
    return service.get_current_status()
