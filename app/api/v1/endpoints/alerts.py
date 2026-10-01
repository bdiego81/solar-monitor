from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_shinemonitor_service
from app.services.shinemonitor import ShineMonitorService
from app.services.telegram import TelegramService
from app.core.alerts import alert_manager
from app.core.config_manager import config_manager
from app.config import get_settings, Settings

router = APIRouter()


class TelegramTestPayload(BaseModel):
    token: Optional[str] = Field(None, description="Token opcional para probar antes de guardar")
    chat_id: Optional[str] = Field(None, description="Chat ID opcional para probar antes de guardar")


@router.post(
    "/test-telegram",
    include_in_schema=False,
    summary="Enviar mensaje de prueba a Telegram",
    description="Envía un mensaje de prueba al chat o grupo para verificar credenciales (acepta credenciales temporales o guardadas)."
)
async def test_telegram(
    payload: Optional[TelegramTestPayload] = None,
    settings: Settings = Depends(get_settings)
):
    """Prueba la integración de Telegram."""
    telegram = TelegramService(settings)
    token = payload.token if payload else None
    chat_id = payload.chat_id if payload else None
    return await telegram.test_connection(token=token, chat_id=chat_id)


@router.post(
    "/test-daily-report",
    include_in_schema=False,
    summary="Probar envío del reporte diario (cierre de jornada)",
    description="Genera y envía de inmediato a Telegram el resumen de jornada para verificar su formato y contenido."
)
async def test_daily_report(
    service: ShineMonitorService = Depends(get_shinemonitor_service)
):
    """Dispara un reporte diario inmediato."""
    status = service.get_current_status()
    return await alert_manager.trigger_daily_report_now(service, status)


@router.get(
    "/status",
    summary="Consultar estado de alertas activas y umbrales",
    description="Retorna el mapa de alertas activas, tiempos de último envío y umbrales configurados."
)
def get_alerts_status():
    """Consulta el estado del AlertManager y la configuración activa."""
    cfg = config_manager.get_config()
    return {
        "telegram_configured": cfg.is_telegram_ready,
        "cooldown_minutes": cfg.alert_cooldown_minutes,
        "thresholds": {
            "max_temp_c": cfg.alert_temp_max_c,
            "overload_w": cfg.alert_overload_w,
            "overload_percent": cfg.alert_overload_pct,
            "low_battery_percent": cfg.alert_low_battery_pct,
            "grid_restore_min_v": cfg.grid_restore_min_v,
            "watchdog_timeout_minutes": cfg.watchdog_timeout_minutes,
            "daily_report_time": cfg.daily_report_time,
            "daily_report_enabled": cfg.daily_report_enabled,
        },
        "alerts": alert_manager.get_active_alerts(),
        "daily_stats": {
            "outages_today": alert_manager.daily_tracker.grid_outages_count,
            "min_battery_today": alert_manager.daily_tracker.min_battery_pct,
            "daily_report_sent": alert_manager.daily_tracker.daily_report_sent
        }
    }


@router.post(
    "/check-now",
    include_in_schema=False,
    summary="Forzar ciclo de evaluación de alertas",
    description="Consulta el estado actual del inversor y ejecuta la evaluación de alertas inmediatamente."
)
async def check_alerts_now(
    service: ShineMonitorService = Depends(get_shinemonitor_service)
):
    """Evalúa manualmente el estado para disparar alertas si corresponde."""
    status = service.get_current_status()
    result = await alert_manager.evaluate_status(status, service_instance=service)
    return {
        "device_sn": status.device_sn,
        "status": status.status,
        "result": result
    }
