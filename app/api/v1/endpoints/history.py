import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_shinemonitor_service
from app.core.calculator import generate_dates_list
from app.services.shinemonitor import ShineMonitorService
from app.schemas.history import HistoryResponse

router = APIRouter()


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Obtener serie histórica de telemetría",
    description="Consulta la generación fotovoltaica, consumos y estado de batería para una fecha o rango de fechas."
)
def get_history(
    date: Optional[str] = Query(
        None,
        description="Fecha única a consultar en formato YYYY-MM-DD (ej: '2026-09-23')"
    ),
    start_date: Optional[str] = Query(
        None,
        description="Fecha de inicio para consultas de rango (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None,
        description="Fecha de término para consultas de rango (YYYY-MM-DD)"
    ),
    service: ShineMonitorService = Depends(get_shinemonitor_service)
) -> HistoryResponse:
    """Endpoint para consultar la serie histórica y el balance de kWh."""
    if start_date and end_date:
        target_dates = generate_dates_list(start_str=start_date, end_str=end_date, max_days=15)
        if not target_dates:
            target_dates = [datetime.date.today().strftime("%Y-%m-%d")]
    elif date:
        target_dates = [date]
    else:
        target_dates = [datetime.date.today().strftime("%Y-%m-%d")]

    return service.get_historical_data(target_dates=target_dates)
